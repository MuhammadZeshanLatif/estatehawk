"""Subscription plans and what each company may see. Payment comes later; the super admin sets plans by hand."""
import datetime as dt

from . import db

# counties/users: None = no limit. reveals: how many leads a trial may open in full (None = all).
PLANS = {
    "trial":    {"label": "Free trial", "price": 0,   "counties": 1,    "users": 1,  "reveals": 10,   "export": False, "days": 14},
    "starter":  {"label": "Starter",    "price": 49,  "counties": 1,    "users": 1,  "reveals": None, "export": True, "export_day": 300},
    "pro":      {"label": "Pro",        "price": 99,  "counties": 3,    "users": 3,  "reveals": None, "export": True, "export_day": 1000},
    "agency":   {"label": "Agency",     "price": 249, "counties": None, "users": 10, "reveals": None, "export": True, "export_day": 3000},
    "internal": {"label": "Owner",      "price": 0,   "counties": None, "users": None, "reveals": None, "export": True},
}
PUBLIC = ["trial", "starter", "pro", "agency"]


def today():
    return dt.date.today().isoformat()


def org_info(org_id):
    o = db.q1("SELECT * FROM orgs WHERE id=?", (org_id,))
    if not o:
        return None
    plan = PLANS.get(o["plan"], PLANS["trial"])
    chosen = [r["county_id"] for r in db.q("SELECT county_id FROM org_counties WHERE org_id=? ORDER BY county_id", (org_id,))]
    if plan["counties"] is None and not chosen:
        counties = None  # every county
    else:
        counties = chosen[: plan["counties"]] if plan["counties"] else chosen
    days_left = None
    expired = False
    if o["plan"] == "trial":
        ends = o.get("trial_ends") or today()
        days_left = (dt.date.fromisoformat(ends[:10]) - dt.date.today()).days
        expired = days_left < 0
    used = db.q1("SELECT COUNT(*) n FROM reveals WHERE org_id=?", (org_id,))["n"] if plan["reveals"] else 0
    users = db.q1("SELECT COUNT(*) n FROM users WHERE org_id=? AND active=1", (org_id,))["n"]
    return {"id": o["id"], "name": o["name"], "plan": o["plan"], "label": plan["label"], "limits": plan, "status": o["status"],
            "trial_ends": o.get("trial_ends"), "days_left": days_left, "expired": expired or o["status"] == "suspended",
            "suspended": o["status"] == "suspended", "counties": counties, "reveals_used": used,
            "reveals_left": (plan["reveals"] - used) if plan["reveals"] else None, "users": users}


def is_locked(info, parcel_id):
    """Trial companies see a lead in full only after revealing it."""
    if not info or not info["limits"]["reveals"]:
        return False
    return not db.q1("SELECT 1 FROM reveals WHERE org_id=? AND parcel_id=?", (info["id"], parcel_id))


def revealed_set(info, ids):
    if not info or not info["limits"]["reveals"] or not ids:
        return None
    rows = db.q(f"SELECT parcel_id FROM reveals WHERE org_id=? AND parcel_id IN ({','.join('?' * len(ids))})", [info["id"]] + list(ids))
    return {r["parcel_id"] for r in rows}


HIDE = {"owner_name": "Owner hidden", "owner_full_name": "Owner hidden", "street": "Address hidden", "mail_address": None,
        "parcel_number": "Hidden", "property_url": None, "legal_desc": None, "photo_url": None, "contact_status": None}


def mask(row):
    """What a trial user sees for a lead they have not revealed: money, score and area, but not who or where."""
    for k, v in HIDE.items():
        if k in row:
            row[k] = v
    if row.get("lat") is not None:  # about 1 km: right area on the map, not the house
        row["lat"], row["lng"] = round(row["lat"], 2), round(row["lng"], 2)
    row["locked"] = True
    return row


def export_allowance(info):
    """How many CSV rows this company may still export today. None = no limit (owner).
    The first 7 days after the first payment get half the daily limit, so nobody can pay, copy everything and leave."""
    lim = info["limits"].get("export_day")
    if not lim:
        return None
    from . import billing
    since = (billing.get(info["id"]).get("paid_since") or "")[:10]
    if since and (dt.date.today() - dt.date.fromisoformat(since)).days < 7:
        lim //= 2
    r = db.q1("SELECT value FROM org_settings WHERE org_id=? AND key=?", (info["id"], "export:" + today()))
    used = int(r["value"]) if r and str(r["value"]).isdigit() else 0
    return max(0, lim - used), lim


def export_used(info, n):
    key = "export:" + today()
    r = db.q1("SELECT value FROM org_settings WHERE org_id=? AND key=?", (info["id"], key))
    if r:
        db.run("UPDATE org_settings SET value=? WHERE org_id=? AND key=?", (str(int(r["value"] or 0) + n), info["id"], key))
    else:
        db.run("INSERT INTO org_settings(org_id,key,value) VALUES(?,?,?)", (info["id"], key, str(n)))
