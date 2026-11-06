"""Owner contacts (phones/emails) collected from free sources.

Same number or email from several sources is stored once, with every source listed.
Sources: what the user pastes after a lookup, and Gemini with Google Search grounding.
"""
import json, re
from . import db, ai

PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?([2-9]\d{2})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def norm(kind, value):
    v = (value or "").strip()
    if kind == "phone":
        m = PHONE_RE.search(v)
        return ("".join(m.groups()), f"({m.group(1)}) {m.group(2)}-{m.group(3)}") if m else (None, None)
    if kind == "email":
        m = EMAIL_RE.search(v)
        return (m.group(0).lower(), m.group(0).lower()) if m else (None, None)
    return (None, None)


def add(pid, kind, value, source, note=""):
    n, pretty = norm(kind, value)
    if not n:
        return None
    from .jobs import now
    row = db.q1("SELECT * FROM contacts WHERE parcel_id=? AND kind=? AND norm=?", (pid, kind, n))
    if row:
        src = json.loads(row["sources"] or "[]")
        if source and source not in src:
            src.append(source)
        db.run("UPDATE contacts SET sources=?, note=COALESCE(NULLIF(note,''),?) WHERE id=?", (json.dumps(src), note, row["id"]))
    else:
        db.run("INSERT INTO contacts(parcel_id,kind,value,norm,sources,note,created) VALUES(?,?,?,?,?,?,?)",
               (pid, kind, pretty, n, json.dumps([source] if source else []), note, now()))
    return n


def add_text(pid, text, source):
    """Paste anything (a block copied from a people-search page): every phone and email in it is saved."""
    found = []
    text = text or ""
    for kind, rx in (("phone", PHONE_RE), ("email", EMAIL_RE)):
        for m in rx.finditer(text):
            n = add(pid, kind, m.group(0), source, label(text, m.start(), m.end()) if kind == "phone" else "")
            if n and n not in found:
                found.append(n)
    return found


def label(text, a, b):
    """Words right around a number: cell / landline / old."""
    before = text[max(0, a - 30):a].lower()
    before = re.split(r"[.;\n]|\band\b", before)[-1]  # only the same clause
    after = re.split(r"[,.;\n]|\band\b", text[b:b + 25].lower())[0]
    ctx = before + " " + after
    kind = "cell" if re.search(r"cell|mobile|wireless", ctx) else "landline" if re.search(r"landline|land line|home", ctx) else ""
    old = bool(re.search(r"previous|former|\bold\b|past|prior", ctx))
    return " ".join(x for x in [kind, "(old)" if old else ""] if x)


def list_for(pid):
    rows = db.q("SELECT * FROM contacts WHERE parcel_id=? ORDER BY kind DESC, id", (pid,))
    for r in rows:
        r["sources"] = json.loads(r["sources"] or "[]")
    rows.sort(key=lambda r: (r["kind"] != "phone", -len(r["sources"]), r["id"]))
    return rows


def _host(url):
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else (url or "web")


def _names(owner):
    """County 'POWELL DAVID E & MARY' -> ('Powell David E', 'David E Powell', 'David Powell')."""
    o = re.split(r"\s*&\s*|\s+AND\s+", (owner or "").strip())[0]
    o = re.sub(r"\b(ETAL|ET AL|TRUSTEE|TRUST|TR|JR|SR|LIFE EST(ATE)?)\b\.?", "", o, flags=re.I).split()
    if len(o) < 2 or re.search(r"\b(LLC|INC|CORP|CO|LTD|BANK|CHURCH|COUNTY|CITY)\b", " ".join(o), re.I):
        n = " ".join(o).title()
        return n, n, n
    last, first, rest = o[0].title(), o[1].title(), " ".join(o[2:]).title()
    return f"{last} {first} {rest}".strip(), f"{first} {rest} {last}".replace("  ", " ").strip(), f"{first} {last}"


def ai_find(p, owner_name, city, state):
    """Gemini + Google Search: public phones/emails for the owner, the way a person would google them."""
    county_form, full, short = _names(p.get("owner_name"))
    mail = (p.get("mail_address") or "").title()
    city = city or (p.get("city") or "").title()
    state = state or p.get("state") or "OH"
    prompt = f"""You are a skip tracer for a real estate investor. Find the phone numbers and emails of this property owner using Google Search.
Owner: {full} (county record writes it as "{county_form}")
Owner mailing address: {mail}
Owner city/state: {city}, {state}
Property owned: {p.get('street')}, {p.get('city') or ''} {p.get('state') or 'OH'} {p.get('zip') or ''}

Run several Google searches, for example:
1. "{county_form}" {city} {state} phone
2. "{short}" "{mail.split(',')[0] if mail else p.get('street')}"
3. "{full}" {city} {state} whitepages OR truepeoplesearch OR fastpeoplesearch
4. "{short}" {p.get('street')} {p.get('city') or ''} Ohio
Public records and people-search pages (Whitepages, TruePeopleSearch, FastPeopleSearch, Spokeo, Radaris, ThatsThem, etc.) are good sources.
Accept a phone or email when that page or snippet shows this name together with the mailing address, the property address, or that city.
Include current and older numbers (mark type and whether current). Never invent a number: only ones you saw in search results.
Reply with JSON only, no other text:
{{"phones":[{{"number":"","type":"cell|landline|unknown","current":true,"source_url":"","why":"short: which page and what matched"}}],
  "emails":[{{"email":"","source_url":"","why":""}}],
  "notes":"one short line: age, relatives, other addresses, or company agent if the owner is a company"}}"""
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096, "thinkingConfig": {"thinkingBudget": 1024}},
    }
    import time
    for attempt in range(3):
        r = ai.requests.post(ai.API.format(model=ai.model()), params={"key": ai.key()}, timeout=120, json=body)
        if r.status_code in (429, 500, 503):  # busy: wait and retry
            time.sleep(4 * (attempt + 1)); continue
        if r.status_code != 200 or (r.json()["candidates"][0].get("groundingMetadata") or {}).get("groundingChunks"):
            break
    if r.status_code != 200:
        raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:300]}")
    cand = r.json()["candidates"][0]
    text = "".join(x.get("text", "") for x in cand.get("content", {}).get("parts", []))
    grounded = [c.get("web", {}) for c in (cand.get("groundingMetadata") or {}).get("groundingChunks", [])]
    m = re.search(r"\{.*\}", text, re.S)
    data = {}
    if m:
        try:
            data = json.loads(m.group(0))
        except ValueError:
            data = {}
    titles = {g.get("uri"): g.get("title") for g in grounded}

    def tag_for(src):
        # grounding links are google redirect URLs; the chunk title is the real site (e.g. whitepages.com)
        site = titles.get(src) or (_host(src) if src and "vertexaisearch" not in src else "")
        return f"Gemini: {site}" if site else "Gemini search"
    added = 0
    if not grounded:  # no real search happened: do not trust anything
        return {"added": 0, "notes": "Gemini did not run a web search for this one. Try again.", "searched": []}
    for ph in data.get("phones") or []:
        tag = tag_for(ph.get("source_url") or "")
        label = " ".join(x for x in [ph.get("type") if ph.get("type") != "unknown" else "", "" if ph.get("current", True) else "(old)", ph.get("why") or ""] if x)
        if add(p["id"], "phone", ph.get("number"), tag, label):
            added += 1
    for em in data.get("emails") or []:
        tag = tag_for(em.get("source_url") or "")
        if add(p["id"], "email", em.get("email"), tag, em.get("why") or ""):
            added += 1
    notes = (data.get("notes") or "").strip()
    mark(p["id"])
    return {"added": added, "notes": notes, "searched": [g.get("title") for g in grounded if g.get("title")][:6]}


def mark(pid):
    """found = we have at least one phone/email; private = searched, nothing public."""
    from .jobs import now
    has = db.q1("SELECT COUNT(*) n FROM contacts WHERE parcel_id=?", (pid,))["n"]
    db.run("UPDATE parcels SET contact_status=?, contact_checked=? WHERE id=?", ("found" if has else "private", now(), pid))


class QuotaHit(Exception):
    pass


def run_batch(status_cb=None):
    """After a sync: search owners not searched yet, best scores first, up to the daily limit."""
    cfg = db.get_setting("contact_lookup") or {}
    if not cfg.get("enabled", True) or not ai.enabled():
        return {"done": 0, "skipped": "off"}
    import datetime as dt, time
    today = dt.date.today().isoformat()
    used = db.q1("SELECT COUNT(*) n FROM parcels WHERE contact_checked LIKE ? AND contact_status IN ('found','private')", (today + "%",))["n"]
    left = max(0, int(cfg.get("per_day", 50)) - used)
    rows = db.q("""SELECT p.* FROM parcels p WHERE p.is_active=1 AND p.demo=0 AND p.contact_status IS NULL
                   AND COALESCE(TRIM(p.owner_name),'') <> '' AND p.score>=?
                   ORDER BY p.score DESC LIMIT ?""", (int(cfg.get("min_score", 0)), left))
    done = found = 0
    for i, p in enumerate(rows):
        if status_cb:
            status_cb(i, len(rows))
        try:
            r = ai_find(p, "", "", "")
            done += 1
            found += 1 if r.get("added") else 0
            if r.get("notes"):
                from .jobs import now
                db.run("INSERT INTO activities(parcel_id,ts,kind,text,author) VALUES(?,?,?,?,?)",
                       (p["id"], now(), "note", "Gemini contact search: " + r["notes"], "Gemini"))
        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg.lower() or "RESOURCE_EXHAUSTED" in msg:
                break  # free limit reached for today; the rest go tomorrow
            continue
        time.sleep(4)  # stay under the free per-minute limit
    return {"done": done, "found": found}
