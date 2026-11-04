import csv, datetime as dt, io, json, os, re

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import db, scoring, ai, notify, jobs, demo, geocode, contacts, auth, ctx, plans, site
from .counties import KNOWN_ISSG
from .scraper.issg import IssgClient

ROOT = db.ROOT
ENV_PATH = os.path.join(ROOT, ".env")
load_dotenv(ENV_PATH)
WEB = os.path.join(ROOT, "web")

app = FastAPI(title="EstateHawk", docs_url=None, redoc_url=None)
app.middleware("http")(auth.middleware)
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
app.add_middleware(GZipMiddleware, minimum_size=800)


@app.middleware("http")
async def cache_headers(request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith("/site/"):  # website images and fonts: change rarely
        resp.headers["Cache-Control"] = "public, max-age=604800"
    return resp


@app.middleware("http")
async def canonical_host(request, call_next):
    """Pages on the old onrender address move to the real domain, so Google sees one site. The API stays on both."""
    host = (request.url.hostname or "").lower()
    if host.endswith(".onrender.com") and request.method in ("GET", "HEAD") and not request.url.path.startswith("/api/"):
        from fastapi.responses import RedirectResponse
        q = ("?" + request.url.query) if request.url.query else ""
        return RedirectResponse(site.CANONICAL + request.url.path + q, status_code=301)
    return await call_next(request)


# ------------------------------------------------------------------ login + team
def _client_ip(request):
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")


@app.get("/api/auth/me")
def auth_me(request: Request):
    u = auth.current(request)
    if not u:
        return JSONResponse({"user": None, "setup": not auth.users_exist()}, status_code=401)
    return {"user": u, "org": plans.org_info(u.get("org_id") or 1)}


@app.post("/api/auth/setup")
async def auth_setup(request: Request):
    if auth.users_exist():
        raise HTTPException(400, "Admin already created. Please log in.")
    b = await request.json()
    email, pw = (b.get("email") or "").strip().lower(), b.get("password") or ""
    if "@" not in email or len(pw) < 8:
        raise HTTPException(400, "Enter an email and a password of at least 8 characters")
    db.con()  # makes sure company #1 (EstateHawk HQ) exists
    db.run("INSERT INTO users(email,name,pw,role,created,org_id) VALUES(?,?,?,?,?,1)",
           (email, (b.get("name") or "").strip() or email.split("@")[0], auth.hash_pw(pw), "superadmin", jobs.now()))
    u = db.q1("SELECT id FROM users WHERE email=?", (email,))
    resp = JSONResponse({"ok": True})
    auth.set_cookie(resp, request, u["id"])
    return resp


@app.post("/api/auth/login")
async def auth_login(request: Request):
    ip = _client_ip(request)
    auth.throttle(ip)
    b = await request.json()
    u = db.q1("SELECT * FROM users WHERE email=?", ((b.get("email") or "").strip().lower(),))
    if not u or not u["active"] or not auth.check_pw(b.get("password") or "", u["pw"]):
        auth.failed(ip)
        raise HTTPException(401, "Wrong email or password")
    o = db.q1("SELECT status FROM orgs WHERE id=?", (u.get("org_id") or 1,))
    if o and o["status"] == "suspended" and u["role"] != "superadmin":
        raise HTTPException(403, "Your company account is paused. Contact EstateHawk.")
    db.run("UPDATE users SET last_login=? WHERE id=?", (jobs.now(), u["id"]))
    auth.audit("login", "", user=u, org=u.get("org_id"), ip=ip)
    resp = JSONResponse({"ok": True})
    auth.set_cookie(resp, request, u["id"])
    return resp


@app.post("/api/auth/signup")
async def auth_signup(request: Request):
    """Self-serve sign up from the website: a new company on a 14-day trial with one county, and its admin login."""
    ip = _client_ip(request)
    auth.throttle(ip)
    b = await request.json()
    if b.get("website"):  # honeypot field: bots fill it
        raise HTTPException(400, "Something went wrong. Please try again.")
    name = (b.get("name") or "").strip()[:80]
    email, pw = (b.get("email") or "").strip().lower()[:120], b.get("password") or ""
    if not name or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Enter your name and a valid email.")
    if len(pw) < 8:
        raise HTTPException(400, "Choose a password of at least 8 characters.")
    if db.q1("SELECT 1 FROM users WHERE email=?", (email,)):
        auth.failed(ip)
        raise HTTPException(400, "This email already has an account. Sign in instead.")
    try:
        cid = int(b.get("county_id") or 0)
    except ValueError:
        cid = 0
    if not db.q1("SELECT 1 FROM counties WHERE id=? AND enabled=1 AND demo=0", (cid,)):
        raise HTTPException(400, "Choose your first county.")
    ends = (dt.date.today() + dt.timedelta(days=plans.PLANS["trial"]["days"])).isoformat()
    company = (b.get("company") or "").strip()[:80] or f"{name}'s team"
    oid = db.run("INSERT INTO orgs(name,plan,status,trial_ends,created,notes) VALUES(?,?,?,?,?,?)",
                 (company, "trial", "active", ends, jobs.now(), "Signed up on the website"))
    db.run("INSERT INTO org_counties(org_id, county_id) VALUES(?,?)", (oid, cid))
    uid = db.run("INSERT INTO users(email,name,pw,role,created,org_id) VALUES(?,?,?,?,?,?)",
                 (email, name, auth.hash_pw(pw), "admin", jobs.now(), oid))
    u = db.q1("SELECT * FROM users WHERE email=?", (email,))
    auth.audit("signed up", f"{company} ({email}) trial", user=u, org=oid, ip=ip)
    resp = JSONResponse({"ok": True})
    auth.set_cookie(resp, request, u["id"] if u else uid)
    return resp


@app.post("/api/public/contact")
async def public_contact(request: Request):
    ip = _client_ip(request)
    auth.throttle(ip)
    b = await request.json()
    if b.get("website"):
        return {"ok": True}
    email, msg = (b.get("email") or "").strip()[:120], (b.get("message") or "").strip()[:2000]
    if "@" not in email or len(msg) < 3:
        raise HTTPException(400, "Enter your email and a message.")
    auth.audit("website message", f"{(b.get('name') or '').strip()[:80]} <{email}>: {msg}", org=1, ip=ip)
    auth.failed(ip)  # counts toward the hourly limit, stops floods
    return {"ok": True}


@app.post("/api/auth/logout")
def auth_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE)
    return resp


@app.post("/api/auth/password")
async def auth_password(request: Request):
    u = auth.current(request)
    if not u:
        raise HTTPException(401, "Please log in")
    b = await request.json()
    row = db.q1("SELECT pw FROM users WHERE id=?", (u["id"],))
    if not auth.check_pw(b.get("old") or "", row["pw"]):
        raise HTTPException(400, "Current password is wrong")
    if len(b.get("new") or "") < 8:
        raise HTTPException(400, "New password needs at least 8 characters")
    db.run("UPDATE users SET pw=? WHERE id=?", (auth.hash_pw(b["new"]), u["id"]))
    return {"ok": True}


def _team_org():
    return ctx.org_id()


@app.get("/api/users")
def users_list():
    return db.q("SELECT id, email, name, role, active, created, last_login FROM users WHERE org_id=? ORDER BY id", (_team_org(),))


def _user_in_my_org(uid):
    u = db.q1("SELECT * FROM users WHERE id=?", (uid,))
    if not u or (u["org_id"] != _team_org() and not ctx.get().get("super")):
        raise HTTPException(404, "User not found")
    if u["role"] == "superadmin" and not ctx.get().get("super"):
        raise HTTPException(403, "Not allowed")
    return u


@app.post("/api/users")
async def users_add(request: Request):
    b = await request.json()
    email, pw = (b.get("email") or "").strip().lower(), b.get("password") or ""
    if "@" not in email or len(pw) < 8:
        raise HTTPException(400, "Enter an email and a temporary password of at least 8 characters")
    if db.q1("SELECT 1 FROM users WHERE email=?", (email,)):
        raise HTTPException(400, "This email already has an account")
    info = ctx.get()["org"]
    limit = info["limits"]["users"]
    if limit and info["users"] >= limit and not ctx.get().get("super"):
        raise HTTPException(402, f"Your {info['label']} plan allows {limit} user(s). Upgrade to add more.")
    db.run("INSERT INTO users(email,name,pw,role,created,org_id) VALUES(?,?,?,?,?,?)",
           (email, (b.get("name") or "").strip() or email.split("@")[0], auth.hash_pw(pw),
            b.get("role") if b.get("role") in ("admin", "member") else "member", jobs.now(), _team_org()))
    return {"ok": True}


@app.put("/api/users/{uid}")
async def users_edit(uid: int, request: Request):
    b = await request.json()
    me = request.state.user
    _user_in_my_org(uid)
    if uid == me["id"] and (b.get("active") is False or b.get("role") == "member"):
        raise HTTPException(400, "You cannot remove your own admin access")
    if "active" in b:
        db.run("UPDATE users SET active=? WHERE id=?", (1 if b["active"] else 0, uid))
    if b.get("role") in ("admin", "member"):
        db.run("UPDATE users SET role=? WHERE id=?", (b["role"], uid))
    if b.get("password"):
        if len(b["password"]) < 8:
            raise HTTPException(400, "Password needs at least 8 characters")
        db.run("UPDATE users SET pw=? WHERE id=?", (auth.hash_pw(b["password"]), uid))
    return {"ok": True}


@app.delete("/api/users/{uid}")
def users_delete(uid: int, request: Request):
    if uid == request.state.user["id"]:
        raise HTTPException(400, "You cannot delete yourself")
    _user_in_my_org(uid)
    db.run("DELETE FROM users WHERE id=?", (uid,))
    return {"ok": True}


@app.on_event("startup")
def _startup():
    db.con()
    db.load_env()
    if os.environ.get("ESTATEHAWK_NO_SCHEDULER") != "1":
        jobs.start_scheduler()


def body(req_json):
    return req_json or {}


# ------------------------------------------------------------------ helpers
STAGES = ["new", "contacted", "replied", "negotiating", "under_contract", "closed"]
STAGE_LABEL = {"new": "New lead", "contacted": "Contacted", "replied": "Replied", "negotiating": "Negotiating",
               "under_contract": "Under contract", "closed": "Closed"}


def OID():
    return int(ctx.org_id() or 1)


def INFO():
    return ctx.get().get("org") or plans.org_info(OID())


def allowed_counties():
    """None = every county; else the list this company pays for."""
    return INFO()["counties"]


def county_filter(county, alias="p"):
    allowed = allowed_counties()
    s, a = "", []
    if allowed is not None:
        s = f" AND {alias}.county_id IN ({','.join(str(int(c)) for c in allowed) or '0'})"
    if county and str(county) not in ("all", "0", ""):
        s += f" AND {alias}.county_id=?"; a.append(int(county))
    return s, a


def apply_mask(rows):
    """Trial: leads not yet revealed show money and score but not owner or address."""
    info = INFO()
    if not info["limits"]["reveals"]:
        return rows
    seen = plans.revealed_set(info, [r["id"] for r in rows]) or set()
    return [r if r["id"] in seen else plans.mask(r) for r in rows]


def require_unlocked(pid):
    if plans.is_locked(INFO(), pid):
        raise HTTPException(403, "Reveal this lead first (free trial).")


def require_export():
    if not INFO()["limits"]["export"]:
        raise HTTPException(402, "Exports and letters are on paid plans. Upgrade to use them.")


def parcel_where(params):
    w, a = " WHERE 1=1", []
    s, x = county_filter(params.get("county")); w += s; a += x
    if params.get("active", "1") == "1":
        w += " AND p.is_active=1"
    if params.get("min_score"):
        w += " AND p.score>=?"; a.append(float(params["min_score"]))
    if params.get("min_equity"):
        w += " AND COALESCE(p.est_equity,0)>=?"; a.append(float(params["min_equity"]))
    if params.get("min_owed"):
        w += " AND COALESCE(p.total_due,p.amount_owed,0)>=?"; a.append(float(params["min_owed"]))
    if params.get("max_owed"):
        w += " AND COALESCE(p.total_due,p.amount_owed,0)<=?"; a.append(float(params["max_owed"]))
    if params.get("min_years"):
        w += " AND COALESCE(p.years_behind,1)>=?"; a.append(float(params["min_years"]))
    if params.get("ptype") and params["ptype"] != "all":
        if params["ptype"] == "homes":
            # many county lists do not say what the property is: keep "unknown" ones instead of hiding whole counties
            w += " AND (p.property_type IN ('Single family','Residential') OR p.property_type IS NULL OR p.property_type IN ('Unknown','Other'))"
        else:
            w += " AND p.property_type=?"; a.append(params["ptype"])
    if params.get("out_of_state") == "1":
        w += " AND p.mail_state IS NOT NULL AND p.mail_state != p.state"
    if params.get("new_days"):
        w += " AND p.first_seen>=?"; a.append((dt.date.today() - dt.timedelta(days=int(params["new_days"]))).isoformat())
    if params.get("q"):
        qq = f"%{params['q'].strip()}%"
        w += " AND (p.street LIKE ? OR p.owner_name LIKE ? OR p.parcel_number LIKE ? OR p.city LIKE ?)"; a += [qq] * 4
    return w, a


SORTS = {"score": "p.score DESC", "owed": "COALESCE(p.total_due,p.amount_owed) DESC", "equity": "p.est_equity DESC",
         "years": "p.years_behind DESC", "value": "p.appraised_total DESC", "newest": "p.first_seen DESC, p.score DESC"}

LIST_COLS = """p.id, p.county_id, p.parcel_number, p.owner_name, p.street, p.city, p.state, p.zip, p.amount_owed, p.total_due,
 p.years_behind, p.appraised_total, p.est_equity, p.score, p.lat, p.lng, p.property_type, p.mail_state, p.first_seen,
 p.is_active, p.demo, p.photo_url, p.beds, p.baths_full, p.living_area, p.year_built, p.contact_status, c.name AS county_name, pl.stage"""


def PL():
    """Join to this company's own pipeline row."""
    return f"LEFT JOIN pipeline pl ON pl.parcel_id=p.id AND pl.org_id={OID()}"


# ------------------------------------------------------------------ meta / stats
@app.get("/api/meta")
def meta():
    s = db.all_settings()
    cf, _ = county_filter(None)
    counts = db.q1(f"SELECT COUNT(*) n, SUM(is_active) active FROM parcels p WHERE 1=1{cf}")
    c = ctx.get()
    return {"settings": s, "integrations": notify.configured(), "gemini_model": ai.model(),
            "counties": db.q(f"SELECT id, name, state, enabled, lat, lng FROM counties p WHERE 1=1{cf.replace('p.county_id', 'p.id')} ORDER BY name"),
            "parcels": counts["n"] or 0, "active": counts["active"] or 0, "sync": jobs.STATUS,
            "stages": [{"key": k, "label": STAGE_LABEL[k]} for k in STAGES],
            "last_sync": (db.q1("SELECT MAX(last_sync) t FROM counties") or {}).get("t"),
            "unread_alerts": unread_alerts(), "org": INFO(), "user": c.get("user"), "super": bool(c.get("super")),
            "plans": {k: plans.PLANS[k] for k in plans.PUBLIC}}


def unread_alerts():
    cf, _ = county_filter(None, "al")
    return db.q1(f"""SELECT COUNT(*) n FROM alerts al WHERE 1=1{cf} AND NOT EXISTS
                     (SELECT 1 FROM alert_reads r WHERE r.org_id={OID()} AND r.alert_id=al.id)""")["n"]


@app.get("/api/stats")
def stats(county: str = "all"):
    s, a = county_filter(county)
    t = dt.date.today().isoformat()
    y = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    new_today = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.first_seen=?{s}", [t] + a)["n"]
    new_y = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.first_seen=?{s}", [y] + a)["n"]
    hi = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.is_active=1 AND p.score>=80{s}", a)["n"]
    hi_wk = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.is_active=1 AND p.score>=80 AND p.first_seen<?{s}",
                  [(dt.date.today() - dt.timedelta(days=7)).isoformat()] + a)["n"]
    eq = db.q1(f"SELECT AVG(p.est_equity) v FROM parcels p WHERE p.is_active=1 AND p.est_equity>0 AND (p.property_type IN ('Single family','Residential') OR p.property_type IS NULL OR p.property_type IN ('Unknown','Other')){s}", a)["v"]
    cc, _ = county_filter(None, "counties")
    ct = db.q1(f"SELECT COUNT(*) n, COUNT(DISTINCT state) st FROM counties WHERE enabled=1{cc.replace('counties.county_id', 'counties.id')}")
    active = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.is_active=1{s}", a)["n"]
    pct = lambda n, o: (round((n - o) * 100 / o) if o else None)
    return {"new_today": new_today, "new_change": pct(new_today, new_y), "high_score": hi, "high_change": pct(hi, hi_wk),
            "avg_equity": round(eq or 0), "counties": ct["n"], "states": ct["st"], "active": active}


# ------------------------------------------------------------------ parcels
@app.get("/api/parcels")
def parcels(request: Request):
    params = dict(request.query_params)
    w, a = parcel_where(params)
    order = SORTS.get(params.get("sort", "score"), SORTS["score"])
    per = min(int(params.get("per", 25)), 500)
    page = max(int(params.get("page", 1)), 1)
    total = db.q1(f"SELECT COUNT(*) n FROM parcels p {w}", a)["n"]
    rows = db.q(f"""SELECT {LIST_COLS} FROM parcels p JOIN counties c ON c.id=p.county_id {PL()}
                   {w} ORDER BY {order} LIMIT ? OFFSET ?""", a + [per, (page - 1) * per])
    return {"total": total, "page": page, "per": per, "rows": apply_mask(rows)}


@app.get("/api/parcels/export.csv")
def export_parcels(request: Request):
    require_export()
    params = dict(request.query_params)
    w, a = parcel_where(params)
    rows = db.q(f"""SELECT c.name county, p.parcel_number, p.owner_name, p.owner_full_name, p.street, p.city, p.state, p.zip,
                   p.mail_address, p.mail_state, p.amount_owed, p.total_due, p.prior_due, p.annual_tax, p.years_behind,
                   p.appraised_total, p.est_equity, p.rent_est, p.suggested_offer, p.score, p.property_type, p.land_use,
                   p.first_seen, p.lat, p.lng FROM parcels p JOIN counties c ON c.id=p.county_id {w} ORDER BY p.score DESC""", a)
    buf = io.StringIO()
    if rows:
        wr = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        wr.writeheader(); wr.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=estatehawk-leads-{dt.date.today()}.csv"})


def get_parcel(pid, unlocked=False):
    cf, _ = county_filter(None)
    p = db.q1(f"""SELECT p.*, c.name county_name, c.host county_host, c.tax_sale_date, pl.stage, pl.fee
                 FROM parcels p JOIN counties c ON c.id=p.county_id {PL()} WHERE p.id=?{cf}""", (pid,))
    if not p:
        raise HTTPException(404, "Parcel not found")
    if unlocked:
        require_unlocked(pid)
    return p


@app.get("/api/parcels/{pid:path}/detail")
def parcel_detail(pid: str):
    p = get_parcel(pid)
    info = INFO()
    if plans.is_locked(info, pid):
        br = json.loads(p.get("score_breakdown") or "{}")
        p["score_parts"] = br.get("parts", {})
        p["reasons"] = scoring.reasons(p, br)
        p = plans.mask(p)
        p.update(snapshots=[], activities=[], offers=[], tasks=[], contacts=[], offer_defaults=db.get_setting("offer_defaults"),
                 ai=False, reveals_left=info["reveals_left"], reveals_total=info["limits"]["reveals"])
        p["reasons"] = [(t, x) for t, x in p["reasons"] if "Tax bills go to" not in x] + ([("Out-of-state owner", "Owner lives in another state.")] if p.get("mail_state") and p.get("mail_state") != p.get("state") else [])
        return p
    if p.get("lat") is None and (p.get("street") or "")[:1].isdigit() and not p.get("demo"):
        ll = geocode.one(p["street"], p.get("city") or "", p.get("state") or "OH", p.get("zip") or "")
        if ll:
            db.run("UPDATE parcels SET lat=?, lng=? WHERE id=?", (ll[0], ll[1], pid))
            p["lat"], p["lng"] = ll
    br = json.loads(p.get("score_breakdown") or "{}")
    p["score_parts"] = br.get("parts", {})
    p["reasons"] = scoring.reasons(p, br)
    p["snapshots"] = db.q("SELECT date, amount, owner_name FROM snapshots WHERE parcel_id=? ORDER BY date", (pid,))
    p["activities"] = db.q("SELECT * FROM activities WHERE parcel_id=? AND (org_id=? OR org_id IS NULL) ORDER BY ts DESC", (pid, OID()))
    p["offers"] = db.q("SELECT * FROM offers WHERE parcel_id=? AND org_id=? ORDER BY id DESC", (pid, OID()))
    p["tasks"] = db.q("SELECT * FROM tasks WHERE parcel_id=? AND org_id=? ORDER BY done, due", (pid, OID()))
    p["reveals_left"] = info["reveals_left"]
    p["contacts"] = contacts.list_for(pid)
    p["offer_defaults"] = db.get_setting("offer_defaults")
    p["ai"] = ai.enabled()
    return p


@app.post("/api/parcels/{pid:path}/reveal")
def reveal(pid: str):
    get_parcel(pid)
    info = INFO()
    if not plans.is_locked(info, pid):
        return {"ok": True, "reveals_left": info["reveals_left"]}
    if info["reveals_left"] is not None and info["reveals_left"] <= 0:
        raise HTTPException(402, f"You have opened all {info['limits']['reveals']} free leads. Upgrade to see every lead.")
    db.run("INSERT INTO reveals(org_id,parcel_id,ts) VALUES(?,?,?)", (OID(), pid, jobs.now()))
    return {"ok": True, "reveals_left": plans.org_info(OID())["reveals_left"]}


@app.post("/api/parcels/{pid:path}/contacts")
async def add_contacts(pid: str, request: Request):
    get_parcel(pid, unlocked=True)
    b = await request.json()
    found = contacts.add_text(pid, b.get("text", ""), (b.get("source") or "Manual").strip()[:40])
    if found:
        contacts.mark(pid)
    elif b.get("searched"):
        contacts.mark(pid)  # searched, nothing public -> Private
    if b.get("summary"):
        db.run("INSERT INTO activities(parcel_id,ts,kind,text,author) VALUES(?,?,?,?,?)",
               (pid, jobs.now(), "note", "Google AI Overview: " + b["summary"][:600], "Google"))
    return {"found": found, "contacts": contacts.list_for(pid)}


@app.post("/api/parcels/{pid:path}/contacts/ai")
async def ai_contacts(pid: str, request: Request):
    p = get_parcel(pid, unlocked=True)
    if not ai.enabled():
        raise HTTPException(400, "Add a Gemini API key in Settings > Integrations")
    b = await request.json()
    try:
        res = contacts.ai_find(p, b.get("name", ""), b.get("city", ""), b.get("state", ""))
    except Exception as e:
        raise HTTPException(502, str(e)[:300])
    if res.get("notes"):
        db.run("INSERT INTO activities(parcel_id,ts,kind,text,author) VALUES(?,?,?,?,?)",
               (pid, jobs.now(), "note", "Gemini contact search: " + res["notes"], "Gemini"))
    res["contacts"] = contacts.list_for(pid)
    return res


@app.delete("/api/contacts/{cid}")
def del_contact(cid: int):
    row = db.q1("SELECT parcel_id FROM contacts WHERE id=?", (cid,))
    db.run("DELETE FROM contacts WHERE id=?", (cid,))
    if row:
        contacts.mark(row["parcel_id"])
    return {"ok": True}


@app.get("/api/parcels/{pid:path}/ai-reasons")
def parcel_ai_reasons(pid: str):
    p = get_parcel(pid, unlocked=True)
    if not ai.enabled():
        raise HTTPException(400, "Add a Gemini API key in Settings > Integrations")
    br = json.loads(p.get("score_breakdown") or "{}")
    try:
        return {"reasons": ai.ai_reasons(p, br.get("parts", {}))}
    except Exception as e:
        raise HTTPException(502, str(e)[:300])


@app.post("/api/parcels/{pid:path}/offer")
async def make_offer(pid: str, request: Request):
    p = get_parcel(pid, unlocked=True)
    b = await request.json()
    d = db.get_setting("offer_defaults")
    terms = {"price": float(b.get("price") or p.get("suggested_offer") or 0), "financing": b.get("financing") or d["financing"],
             "closing_days": int(b.get("closing_days") or d["closing_days"]), "earnest": float(b.get("earnest") or d["earnest"]),
             "seller_credits": b.get("seller_credits") or d["seller_credits"]}
    subject, text, source = ai.offer(p, terms, db.get_setting("profile"))
    oid = db.run("""INSERT INTO offers(parcel_id,created,price,financing,closing_days,earnest,seller_credits,subject,body,source,org_id)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (pid, jobs.now(), terms["price"], terms["financing"], terms["closing_days"],
                                                    terms["earnest"], terms["seller_credits"], subject, text, source, OID()))
    if not db.q1("SELECT 1 FROM pipeline WHERE parcel_id=? AND org_id=?", (pid, OID())):
        db.run("INSERT INTO pipeline(org_id,parcel_id,stage,updated_at) VALUES(?,?,?,?)", (OID(), pid, "new", jobs.now()))
    return db.q1("SELECT * FROM offers WHERE id=?", (oid,))


@app.put("/api/offers/{oid}")
async def edit_offer(oid: int, request: Request):
    b = await request.json()
    db.run("UPDATE offers SET subject=?, body=? WHERE id=? AND org_id=?", (b.get("subject", ""), b.get("body", ""), oid, OID()))
    return db.q1("SELECT * FROM offers WHERE id=?", (oid,))


@app.post("/api/parcels/{pid:path}/stage")
async def set_stage(pid: str, request: Request):
    get_parcel(pid, unlocked=True)
    b = await request.json()
    st = b.get("stage")
    if st not in STAGES and st != "remove":
        raise HTTPException(400, "bad stage")
    if st == "remove":
        db.run("DELETE FROM pipeline WHERE parcel_id=? AND org_id=?", (pid, OID()))
        return {"ok": True}
    fee = b.get("fee")
    db.run("""INSERT INTO pipeline(org_id,parcel_id,stage,updated_at,fee,closed_at) VALUES(?,?,?,?,?,?)
              ON CONFLICT(org_id,parcel_id) DO UPDATE SET stage=excluded.stage, updated_at=excluded.updated_at,
              fee=COALESCE(excluded.fee, pipeline.fee), closed_at=COALESCE(excluded.closed_at, pipeline.closed_at)""",
           (OID(), pid, st, jobs.now(), fee, dt.date.today().isoformat() if st == "closed" else None))
    db.run("INSERT INTO activities(parcel_id,ts,kind,text,author,org_id) VALUES(?,?,?,?,?,?)",
           (pid, jobs.now(), "stage", f"Moved to {STAGE_LABEL[st]}", me_name(), OID()))
    return {"ok": True}


@app.post("/api/parcels/{pid:path}/activity")
async def add_activity(pid: str, request: Request):
    get_parcel(pid, unlocked=True)
    b = await request.json()
    kind = b.get("kind", "note")
    db.run("INSERT INTO activities(parcel_id,ts,kind,text,author,org_id) VALUES(?,?,?,?,?,?)",
           (pid, jobs.now(), kind, b.get("text", ""), b.get("author") or me_name(), OID()))
    for want, from_stages in (("contacted", ("new",)), ("replied", ("new", "contacted"))):
        if (want == "contacted" and kind in ("email", "call", "sms", "letter") and not b.get("no_stage")) or (want == "replied" and kind == "reply"):
            cur = db.q1("SELECT stage FROM pipeline WHERE parcel_id=? AND org_id=?", (pid, OID()))
            if not cur or cur["stage"] in from_stages:
                db.run("""INSERT INTO pipeline(org_id,parcel_id,stage,updated_at) VALUES(?,?,?,?)
                          ON CONFLICT(org_id,parcel_id) DO UPDATE SET stage=excluded.stage, updated_at=excluded.updated_at""",
                       (OID(), pid, want, jobs.now()))
    return {"ok": True}


def me_name():
    u = ctx.get().get("user") or {}
    return u.get("name") or db.get_setting("profile").get("name")


@app.get("/api/map")
def map_points(request: Request):
    params = dict(request.query_params)
    w, a = parcel_where(params)
    return apply_mask(db.q(f"""SELECT {LIST_COLS} FROM parcels p JOIN counties c ON c.id=p.county_id {PL()}
                   {w} AND p.lat IS NOT NULL ORDER BY p.score DESC LIMIT 3000""", a))


# ------------------------------------------------------------------ alerts
ALERT_TYPES = {"new_delinquent": "New delinquent", "auction": "Auction dates", "owner_change": "Owner changes",
               "amount_up": "Equity changes", "high_score": "High score", "paid_off": "Paid off"}


@app.get("/api/alerts")
def alerts(type: str = "all", county: str = "all", limit: int = 200):
    cf, _ = county_filter(None, "al")
    w, a = " WHERE 1=1" + cf, []
    if type != "all":
        if type == "equity":
            w += " AND al.type IN ('amount_up','high_score')"
        else:
            w += " AND al.type=?"; a.append(type)
    if county not in ("all", ""):
        w += " AND al.county_id=?"; a.append(int(county))
    rows = db.q(f"""SELECT al.id, al.ts, al.type, al.county_id, al.parcel_id, al.title, al.body, al.score, al.sent,
                    CASE WHEN EXISTS (SELECT 1 FROM alert_reads r WHERE r.org_id={OID()} AND r.alert_id=al.id) THEN 1 ELSE 0 END AS read,
                    c.name county_name, p.street, p.city FROM alerts al LEFT JOIN counties c ON c.id=al.county_id
                    LEFT JOIN parcels p ON p.id=al.parcel_id {w} ORDER BY al.ts DESC LIMIT ?""", a + [limit])
    info = INFO()
    if info["limits"]["reveals"]:
        seen = plans.revealed_set(info, [r["parcel_id"] for r in rows if r["parcel_id"]]) or set()
        for r in rows:
            if r["parcel_id"] and r["parcel_id"] not in seen:
                r["street"] = "Address hidden"
                r["title"] = re.sub(r"\d+ [A-Z0-9 ]+(ST|RD|AVE|DR|LN|CT|PIKE|BLVD|WAY|PL|CIR)\b", "a property", r["title"] or "", flags=re.I)
    counts = {r["type"]: r["n"] for r in db.q(f"SELECT al.type, COUNT(*) n FROM alerts al WHERE 1=1{cf} GROUP BY al.type")}
    return {"rows": rows, "counts": counts, "unread": unread_alerts()}


@app.post("/api/alerts/read")
async def alerts_read(request: Request):
    b = await request.json()
    if b.get("all"):
        cf, _ = county_filter(None, "al")
        db.run(f"""INSERT INTO alert_reads(org_id, alert_id) SELECT {OID()}, al.id FROM alerts al WHERE 1=1{cf}
                   AND NOT EXISTS (SELECT 1 FROM alert_reads r WHERE r.org_id={OID()} AND r.alert_id=al.id)""")
    else:
        for i in b.get("ids", []):
            if not db.q1("SELECT 1 FROM alert_reads WHERE org_id=? AND alert_id=?", (OID(), int(i))):
                db.run("INSERT INTO alert_reads(org_id, alert_id) VALUES(?,?)", (OID(), int(i)))
    return {"ok": True}


# ------------------------------------------------------------------ counties + sync
@app.get("/api/counties")
def counties():
    cf, _ = county_filter(None, "x")
    rows = db.q(f"SELECT * FROM counties x WHERE 1=1{cf.replace('x.county_id', 'x.id')} ORDER BY name")
    start = (dt.date.today() - dt.timedelta(days=29))
    t = dt.date.today().isoformat()
    for c in rows:
        per = {r["d"]: r["n"] for r in db.q("SELECT first_seen d, COUNT(*) n FROM parcels WHERE county_id=? AND first_seen>=? GROUP BY first_seen",
                                            (c["id"], start.isoformat()))}
        c["spark"] = [per.get((start + dt.timedelta(days=i)).isoformat(), 0) for i in range(30)]
        c["new_today"] = per.get(t, 0)
        c["active"] = db.q1("SELECT COUNT(*) n FROM parcels WHERE county_id=? AND is_active=1", (c["id"],))["n"]
        c["last_run"] = db.q1("SELECT * FROM sync_runs WHERE county_id=? ORDER BY id DESC LIMIT 1", (c["id"],))
    return rows


@app.get("/api/known-counties")
def known():
    have = {r["host"] for r in db.q("SELECT host FROM counties")}
    return [dict(k, added=k["host"] in have) for k in KNOWN_ISSG]


@app.post("/api/counties")
async def add_county(request: Request):
    b = await request.json()
    host = re.sub(r"^https?://", "", (b.get("host") or "").strip()).split("/")[0]
    if not b.get("name"):
        raise HTTPException(400, "Name required")
    cid = db.run("INSERT INTO counties(name,state,host,lat,lng,tax_sale_date) VALUES(?,?,?,?,?,?)",
                 (b["name"], b.get("state", "OH"), host, b.get("lat"), b.get("lng"), b.get("tax_sale_date") or None))
    return db.q1("SELECT * FROM counties WHERE id=?", (cid,))


@app.put("/api/counties/{cid}")
async def edit_county(cid: int, request: Request):
    b = await request.json()
    for k in ("name", "state", "host", "enabled", "tax_sale_date", "lat", "lng"):
        if k in b:
            db.run(f"UPDATE counties SET {k}=? WHERE id=?", (b[k], cid))
    return db.q1("SELECT * FROM counties WHERE id=?", (cid,))


@app.delete("/api/counties/{cid}")
def del_county(cid: int):
    if db.q1("SELECT 1 FROM parcels WHERE county_id=? AND demo=0", (cid,)):
        db.run("UPDATE counties SET enabled=0 WHERE id=?", (cid,))
        return {"ok": True, "disabled": True}
    db.run("DELETE FROM parcels WHERE county_id=?", (cid,))
    db.run("DELETE FROM counties WHERE id=?", (cid,))
    return {"ok": True}


@app.post("/api/counties/test")
async def test_county(request: Request):
    b = await request.json()
    host = re.sub(r"^https?://", "", (b.get("host") or "").strip()).split("/")[0]
    try:
        subs = IssgClient(host, delay=0).polsubs()
        return {"ok": True, "townships": len(subs), "parcels": sum(n or 0 for _, n, _h in subs)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


@app.post("/api/sync")
async def sync(request: Request):
    try:
        b = await request.json()
    except Exception:
        b = {}
    if jobs.STATUS.get("running"):
        return {"ok": False, "error": "Sync already running"}
    jobs.sync_in_background(b.get("ids"))
    return {"ok": True}


@app.get("/api/sync/status")
def sync_status():
    return jobs.STATUS


# ------------------------------------------------------------------ pipeline + tasks
@app.get("/api/pipeline")
def pipeline(county: str = "all", q: str = ""):
    s, a = county_filter(county)
    if q:
        s += " AND (p.street LIKE ? OR p.owner_name LIKE ?)"; a += [f"%{q}%"] * 2
    o = OID()
    rows = db.q(f"""SELECT pl.*, p.street, p.city, p.zip, p.owner_name, p.score, p.lat, p.lng, p.county_id, p.total_due, p.amount_owed,
                    (SELECT kind||'|'||ts||'|'||text FROM activities x WHERE x.parcel_id=p.id AND x.org_id={o} ORDER BY ts DESC LIMIT 1) last
                    FROM pipeline pl JOIN parcels p ON p.id=pl.parcel_id WHERE pl.org_id={o}{s} ORDER BY pl.updated_at DESC""", a)
    cols = {k: [] for k in STAGES}
    for r in rows:
        cols.setdefault(r["stage"], []).append(r)
    wk = (dt.datetime.now() - dt.timedelta(days=7)).isoformat(sep=" ")
    sent = db.q1(f"SELECT COUNT(DISTINCT parcel_id) n FROM activities WHERE org_id={o} AND kind IN ('email','call','sms','letter') AND ts>=?", (wk,))["n"]
    rep = db.q1(f"SELECT COUNT(DISTINCT parcel_id) n FROM activities WHERE org_id={o} AND kind='reply' AND ts>=?", (wk,))["n"]
    replies = db.q(f"""SELECT x.*, p.street, p.city FROM activities x JOIN parcels p ON p.id=x.parcel_id WHERE x.org_id={o} AND x.kind='reply'
                      ORDER BY x.ts DESC LIMIT 6""")
    return {"columns": [{"key": k, "label": STAGE_LABEL[k], "items": cols.get(k, [])} for k in STAGES],
            "reply_rate": round(rep * 100 / sent) if sent else 0, "replies_week": rep, "contacts_week": sent, "recent_replies": replies}


@app.get("/api/tasks")
def tasks(scope: str = "today"):
    w = f" WHERE t.org_id={OID()}" + ("" if scope == "all" else " AND (t.done=0 OR t.due>=date('now','-1 day'))")
    return db.q(f"""SELECT t.*, p.street, p.city, p.owner_name FROM tasks t LEFT JOIN parcels p ON p.id=t.parcel_id {w}
                    ORDER BY t.done, t.due LIMIT 50""")


@app.post("/api/tasks")
async def add_task(request: Request):
    b = await request.json()
    if b.get("parcel_id"):
        get_parcel(b["parcel_id"], unlocked=True)
    tid = db.run("INSERT INTO tasks(parcel_id,due,text,kind,org_id) VALUES(?,?,?,?,?)",
                 (b.get("parcel_id"), b.get("due") or dt.date.today().isoformat(), b.get("text", ""), b.get("kind", "call"), OID()))
    return db.q1("SELECT * FROM tasks WHERE id=?", (tid,))


@app.put("/api/tasks/{tid}")
async def edit_task(tid: int, request: Request):
    b = await request.json()
    db.run("UPDATE tasks SET done=? WHERE id=? AND org_id=?", (1 if b.get("done") else 0, tid, OID()))
    return {"ok": True}


@app.post("/api/batch-offers")
async def batch_offers(request: Request):
    require_export()
    b = await request.json()
    ids = b.get("ids") or [r["parcel_id"] for r in db.q("SELECT parcel_id FROM pipeline WHERE stage='new' AND org_id=?", (OID(),))]
    d = db.get_setting("offer_defaults")
    prof = db.get_setting("profile")
    made = 0
    for pid in ids[:200]:
        p = get_parcel(pid, unlocked=True)
        terms = {"price": p.get("suggested_offer") or 0, "financing": d["financing"], "closing_days": d["closing_days"],
                 "earnest": d["earnest"], "seller_credits": d["seller_credits"]}
        s, t, src = ai.offer(p, terms, prof) if b.get("ai") else (*ai.template_offer(p, terms, prof), "template")
        db.run("""INSERT INTO offers(parcel_id,created,price,financing,closing_days,earnest,seller_credits,subject,body,source,org_id)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (pid, jobs.now(), terms["price"], terms["financing"], terms["closing_days"],
                                                  terms["earnest"], terms["seller_credits"], s, t, src, OID()))
        made += 1
    return {"ok": True, "count": made, "ids": ids[:200]}


@app.get("/letters", response_class=HTMLResponse)
def letters(ids: str = ""):
    """Printable mail-merge letters (owner mailing address + latest offer). Print or save as PDF."""
    require_export()
    pids = [i for i in ids.split(",") if i] or [r["parcel_id"] for r in db.q("SELECT parcel_id FROM pipeline WHERE stage='new' AND org_id=?", (OID(),))]
    prof = db.get_setting("profile")
    pages = []
    import html as H
    for pid in pids:
        try:
            p = get_parcel(pid)
        except HTTPException:
            continue
        o = db.q1("SELECT * FROM offers WHERE parcel_id=? AND org_id=? ORDER BY id DESC LIMIT 1", (pid, OID()))
        if not p or not o:
            continue
        to = H.escape(p.get("owner_full_name") or p.get("owner_name") or "")
        addr = H.escape(p.get("mail_address") or f"{p['street']}, {p['city']} {p['state']} {p['zip']}")
        pages.append(f"""<section><p class=from>{H.escape(prof.get('name') or '')}<br>{H.escape(prof.get('company') or '')}<br>
        {H.escape(prof.get('phone') or '')} {H.escape(prof.get('email') or '')}</p><p>{dt.date.today():%B %d, %Y}</p>
        <p>{to}<br>{addr.replace(', ', '<br>', 1)}</p><p><b>Re: {H.escape(p['street'].title())}, {H.escape(p['city'].title())}</b></p>
        <pre>{H.escape(o['body'])}</pre></section>""")
    css = "body{font:15px/1.55 Georgia,serif;color:#222;margin:0}section{padding:64px 72px;page-break-after:always;max-width:720px}pre{white-space:pre-wrap;font:inherit}.from{color:#555}"
    return f"<!doctype html><title>Offer letters</title><style>{css}</style>{''.join(pages) or '<p style=padding:40px>No offers yet. Create offer drafts first.</p>'}<script>setTimeout(()=>print(),400)</script>"


# ------------------------------------------------------------------ reports
@app.get("/api/reports")
def reports(days: int = 30, county: str = "all"):
    start = dt.date.today() - dt.timedelta(days=days - 1)
    prev = start - dt.timedelta(days=days)
    s, a = county_filter(county)
    found = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.first_seen>=?{s}", [start.isoformat()] + a)["n"]
    found_prev = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.first_seen>=? AND p.first_seen<?{s}", [prev.isoformat(), start.isoformat()] + a)["n"]
    o = OID()
    stage_n = lambda sts: db.q1(f"SELECT COUNT(*) n FROM pipeline pl JOIN parcels p ON p.id=pl.parcel_id WHERE pl.org_id={o} AND pl.stage IN ({','.join('?' * len(sts))}){s}", list(sts) + a)["n"]
    contacted = stage_n(STAGES[1:]); replied = stage_n(STAGES[2:]); nego = stage_n(STAGES[3:]); closed = stage_n(["closed"])
    fees = db.q1(f"SELECT COALESCE(SUM(pl.fee),0) f FROM pipeline pl JOIN parcels p ON p.id=pl.parcel_id WHERE pl.org_id={o} AND pl.stage='closed'{s}", a)["f"]
    cc, _ = county_filter(None, "x")
    cs = db.q(f"SELECT id, name FROM counties x WHERE enabled=1{cc.replace('x.county_id', 'x.id')} ORDER BY name")
    per_day = {}
    for c in cs:
        per = {r["d"]: r["n"] for r in db.q("SELECT first_seen d, COUNT(*) n FROM parcels WHERE county_id=? AND first_seen>=? GROUP BY first_seen", (c["id"], start.isoformat()))}
        per_day[c["name"]] = [per.get((start + dt.timedelta(days=i)).isoformat(), 0) for i in range(days)]
    by_county = db.q(f"SELECT c.name, COUNT(p.id) n FROM counties c LEFT JOIN parcels p ON p.county_id=c.id AND p.is_active=1 WHERE 1=1{cc.replace('x.county_id', 'c.id')} GROUP BY c.id, c.name ORDER BY n DESC")
    top = db.q(f"""SELECT p.id, p.street, p.city, p.zip, p.owner_name, p.appraised_total, p.est_equity, p.lat, p.lng, c.name county, pl.stage, pl.fee, pl.closed_at, pl.updated_at
                   FROM pipeline pl JOIN parcels p ON p.id=pl.parcel_id JOIN counties c ON c.id=p.county_id
                   WHERE pl.org_id={o} AND pl.stage IN ('closed','under_contract','negotiating'){s} ORDER BY (pl.stage='closed') DESC, pl.fee DESC, p.score DESC LIMIT 8""", a)
    return {"kpi": {"found": found, "found_change": round((found - found_prev) * 100 / found_prev) if found_prev else None,
                    "contacted": contacted, "replied": replied, "reply_rate": round(replied * 100 / contacted) if contacted else 0,
                    "closed": closed, "fees": fees},
            "labels": [(start + dt.timedelta(days=i)).isoformat() for i in range(days)], "per_day": per_day,
            "by_county": by_county, "funnel": [["Found", found], ["Contacted", contacted], ["Replied", replied], ["Negotiating", nego], ["Closed", closed]],
            "top": top}


@app.get("/api/reports/export.csv")
def reports_csv(days: int = 30):
    require_export()
    r = reports(days)
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["metric", "value"])
    for k, v in r["kpi"].items():
        w.writerow([k, v])
    w.writerow([]); w.writerow(["date"] + list(r["per_day"].keys()))
    for i, d in enumerate(r["labels"]):
        w.writerow([d] + [r["per_day"][c][i] for c in r["per_day"]])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=estatehawk-report-{dt.date.today()}.csv"})


# ------------------------------------------------------------------ settings + integrations
@app.get("/api/settings")
def get_settings():
    return db.all_settings()


@app.put("/api/settings")
async def put_settings(request: Request):
    b = await request.json()
    rescore_needed = False
    is_super = bool(ctx.get().get("super"))
    for k, v in b.items():
        if k in db.DEFAULT_SETTINGS and (is_super or k in db.ORG_KEYS):
            if k in ("weights", "offer_defaults") and v != db.get_setting(k):
                rescore_needed = True
            db.set_setting(k, v)
    if rescore_needed:
        jobs.rescore(quiet=True)
    return db.all_settings()


@app.post("/api/settings/preview-score")
async def preview_score(request: Request):
    b = await request.json()
    pid = b.get("parcel_id") or (db.q1("SELECT id FROM parcels WHERE is_active=1 ORDER BY score DESC LIMIT 1") or {}).get("id")
    if not pid:
        return {"parcel": None}
    p = get_parcel(pid)
    s, br = scoring.score(p, b.get("weights") or db.get_setting("weights"))
    return {"parcel": {k: p.get(k) for k in ("id", "street", "city", "zip", "lat", "lng", "appraised_total", "est_equity", "total_due",
                                             "amount_owed", "years_behind", "mail_state", "owner_occupied")},
            "score": s, "parts": br["parts"], "factors": br["factors"], "labels": scoring.LABELS}


ENV_KEYS = ["GEMINI_API_KEY", "GEMINI_MODEL", "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "ALERT_EMAIL_TO",
            "SLACK_WEBHOOK_URL", "TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM", "TWILIO_WHATSAPP_FROM", "ALERT_PHONE_TO"]
SECRET = {"GEMINI_API_KEY", "SMTP_PASSWORD", "TWILIO_TOKEN", "SLACK_WEBHOOK_URL"}


@app.get("/api/integrations")
def integrations():
    vals = {}
    for k in ENV_KEYS:
        v = os.environ.get(k, "")
        vals[k] = ("set" if v else "") if k in SECRET else v
    return {"values": vals, "configured": notify.configured(), "gemini_model": ai.model()}


@app.post("/api/integrations")
async def save_integrations(request: Request):
    b = await request.json()
    lines = open(ENV_PATH).read().splitlines() if os.path.exists(ENV_PATH) else []
    cur = {l.split("=", 1)[0]: i for i, l in enumerate(lines) if "=" in l and not l.startswith("#")}
    for k, v in b.items():
        if k not in ENV_KEYS or v in (None, "set"):
            continue
        v = str(v).strip()
        os.environ[k] = v
        if k in cur:
            lines[cur[k]] = f"{k}={v}"
        else:
            lines.append(f"{k}={v}")
    try:
        with open(ENV_PATH, "w") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass
    if db.PG:  # hosted: the server's disk is wiped on restart, so keep keys in the database too
        saved = db.get_setting("_env") or {}
        saved.update({k: os.environ[k] for k in ENV_KEYS if os.environ.get(k)})
        db.set_setting("_env", saved)
    return integrations()


@app.post("/api/integrations/test/{name}")
def test_integration(name: str):
    try:
        if name == "gemini":
            return {"ok": True, "message": f"Gemini replied: {ai.test()[:40]}"}
        if name in ("email", "slack", "sms", "whatsapp"):
            r = notify.deliver({name: True}, "EstateHawk test", "This is a test alert from EstateHawk.")
            if not r:
                return {"ok": False, "message": "Not configured"}
            return {"ok": r.get(name) == "sent", "message": r.get(name)}
        if name == "digest":
            s, b = jobs.digest_text()
            return {"ok": True, "message": b, "sent": notify.deliver(db.get_setting("channels"), s, b)}
    except Exception as e:
        return {"ok": False, "message": str(e)[:300]}
    raise HTTPException(404)


@app.post("/api/demo/seed")
def demo_seed():
    demo.seed()
    return {"ok": True}


@app.post("/api/demo/clear")
def demo_clear():
    return {"ok": True, "removed": demo.clear()}


# ------------------------------------------------------------------ plans + super admin
@app.get("/api/plans")
def plan_list():
    return {"plans": {k: plans.PLANS[k] for k in plans.PUBLIC}, "org": INFO()}


def _org_row(o):
    info = plans.org_info(o["id"])
    last = db.q1("SELECT MAX(ts) t FROM audit_log WHERE org_id=?", (o["id"],))["t"]
    admin = db.q1("SELECT name, email FROM users WHERE org_id=? AND role IN ('admin','superadmin') ORDER BY id LIMIT 1", (o["id"],))
    names = [r["name"] for r in db.q("SELECT id, name FROM counties ORDER BY name") if info["counties"] is None or r["id"] in info["counties"]]
    return dict(info, created=o["created"], notes=o.get("notes"), last_activity=last, admin=admin,
                county_names=names if info["counties"] is not None else ["All counties"])


@app.get("/api/admin/orgs")
def admin_orgs():
    return [_org_row(o) for o in db.q("SELECT * FROM orgs ORDER BY id")]


def _set_counties(org, ids, plan):
    limit = plans.PLANS[plan]["counties"]
    ids = [int(i) for i in ids if str(i).isdigit()]
    if limit and len(ids) > limit:
        raise HTTPException(400, f"The {plans.PLANS[plan]['label']} plan allows {limit} county(ies).")
    db.run("DELETE FROM org_counties WHERE org_id=?", (org,))
    for c in ids:
        db.run("INSERT INTO org_counties(org_id, county_id) VALUES(?,?)", (org, c))


@app.post("/api/admin/orgs")
async def admin_org_create(request: Request):
    """New customer company with its first admin login. Trial = 14 days, 1 county."""
    b = await request.json()
    name = (b.get("name") or "").strip()
    email, pw = (b.get("email") or "").strip().lower(), b.get("password") or ""
    plan = b.get("plan") if b.get("plan") in plans.PLANS else "trial"
    if not name or "@" not in email or len(pw) < 8:
        raise HTTPException(400, "Company name, admin email and a temporary password (8+ characters) are needed")
    if db.q1("SELECT 1 FROM users WHERE email=?", (email,)):
        raise HTTPException(400, "This email already has an account")
    limit = plans.PLANS[plan]["counties"]
    if limit and len(b.get("counties") or []) > limit:
        raise HTTPException(400, f"The {plans.PLANS[plan]['label']} plan allows {limit} county(ies).")
    days = int(b.get("trial_days") or plans.PLANS["trial"]["days"])
    ends = (dt.date.today() + dt.timedelta(days=days)).isoformat() if plan == "trial" else None
    oid = db.run("INSERT INTO orgs(name,plan,status,trial_ends,created,notes) VALUES(?,?,?,?,?,?)",
                 (name, plan, "active", ends, jobs.now(), b.get("notes") or ""))
    _set_counties(oid, b.get("counties") or [], plan)
    db.run("INSERT INTO users(email,name,pw,role,created,org_id) VALUES(?,?,?,?,?,?)",
           (email, (b.get("admin_name") or "").strip() or email.split("@")[0], auth.hash_pw(pw), "admin", jobs.now(), oid))
    auth.audit("company created", f"{name} ({plan}) admin {email}")
    return _org_row(db.q1("SELECT * FROM orgs WHERE id=?", (oid,)))


@app.put("/api/admin/orgs/{oid}")
async def admin_org_edit(oid: int, request: Request):
    b = await request.json()
    o = db.q1("SELECT * FROM orgs WHERE id=?", (oid,))
    if not o:
        raise HTTPException(404, "Company not found")
    plan = b.get("plan") if b.get("plan") in plans.PLANS else o["plan"]
    if oid == 1 and (plan != "internal" or b.get("status") == "suspended"):
        raise HTTPException(400, "EstateHawk HQ always stays on the owner plan")
    changes = []
    if b.get("name"):
        db.run("UPDATE orgs SET name=? WHERE id=?", (b["name"].strip(), oid)); changes.append("name")
    if plan != o["plan"]:
        ends = (dt.date.today() + dt.timedelta(days=14)).isoformat() if plan == "trial" else None
        db.run("UPDATE orgs SET plan=?, trial_ends=? WHERE id=?", (plan, ends, oid)); changes.append(f"plan {o['plan']} -> {plan}")
    if b.get("extend_days"):
        base = max(dt.date.today(), dt.date.fromisoformat((o.get("trial_ends") or dt.date.today().isoformat())[:10]))
        db.run("UPDATE orgs SET trial_ends=? WHERE id=?", ((base + dt.timedelta(days=int(b["extend_days"]))).isoformat(), oid))
        changes.append(f"trial +{b['extend_days']} days")
    if b.get("status") in ("active", "suspended"):
        db.run("UPDATE orgs SET status=? WHERE id=?", (b["status"], oid)); changes.append(b["status"])
    if "counties" in b:
        _set_counties(oid, b["counties"], plan); changes.append("counties")
    if "notes" in b:
        db.run("UPDATE orgs SET notes=? WHERE id=?", (b["notes"], oid))
    auth.audit("company updated", f"{o['name']}: {', '.join(changes) or 'notes'}")
    return _org_row(db.q1("SELECT * FROM orgs WHERE id=?", (oid,)))


@app.get("/api/admin/users")
def admin_users():
    return db.q("""SELECT u.id, u.email, u.name, u.role, u.active, u.created, u.last_login, u.org_id, o.name org_name, o.plan
                   FROM users u LEFT JOIN orgs o ON o.id=u.org_id ORDER BY u.org_id, u.id""")


@app.put("/api/admin/users/{uid}")
async def admin_user_edit(uid: int, request: Request):
    b = await request.json()
    u = db.q1("SELECT * FROM users WHERE id=?", (uid,))
    if not u:
        raise HTTPException(404, "User not found")
    if u["role"] == "superadmin" and (b.get("active") is False):
        raise HTTPException(400, "The owner account cannot be blocked")
    if "active" in b:
        db.run("UPDATE users SET active=? WHERE id=?", (1 if b["active"] else 0, uid))
    if b.get("password"):
        db.run("UPDATE users SET pw=? WHERE id=?", (auth.hash_pw(b["password"]), uid))
    if b.get("role") in ("admin", "member") and u["role"] != "superadmin":
        db.run("UPDATE users SET role=? WHERE id=?", (b["role"], uid))
    auth.audit("user updated", f"{u['email']}: {', '.join(k for k in b if k != 'password') or ''}{' password reset' if b.get('password') else ''}")
    return {"ok": True}


@app.get("/api/admin/activity")
def admin_activity(org: str = "", user: str = "", q: str = "", limit: int = 300):
    w, a = " WHERE 1=1", []
    if org.isdigit():
        w += " AND l.org_id=?"; a.append(int(org))
    if user.isdigit():
        w += " AND l.user_id=?"; a.append(int(user))
    if q:
        w += " AND (l.action LIKE ? OR l.detail LIKE ? OR l.user_name LIKE ?)"; a += [f"%{q}%"] * 3
    return db.q(f"""SELECT l.*, o.name org_name FROM audit_log l LEFT JOIN orgs o ON o.id=l.org_id{w}
                    ORDER BY l.id DESC LIMIT ?""", a + [min(limit, 1000)])


@app.get("/api/admin/stats")
def admin_stats():
    orgs = db.q("SELECT plan, status, trial_ends FROM orgs WHERE id<>1")
    today = dt.date.today().isoformat()
    week = (dt.datetime.now() - dt.timedelta(days=7)).isoformat(sep=" ")
    return {"companies": len(orgs),
            "trials": sum(1 for o in orgs if o["plan"] == "trial" and (o["trial_ends"] or "") >= today),
            "paying": sum(1 for o in orgs if o["plan"] in ("starter", "pro", "agency") and o["status"] == "active"),
            "mrr": sum(plans.PLANS[o["plan"]]["price"] for o in orgs if o["plan"] in ("starter", "pro", "agency") and o["status"] == "active"),
            "users": db.q1("SELECT COUNT(*) n FROM users")["n"],
            "active_week": db.q1("SELECT COUNT(DISTINCT user_id) n FROM audit_log WHERE ts>=?", (week,))["n"]}


# ------------------------------------------------------------------ static web app
app.mount("/static", StaticFiles(directory=WEB), name="static")


app.mount("/site", StaticFiles(directory=os.path.join(WEB, "site")), name="site")


@app.get("/sitemap.xml")
def sitemap_xml(request: Request):
    return Response(site.sitemap(request), media_type="application/xml")


@app.get("/robots.txt")
def robots_txt(request: Request):
    return Response(site.robots(request), media_type="text/plain")


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse({"name": "EstateHawk", "short_name": "EstateHawk", "start_url": "/app", "display": "standalone",
                         "background_color": "#F7F6F2", "theme_color": "#14532D",
                         "icons": [{"src": "/static/icon.svg", "sizes": "any", "type": "image/svg+xml"}]})


@app.get("/{path:path}", response_class=HTMLResponse)
def spa(path: str, request: Request):
    if path == "app" or path.startswith("app/"):  # the product (single-page app)
        return FileResponse(os.path.join(WEB, "index.html"), headers={"Cache-Control": "no-cache"})
    html_ = site.render(request, path)  # the marketing website
    if html_ is None:
        return HTMLResponse(site.not_found(request), status_code=404)
    return HTMLResponse(html_, headers={"Cache-Control": "public, max-age=300"})
