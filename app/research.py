"""Property research: flood zone, state tax-sale rules, comps and value (RentCast), and the deal calculator.

Every fact says where it came from. Estimates are labelled as estimates. Legal text is a dated summary with the
statute link, never legal advice.
"""
import datetime as dt
import json
import os

import requests

from . import db

UA = "EstateHawk/1.0 (https://getestatehawk.com; support@getestatehawk.com)"

# ------------------------------------------------------------------ flood zone (FEMA National Flood Hazard Layer)
FLOOD_SOURCES = [
    ("FEMA National Flood Hazard Layer",
     "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"),
    ("FEMA flood hazard layer (HIFLD copy)",
     "https://maps.nccs.nasa.gov/mapping/rest/services/hifld_open/national_flood_hazard/FeatureServer/3/query"),
]
FLOOD_HIGH = ("A", "AE", "AH", "AO", "AR", "A99", "V", "VE")  # FEMA special flood hazard areas (1% a year)


def flood_words(zone, sfha):
    z = (zone or "").upper()
    if not z:
        return "Not checked"
    if sfha or z in FLOOD_HIGH:
        return f"Zone {z}: high risk (FEMA special flood hazard area; lenders require flood insurance)"
    if z == "X":
        return "Zone X: moderate to low risk"
    if z == "D":
        return "Zone D: risk not studied by FEMA"
    return f"Zone {z}"


def flood(lat, lng, session=None):
    """{'zone', 'sfha', 'source'} at a point, or None when no source answers."""
    s = session or requests.Session()
    for name, url in FLOOD_SOURCES:
        try:
            r = s.get(url, timeout=8, headers={"User-Agent": UA}, params={
                "geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "false", "f": "json"})
            feats = r.json().get("features") if r.status_code == 200 else None
        except (requests.RequestException, ValueError):
            continue
        if feats is None:
            continue
        if not feats:  # inside the mapped area but no polygon: FEMA treats unmapped land as not studied
            return {"zone": "", "sfha": 0, "source": name, "unmapped": True}
        a = {k.upper(): v for k, v in (feats[0].get("attributes") or {}).items()}
        zone = (a.get("FLD_ZONE") or "").strip()
        sfha = 1 if str(a.get("SFHA_TF") or "").upper() in ("T", "TRUE", "1") or zone.upper() in FLOOD_HIGH else 0
        return {"zone": zone, "sfha": sfha, "source": name, "subtype": a.get("ZONE_SUBTY") or ""}
    return None


def flood_for(p):
    """Cached flood zone for a lead with a map point (looked up once, kept 180 days)."""
    if p.get("lat") is None:
        return {"words": "Not checked: no map location", "zone": None}
    checked = p.get("flood_checked")
    if checked and checked >= (dt.date.today() - dt.timedelta(days=180)).isoformat():
        return {"words": flood_words(p.get("flood_zone"), p.get("flood_sfha")), "zone": p.get("flood_zone"),
                "sfha": p.get("flood_sfha"), "checked": checked, "source": "FEMA National Flood Hazard Layer"}
    f = flood(p["lat"], p["lng"])
    if f is None:
        return {"words": "Not checked: the FEMA map did not answer. Try again later.", "zone": None}
    today = dt.date.today().isoformat()
    db.run("UPDATE parcels SET flood_zone=?, flood_sfha=?, flood_checked=? WHERE id=?", (f["zone"], f["sfha"], today, p["id"]))
    words = "No FEMA flood zone mapped here" if f.get("unmapped") else flood_words(f["zone"], f["sfha"])
    return {"words": words, "zone": f["zone"], "sfha": f["sfha"], "checked": today, "source": f["source"]}


# ------------------------------------------------------------------ state tax-sale rules (summaries, dated, linked)
REVIEWED = "2026-11-06"
NOT_ADVICE = ("A plain-language summary of state law for research. It is not legal advice; rules change and counties "
              "add their own steps. Confirm with the county and a real estate attorney before you bid or buy.")
RULES = {
    "OH": {
        "name": "Ohio",
        "kind": "Tax foreclosure, then sheriff or forfeited-land sale",
        "points": [
            ("How a sale happens", "Delinquent taxes become a lien. The county prosecutor can file a tax foreclosure in court, and the property is then offered at a sheriff's sale. Unsold parcels can be forfeited to the state and offered again at a forfeited-land sale.",
             "https://codes.ohio.gov/ohio-revised-code/chapter-5721"),
            ("Owner can redeem until", "The owner can pay the taxes, penalties, interest and costs and keep the property any time before the court confirms the sale.",
             "https://codes.ohio.gov/assets/laws/revised-code/authenticated/57/5721/5721.25/4-7-2009/5721.25-4-7-2009.pdf"),
            ("Tax certificates", "Some Ohio counties sell tax certificates (a lien on the taxes, not the property). The certificate holder can later ask for foreclosure if the owner does not pay.",
             "https://codes.ohio.gov/ohio-revised-code/section-5721.30"),
        ],
        "checklist": ["County treasurer payoff letter (amount to clear the taxes)", "Title search for mortgages, liens and judgments",
                      "Sheriff's sale terms: deposit, payment deadline, who pays the deed and recording fees",
                      "Confirmation of sale entry and sheriff's deed", "Occupancy check before closing"],
    },
    "TX": {
        "name": "Texas",
        "kind": "Tax foreclosure lawsuit, then constable or sheriff sale",
        "points": [
            ("How a sale happens", "The taxing units sue the owner. After judgment the property is sold at a public sale by the constable or sheriff; tax attorneys publish the sale lists.",
             "https://statutes.capitol.texas.gov/Docs/TX/htm/TX.34.htm"),
            ("Redemption after the sale", "Homestead and agricultural land: the owner can buy it back within 2 years after the deed is recorded (25% premium in year one, 50% in year two). Other property: within 180 days, premium up to 25%.",
             "https://texas.public.law/statutes/tex._tax_code_section_34.21"),
            ("What the buyer gets", "A deed without warranty. The buyer should expect title work and possible redemption before the property is free to resell.",
             "https://statutes.capitol.texas.gov/Docs/TX/htm/TX.34.htm"),
        ],
        "checklist": ["Sale list entry: cause number, minimum bid, adjudged value", "Title search, including federal tax liens (IRS can redeem for 120 days)",
                      "Homestead or agricultural status (sets the 2-year redemption)", "Payment terms on sale day (certified funds)",
                      "Recorded deed date (starts the redemption clock)"],
    },
}


def redemption_end(state, sale_or_deed_date, homestead=None):
    """Texas: last day the owner can redeem, counted from the deed (sale) date. None when unknown."""
    if state != "TX" or not sale_or_deed_date:
        return None
    try:
        d = dt.date.fromisoformat(sale_or_deed_date[:10])
    except ValueError:
        return None
    if homestead:
        try:
            return d.replace(year=d.year + 2).isoformat()
        except ValueError:  # Feb 29
            return (d + dt.timedelta(days=730)).isoformat()
    return (d + dt.timedelta(days=180)).isoformat()


def rules_for(p):
    st = (p.get("state") or "OH").upper()
    r = RULES.get(st)
    if not r:
        return None
    out = {**r, "state": st, "reviewed": REVIEWED, "note": NOT_ADVICE}
    sale = p.get("sale_date") or p.get("tax_sale_date")
    if sale:
        out["sale_date"] = sale
        if st == "TX":
            home = p.get("owner_occupied") == 1
            end = redemption_end(st, sale, home)
            out["redemption"] = {"ends": end, "homestead": home,
                                 "basis": "2 years (homestead)" if home else "180 days (not marked as homestead)",
                                 "assumes": "Counted from the sale date; the clock really starts when the deed is recorded."}
    return out


# ------------------------------------------------------------------ comps and value (RentCast)
RENTCAST = "https://api.rentcast.io/v1/avm/value"


def rentcast_key():
    return os.environ.get("RENTCAST_API_KEY", "").strip()


def rentcast_limit():
    """Calls allowed per calendar month. RentCast has no hard cap and bills every call past the plan, so we stop here."""
    try:
        return int(os.environ.get("RENTCAST_MONTHLY_LIMIT", "45"))
    except ValueError:
        return 45


def _usage_key():
    return "rentcast:" + dt.date.today().strftime("%Y-%m")


def rentcast_used():
    r = db.q1("SELECT value FROM org_settings WHERE org_id=0 AND key=?", (_usage_key(),))
    return int((r or {}).get("value") or 0)


def comps(p, refresh=False, fetch=True):
    """Value estimate and nearby sales from RentCast, cached 30 days per lead. None without a key or an address.
    fetch=False only reads the cache (used by the calculator, so it never spends a paid call)."""
    cached = db.q1("SELECT ts, data FROM research_cache WHERE parcel_id=? AND kind='comps'", (p["id"],))
    if cached and not refresh and cached["ts"] >= (dt.date.today() - dt.timedelta(days=30)).isoformat():
        return json.loads(cached["data"])
    if not fetch:
        return json.loads(cached["data"]) if cached else None
    if not rentcast_key():
        return None
    if not (p.get("street") or "")[:1].isdigit():
        return {"error": "Needs a street address with a house number."}
    used = rentcast_used()
    if used >= rentcast_limit():
        if cached:
            return json.loads(cached["data"])
        return {"error": "Value lookups for this month are used up. They start again on the 1st."}
    db.run("""INSERT INTO org_settings(org_id,key,value) VALUES(0,?,?)
              ON CONFLICT(org_id,key) DO UPDATE SET value=excluded.value""", (_usage_key(), str(used + 1)))
    addr = ", ".join(x for x in (p.get("street"), p.get("city"), f"{p.get('state') or 'OH'} {p.get('zip') or ''}".strip()) if x)
    try:
        r = requests.get(RENTCAST, timeout=30, headers={"X-Api-Key": rentcast_key(), "Accept": "application/json"},
                         params={"address": addr, "compCount": 6, **({"squareFootage": p["living_area"]} if p.get("living_area") else {}),
                                 **({"bedrooms": p["beds"]} if p.get("beds") else {})})
    except requests.RequestException as e:
        return {"error": f"RentCast did not answer ({e.__class__.__name__})."}
    if r.status_code != 200:
        return {"error": f"RentCast said {r.status_code}: {r.text[:160]}"}
    j = r.json()
    data = {"value": j.get("price"), "low": j.get("priceRangeLow"), "high": j.get("priceRangeHigh"), "source": "RentCast AVM",
            "fetched": dt.date.today().isoformat(),
            "comps": [{"address": c.get("formattedAddress"), "price": c.get("price"), "sqft": c.get("squareFootage"),
                       "beds": c.get("bedrooms"), "baths": c.get("bathrooms"), "miles": round(c.get("distance") or 0, 2),
                       "date": (c.get("removedDate") or c.get("listedDate") or c.get("lastSeenDate") or "")[:10],
                       "status": c.get("status") or ""} for c in (j.get("comparables") or [])[:6]]}
    db.run("""INSERT INTO research_cache(parcel_id,kind,ts,data) VALUES(?,?,?,?)
              ON CONFLICT(parcel_id,kind) DO UPDATE SET ts=excluded.ts, data=excluded.data""",
           (p["id"], "comps", data["fetched"], json.dumps(data)))
    return data


# ------------------------------------------------------------------ deal calculator
RISK = {"low": {"profit": 25, "repair_buffer": 20}, "medium": {"profit": 20, "repair_buffer": 10}, "high": {"profit": 15, "repair_buffer": 0}}


def calc(p, d=None, arv=None, repairs=None, liens=0):
    """Max bid and expected profit. Every input is shown back, with where it came from."""
    d = {**db.DEFAULT_SETTINGS["calc_defaults"], **(d or {})}
    risk = RISK.get(d.get("risk") or "medium", RISK["medium"])
    profit_pct = float(d.get("profit_pct") or risk["profit"])
    src = {}
    if arv is None:
        cv = (comps(p, fetch=False) or {}).get("value")
        arv, src["arv"] = (cv, "RentCast value estimate") if cv else (p.get("appraised_total") or 0, "County value (often below market)")
    else:
        src["arv"] = "Your number"
    sqft = p.get("living_area") or 0
    if repairs is None:
        base = sqft * float(d.get("repair_per_sqft") or 25) if sqft else arv * 0.15
        repairs = round(base * (1 + risk["repair_buffer"] / 100))
        src["repairs"] = (f"{sqft:,} sq ft x ${d.get('repair_per_sqft')}/sq ft" if sqft else "15% of value") + (f" + {risk['repair_buffer']}% buffer" if risk["repair_buffer"] else "")
    else:
        src["repairs"] = "Your number"
    taxes = p.get("total_due") or p.get("amount_owed") or 0
    buy_close = arv * float(d.get("buy_closing_pct") or 0) / 100
    sell_close = arv * float(d.get("sell_closing_pct") or 0) / 100
    months = float(d.get("hold_months") or 0)
    hold = months * (float(d.get("monthly_hold") or 0) + (p.get("annual_tax") or 0) / 12)
    profit = arv * profit_pct / 100
    costs = repairs + taxes + (liens or 0) + buy_close + sell_close + hold
    max_bid = max(0, arv - costs - profit)
    rule70 = max(0, arv * 0.7 - repairs - taxes)
    cash_in = max_bid + repairs + taxes + (liens or 0) + buy_close + hold
    return {"arv": round(arv), "repairs": round(repairs), "taxes": round(taxes, 2), "liens": liens or 0,
            "buy_closing": round(buy_close), "sell_closing": round(sell_close), "holding": round(hold), "hold_months": months,
            "profit": round(profit), "profit_pct": profit_pct, "max_bid": round(max_bid / 100) * 100, "rule70": round(rule70 / 100) * 100,
            "roi_pct": round(profit * 100 / cash_in, 1) if cash_in else None, "risk": d.get("risk") or "medium", "sources": src,
            "warning": None if arv else "No value to work from: add your own after-repair value."}
