"""Fill missing Texas owner names from the Texas Geographic Information Office parcel map.

The tax-sale feed does not publish owners. A map hit alone is insufficient: the
county and street address must also match before we attach an owner to a lead.
"""
import concurrent.futures
import datetime as dt
import re

import requests

from . import db

IDENTIFY = ("https://feature.geographic.texas.gov/arcgis/rest/services/Parcels/"
            "stratmap_land_parcels_48_most_recent/MapServer/identify")
BAD_NAMES = {"", "NULL", "N/A", "UNKNOWN", "CURRENT PROPERTY OWNER", "OWNER UNKNOWN"}
SUFFIXES = {"STREET": "ST", "ROAD": "RD", "AVENUE": "AVE", "DRIVE": "DR", "LANE": "LN",
            "COURT": "CT", "BOULEVARD": "BLVD", "PLACE": "PL", "PARKWAY": "PKWY"}


def clean(value):
    s = str(value or "").strip()
    return "" if s.upper() in {"NULL", "NONE", "N/A"} else s


def street(value):
    words = re.findall(r"[A-Z0-9]+", clean(value).upper().split(",", 1)[0])
    return " ".join(SUFFIXES.get(w, w) for w in words)


def match(p, results):
    """Accept one owner only when the point, county, street and known ZIP agree."""
    county = re.sub(r"\s+COUNTY$", "", p["county_name"].upper())
    wanted = street(p["street"])
    if not wanted or not re.match(r"^\d+\b", wanted):
        return None
    matches = []
    for item in results:
        a = item.get("attributes") or {}
        name = clean(a.get("OWNER_NAME"))
        situs = clean(a.get("SITUS_ADDR"))
        if name.upper() in BAD_NAMES or clean(a.get("COUNTY")).upper() != county:
            continue
        if street(situs) != wanted:
            continue
        source_zip = re.search(r"\b\d{5}(?:\d{4})?\b", situs.split(",", 1)[1] if "," in situs else "")
        if p.get("zip") and source_zip and source_zip.group(0)[:5] != str(p["zip"])[:5]:
            continue
        matches.append(a)
    owners = {clean(a["OWNER_NAME"]).upper() for a in matches}
    return matches[0] if len(owners) == 1 else None


def lookup(p):
    x, y = float(p["lng"]), float(p["lat"])
    params = {"geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "sr": "4326",
              "layers": "all:0", "tolerance": 0,
              "mapExtent": f"{x-.01},{y-.01},{x+.01},{y+.01}",
              "imageDisplay": "1000,1000,96", "returnGeometry": "false", "f": "json"}
    response = requests.get(IDENTIFY, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:200])
    return match(p, data.get("results") or [])


def run_batch(limit=300, status_cb=None):
    """Backfill a bounded batch; misses are retried after 30 days, network failures sooner."""
    retry_before = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    rows = db.q("""SELECT p.id, p.street, p.zip, p.lat, p.lng, c.name county_name
                   FROM parcels p JOIN counties c ON c.id=p.county_id
                   WHERE p.is_active=1 AND p.demo=0 AND c.state='TX'
                     AND COALESCE(TRIM(p.owner_name),'')=''
                     AND p.lat IS NOT NULL AND p.lng IS NOT NULL
                     AND p.street GLOB '[0-9]*'
                     AND (p.owner_checked IS NULL OR p.owner_checked < ?)
                   ORDER BY p.score DESC LIMIT ?""", (retry_before, max(0, int(limit))))
    found = missed = failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(lookup, p) for p in rows]
        for i, (p, future) in enumerate(zip(rows, futures), 1):
            if status_cb:
                status_cb(i, len(rows))
            try:
                result = future.result()
            except Exception as exc:
                failed += 1
                if failed <= 3:
                    print(f"Texas owner lookup: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
                continue
            if result:
                name = clean(result.get("OWNER_NAME"))
                mail = clean(result.get("MAIL_ADDR"))
                # The source may have an invalid state abbreviation; keep the address as published.
                db.run("""UPDATE parcels SET owner_name=?, owner_full_name=?, owner_source=?, owner_checked=?,
                         mail_address=COALESCE(NULLIF(mail_address,''), ?) WHERE id=? AND COALESCE(TRIM(owner_name),'')=''""",
                       (name, name, "Texas GIO parcel map / " + clean(result.get("SOURCE")),
                        dt.date.today().isoformat(), mail, p["id"]))
                found += 1
            else:
                db.run("UPDATE parcels SET owner_checked=? WHERE id=?", (dt.date.today().isoformat(), p["id"]))
                missed += 1
    return {"checked": len(rows), "found": found, "unmatched": missed, "errors": failed}
