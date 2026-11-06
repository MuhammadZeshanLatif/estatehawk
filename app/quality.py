"""Where each number comes from, how fresh it is and what is missing: per lead and per county.

Per lead: the county list it came from, when it was first and last seen there, whether it is still on the latest list,
the amount on the list against the amount on the county's own property record, the fields the county did not publish,
and which numbers are estimates.
Per county: share of leads with an address, a map point, a county value and an owner mailing address, plus how old
the last good download is.
"""
import datetime as dt

from . import db

FILE_LISTS = {
    "franklin": "https://apps.franklincountyauditor.com",
    "montgomery": "https://go.mcohio.org/applications/treasurer/search/",
    "hamilton": "https://www.hamiltoncountyauditor.org/download/Delinquent/unpaid.xlsx",
    "stark": "https://www.starkcountyohio.gov/government/offices/treasurer/departments/delinquent_tax_and_foreclosures/index.php",
    "allen": "https://allencountyohauditor.com/delinquent-lists-and-auditor-sales/",
    "summit": "https://akronlegalnews.com/notices/delinquent_taxes",
}


def list_url(host):
    """The public page of the county list a lead came from."""
    h = host or ""
    if h.startswith("lgbs"):
        return "https://taxsales.lgbs.com/"
    if h.startswith("file:"):
        return FILE_LISTS.get(h[5:])
    return f"https://{h}/DelinquentList" if h else None


def source_name(host):
    h = host or ""
    if h.startswith("lgbs"):
        return "Texas tax sale list (Linebarger, for the county tax office)"
    if h.startswith("file:allen"):
        return "County auditor delinquent list"
    return "County treasurer delinquent list"


def _day(ts):
    return (ts or "")[:10] or None


FIELDS = [  # (column test, what the reader misses without it)
    (lambda p: (p.get("owner_name") or "").strip(), "Owner name"),
    (lambda p: (p.get("street") or "").strip(), "Street address"),
    (lambda p: p.get("lat") is not None, "Map location"),
    (lambda p: p.get("appraised_total"), "County value"),
    (lambda p: p.get("mail_address") or p.get("mail_state"), "Owner mailing address"),
    (lambda p: p.get("land_use") or p.get("property_type") not in (None, "", "Unknown"), "Property type"),
    (lambda p: p.get("annual_tax"), "Yearly tax amount"),
]


def lead(p, county):
    """The 'Data sources' panel for one lead. `county` = its counties row."""
    last_sync = _day(county.get("last_sync"))
    seen = _day(p.get("last_seen"))
    on_latest = bool(p.get("is_active")) and (not last_sync or (seen or "") >= last_sync)
    missing = [label for test, label in FIELDS if not test(p)]
    a_list, a_rec = p.get("amount_owed"), p.get("total_due")
    differs = bool(a_list and a_rec and abs(a_list - a_rec) > max(50, 0.1 * max(a_list, a_rec)))
    if not p.get("is_active"):
        status, note = "removed", "No longer on the county list: the taxes may have been paid or the parcel redeemed."
    elif not on_latest:
        status, note = "stale", f"Not seen on the latest county download ({last_sync}). It may have been paid since."
    elif differs:
        status, note = "conflict", "The amount on the county list and on the county property record do not match."
    elif missing:
        status, note = "partial", f"On the latest list. The source did not provide: {', '.join(m.lower() for m in missing)}."
    else:
        status, note = "verified", "On the latest county list, with an address, map location and county value."
    return {
        "status": status, "note": note,
        "source": source_name(county.get("host")), "list_url": list_url(county.get("host")),
        "record_url": p.get("property_url"),
        "first_seen": _day(p.get("first_seen")), "last_seen": seen, "record_read": _day(p.get("enriched_at")),
        "owner_source": p.get("owner_source"), "owner_checked": _day(p.get("owner_checked")),
        "county_last_sync": county.get("last_sync"), "county_status": county.get("sync_status"),
        "amount_list": a_list, "amount_record": a_rec, "amount_differs": differs,
        "missing": missing,
        "estimates": [x for x, have in (("Equity", p.get("est_equity") is not None), ("Rent", p.get("rent_est")),
                                        ("Suggested offer", p.get("suggested_offer")), ("Deal score", p.get("score") is not None)) if have],
    }


def counties(ids=None):
    """{county_id: {"n", "address", "map", "value", "mailing", "complete", "fresh_days", "fresh"}} for active leads."""
    where = f" AND county_id IN ({','.join(str(int(i)) for i in ids)})" if ids else ""
    rows = db.q(f"""SELECT county_id, COUNT(*) n,
                    SUM(CASE WHEN COALESCE(street,'') <> '' THEN 1 ELSE 0 END) address,
                    SUM(CASE WHEN lat IS NOT NULL THEN 1 ELSE 0 END) map,
                    SUM(CASE WHEN appraised_total IS NOT NULL AND appraised_total > 0 THEN 1 ELSE 0 END) value,
                    SUM(CASE WHEN COALESCE(mail_address,'') <> '' OR COALESCE(mail_state,'') <> '' THEN 1 ELSE 0 END) mailing
                    FROM parcels WHERE is_active=1{where} GROUP BY county_id""")
    sync = {r["id"]: r for r in db.q("SELECT id, last_sync, sync_status FROM counties")}
    out = {}
    today = dt.date.today()
    for r in rows:
        n = r["n"] or 0
        pct = {k: round(100 * (r[k] or 0) / n) if n else 0 for k in ("address", "map", "value", "mailing")}
        s = sync.get(r["county_id"]) or {}
        try:
            days = (today - dt.date.fromisoformat(_day(s.get("last_sync")))).days
        except (TypeError, ValueError):
            days = None
        out[r["county_id"]] = {"n": n, **pct, "complete": round((pct["address"] + pct["map"] + pct["value"] + pct["mailing"]) / 4),
                               "fresh_days": days,
                               "fresh": "fresh" if days is not None and days <= 2 else "aging" if days is not None and days <= 7 else "old"}
    return out


def grade(q):
    """Plain word for a county's data: Full, Good, Limited."""
    if not q:
        return "No data"
    if q["address"] >= 90 and q["value"] >= 80:
        return "Full"
    if q["address"] >= 60:
        return "Good"
    return "Limited"
