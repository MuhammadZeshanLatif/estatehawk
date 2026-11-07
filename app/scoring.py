"""Deal scoring (0-100) using the weights from Settings > Deal scoring.

Each factor gives a 0..1 strength, multiplied by its weight (weights sum to 100).
All money estimates are labelled "est." in the UI: county appraisal is used as value,
and equity ignores any mortgage (not public in the treasurer data).
"""
import math


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def property_type(land_use):
    lu = (land_use or "").upper()
    code = lu[:3]
    if code.startswith("5") or "DWELL" in lu or "RESID" in lu or "CONDO" in lu:
        return "Single family" if code in ("510", "") or "SINGLE" in lu else "Residential"
    if code.startswith("4"):
        return "Commercial"
    if code.startswith("3"):
        return "Industrial"
    if code.startswith("1"):
        return "Agricultural"
    if "VACANT" in lu:
        return "Vacant land"
    return "Other" if lu else "Unknown"


def derive(p):
    """Fill years_behind, est_equity, rent_est, suggested_offer, property_type on a parcel dict."""
    due = p.get("total_due") or p.get("amount_owed") or 0
    annual = p.get("annual_tax") or 0
    prior = p.get("prior_due") or 0
    # current year + however many years of tax the prior balance covers
    import datetime as _dt
    if p.get("cert_year"):
        yb = max(1, (_dt.date.today().year - 1) - int(p["cert_year"]) + 1)
    elif annual > 0 and prior:
        yb = 1 + round(prior / annual)
    elif prior and not annual:
        yb = 2  # only old (prior-year) tax is owed; exact years unknown
    else:
        yb = 1
    p["years_behind"] = min(yb, 15)
    value = p.get("appraised_total") or 0
    p["est_equity"] = round(value - due, 0) if value else None
    ptype = property_type(p.get("land_use"))
    p["property_type"] = ptype
    if value and ptype in ("Single family", "Residential"):
        # rough rule of thumb for small Ohio markets: ~0.9% of value per month, floor $650
        base = max(650, value * 0.009)
        if p.get("beds"):
            base = max(base, 550 + 250 * min(int(p["beds"]), 5))
        p["rent_est"] = round(base / 10) * 10
    else:
        p["rent_est"] = None
    return p


def suggested_offer(p, discount_pct=65):
    value = p.get("appraised_total") or 0
    due = p.get("total_due") or p.get("amount_owed") or 0
    if not value:
        return None
    return max(0, round((value * discount_pct / 100 - due) / 500) * 500)


def factors(p):
    due = p.get("total_due") or p.get("amount_owed") or 0
    value = p.get("appraised_total") or 0
    eq = p.get("est_equity") or 0
    yb = p.get("years_behind") or 1
    f = {}
    f["years_behind"] = clamp((yb - 0.5) / 3.5)
    eq_abs = clamp(eq / 100000)
    eq_ratio = clamp(eq / value) if value else 0
    f["equity"] = 0.5 * eq_abs + 0.5 * eq_ratio if value else 0.2
    f["amount_owed"] = clamp(math.log(max(due, 1) / 300) / math.log(25000 / 300)) if due else 0
    state = (p.get("state") or "OH").upper()
    ms = (p.get("mail_state") or "").upper()
    if ms and ms != state:
        f["out_of_state"] = 1.0
    elif p.get("owner_occupied") == 0 and p.get("mail_zip") and p.get("zip") and p.get("mail_zip") != p.get("zip"):
        f["out_of_state"] = 0.55  # absentee owner, same state
    else:
        f["out_of_state"] = 0.0
    vac = 0.0
    if p.get("owner_occupied") == 0:
        vac += 0.5
    if yb >= 3:
        vac += 0.3
    if p.get("improvement_value") == 0:
        vac += 0.2  # nothing built on it: land deal
    f["vacancy"] = clamp(vac)
    return f


LABELS = {
    "years_behind": "Years behind on tax",
    "equity": "Estimated equity",
    "amount_owed": "Amount owed",
    "out_of_state": "Out-of-state / absentee owner",
    "vacancy": "Vacancy signals",
}


def score(p, weights):
    f = factors(p)
    total_w = sum(weights.values()) or 1
    parts = {k: round(f.get(k, 0) * weights.get(k, 0) * 100 / total_w, 1) for k in LABELS}
    s = round(sum(parts.values()))
    return s, {"parts": parts, "factors": f, "weights": weights}


def reasons(p, breakdown):
    """Plain-language 'why this score' bullets (used when no AI key is set)."""
    out = []
    yb = p.get("years_behind") or 1
    due = p.get("total_due") or p.get("amount_owed") or 0
    if yb >= 2:
        out.append(("Longer tax delinquency", f"About {yb:g} years behind (${due:,.0f} due). This is a public-record signal, not evidence that the owner wants to sell."))
    else:
        out.append(("Recently delinquent", f"${due:,.0f} owed, behind for about a year. Check the record before deciding whether to reach out."))
    eq = p.get("est_equity")
    if eq:
        v = p.get("appraised_total") or 0
        out.append(("High equity potential" if eq > 40000 else "Some equity",
                    f"Est. equity ${eq:,.0f} ({eq / v:.0%} of county value ${v:,.0f}); no mortgage data in county records."))
    ms = p.get("mail_state")
    if ms and ms != (p.get("state") or "OH"):
        out.append(("Out-of-state owner", f"Tax bills go to {ms}. Mailing distance alone does not show selling interest."))
    elif p.get("owner_occupied") == 0:
        out.append(("Not owner-occupied", "Owner does not claim the owner-occupancy credit: likely a rental or vacant."))
    return out[:3]
