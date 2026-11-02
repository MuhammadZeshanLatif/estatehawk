"""Free address -> lat/lng using the US Census Bureau batch geocoder (no API key).
Used when a county property page has no map link (e.g. Geauga auditor site)."""
import csv, io
import requests

URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"


def batch(rows):
    """rows: [(id, street, city, state, zip)] -> {id: (lat, lng)}. Max 10,000 per call; we send 1,000."""
    out = {}
    for i in range(0, len(rows), 1000):
        chunk = rows[i:i + 1000]
        buf = io.StringIO()
        w = csv.writer(buf)
        for r in chunk:
            w.writerow(r)
        try:
            resp = requests.post(URL, data={"benchmark": "Public_AR_Current"},
                                 files={"addressFile": ("addresses.csv", buf.getvalue(), "text/csv")}, timeout=300)
            resp.raise_for_status()
        except requests.RequestException:
            continue
        for line in csv.reader(io.StringIO(resp.text)):
            # id, input address, Match/No_Match, Exact/Non_Exact, matched address, "lon,lat", tiger id, side
            if len(line) >= 6 and line[2] == "Match" and "," in line[5]:
                lon, lat = line[5].split(",")
                try:
                    out[line[0]] = (float(lat), float(lon))
                except ValueError:
                    pass
    return out


def one(street, city, state, zp):
    """Single address -> (lat, lng) or None. Used when a deal page is opened before the next sync."""
    try:
        r = requests.get("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                         params={"address": f"{street}, {city} {state} {zp}".strip(), "benchmark": "Public_AR_Current", "format": "json"},
                         timeout=10)
        m = r.json()["result"]["addressMatches"]
        if m:
            return m[0]["coordinates"]["y"], m[0]["coordinates"]["x"]
    except Exception:
        pass
    return None
