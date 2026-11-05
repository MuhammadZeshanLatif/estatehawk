"""Fill map points, acres, county record links and street addresses for Ohio leads whose county list has only a parcel
number (Allen County: parcel, owner, amount).

1. Ohio DNR statewide parcel layer (public ArcGIS): parcel shape -> center point, acres, auditor record link.
2. Ohio LBRS statewide address points (the county's own 911 addresses): the address point inside the parcel.
3. When no address point lies inside (vacant land): OpenStreetMap Nominatim for the city and zip only
   (one request a second, as its usage policy asks).
"""
import re
import time

import requests

DNR = "https://gis.ohiodnr.gov/arcgis/rest/services/OIT_Services/odnr_landbase_v2/MapServer/4/query"
NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
LBRS = "https://maps.ohio.gov/arcgis/rest/services/Hosted/Ohio_Statewide_LBRS_Address_Points/FeatureServer/0/query"
UA = "EstateHawk/1.0 (https://getestatehawk.com; support@getestatehawk.com)"


def pin(parcel_number):
    """'37-3106-11-007.000' -> '37310611007000' (the statewide layer stores digits only)."""
    return re.sub(r"\D", "", parcel_number or "")


def _centroid(rings):
    """Area-weighted center of the largest ring (good enough to land on the lot)."""
    best, best_a = None, 0
    for ring in rings or []:
        a = cx = cy = 0.0
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            f = x1 * y2 - x2 * y1
            a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f
        if abs(a) > best_a and a:
            best_a, best = abs(a), (cy / (3 * a), cx / (3 * a))
    if best is None and rings and rings[0]:
        xs, ys = [p[0] for p in rings[0]], [p[1] for p in rings[0]]
        best = (sum(ys) / len(ys), sum(xs) / len(xs))
    return best  # (lat, lng)


def lookup(county_name, pins, session=None, chunk=40):
    """{pin: {"lat", "lng", "acres", "url"}} for the given digit-only parcel numbers of one county."""
    s = session or requests.Session()
    s.headers.setdefault("User-Agent", UA)
    county = county_name.replace(" County", "").replace("'", "''")
    out = {}
    pins = [p for p in dict.fromkeys(pins) if p]
    for i in range(0, len(pins), chunk):
        part = pins[i:i + chunk]
        where = f"COUNTY='{county}' AND PIN IN ({','.join(repr(p) for p in part)})"
        try:
            r = s.post(DNR, timeout=60, data={"where": where, "outFields": "PIN,AUD_LINK,CALC_ACRES,ASSR_ACRES",
                                               "returnGeometry": "true", "outSR": "4326", "geometryPrecision": "6",
                                               "maxAllowableOffset": "0.00002", "f": "json"})
            feats = r.json().get("features", []) if r.status_code == 200 else []
        except (requests.RequestException, ValueError):
            continue
        for f in feats:
            a = f.get("attributes") or {}
            c = _centroid((f.get("geometry") or {}).get("rings"))
            if not a.get("PIN") or not c:
                continue
            out[a["PIN"]] = {"lat": round(c[0], 6), "lng": round(c[1], 6), "acres": a.get("ASSR_ACRES") or a.get("CALC_ACRES"),
                             "url": a.get("AUD_LINK"), "rings": f["geometry"]["rings"]}
        time.sleep(0.3)
    return out


def _pick(feats, lat, lng):
    good = []
    for f in feats:
        a = f.get("attributes") or {}
        if (a.get("addr_num") or 0) <= 0 or not a.get("lsn"):
            continue
        g = f.get("geometry") or {}
        d = ((g.get("y", lat) - lat) ** 2 + (g.get("x", lng) - lng) ** 2) if g else 0
        good.append((d, a.get("addr_num"), a))
    if not good:
        return None
    a = sorted(good, key=lambda t: (t[0], t[1]))[0][2]
    return a["lsn"].upper(), (a.get("usps_city") or a.get("city") or "").upper(), (a.get("zip") or "")[:5]


def address(lat, lng, rings=None, session=None):
    """(street, city, zip) from the Ohio address points: one inside the parcel shape, else the nearest within 30 m."""
    import json
    s = session or requests.Session()
    s.headers.setdefault("User-Agent", UA)
    tries = []
    if rings:
        tries.append({"geometry": json.dumps({"rings": rings, "spatialReference": {"wkid": 4326}}),
                      "geometryType": "esriGeometryPolygon", "spatialRel": "esriSpatialRelIntersects"})
    tries.append({"geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "distance": "30", "units": "esriSRUnit_Meter",
                  "spatialRel": "esriSpatialRelIntersects"})
    for t in tries:
        try:
            r = s.post(LBRS, timeout=30, data={**t, "inSR": "4326", "outSR": "4326", "outFields": "addr_num,lsn,city,usps_city,zip",
                                                "returnGeometry": "true", "resultRecordCount": "20", "f": "json"})
            hit = _pick(r.json().get("features", []) if r.status_code == 200 else [], lat, lng)
        except (requests.RequestException, ValueError):
            hit = None
        if hit:
            return hit
    return None


def city_zip(lat, lng, session=None):
    """(city, zip) for a point with no address (vacant land), from OpenStreetMap."""
    s = session or requests.Session()
    try:
        r = s.get(NOMINATIM, timeout=20, headers={"User-Agent": UA},
                  params={"lat": lat, "lon": lng, "format": "jsonv2", "zoom": 16, "addressdetails": 1})
        a = (r.json() or {}).get("address", {}) if r.status_code == 200 else {}
    except (requests.RequestException, ValueError):
        return None
    city = a.get("city") or a.get("town") or a.get("village") or a.get("hamlet") or a.get("township") or ""
    return (city.upper(), (a.get("postcode") or "")[:5]) if city else None
