import csv, datetime as dt, io, json, os, re

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import db, scoring, ai, notify, jobs, demo, geocode, contacts, auth, ctx, plans, site, billing, mailer, google_auth, quality, research
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
        resp.headers["Access-Control-Allow-Origin"] = "*"  # public brand assets, usable from social profiles
    # browser security headers: no framing by other sites, no MIME sniffing, no plugins, HTTPS only
    h = resp.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "SAMEORIGIN")
    h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    h.setdefault("Content-Security-Policy", "frame-ancestors 'self'; object-src 'none'; base-uri 'self'")
    if request.headers.get("x-forwarded-proto", request.url.scheme) == "https":
        h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return resp


@app.exception_handler(ValueError)
async def bad_value(request, exc):
    """A filter or form value that is not a number: a clear 400 instead of a server error."""
    return JSONResponse({"detail": "One of the values is not valid. Check numbers and try again."}, status_code=400)


@app.middleware("http")
async def canonical_host(request, call_next):
    """Pages on the old onrender address move to the real domain, so Google sees one site. The API stays on both."""
    host = (request.url.hostname or "").lower()
    if host.endswith(".onrender.com") and request.method in ("GET", "HEAD") and not request.url.path.startswith("/api/"):
        from fastapi.responses import RedirectResponse
        q = ("?" + request.url.query) if request.url.query else ""
        return RedirectResponse(site.CANONICAL + request.url.path + q, status_code=301)
    return await call_next(request)


@app.get("/healthz")
@app.head("/healthz")
def healthz():
    """Keep-awake ping target. Touches no database, so Neon can still sleep while Render stays up."""
    return {"ok": True}


# ------------------------------------------------------------------ login + team
def _client_ip(request):
    return auth.client_ip(request)


@app.get("/api/auth/me")
def auth_me(request: Request):
    u = auth.current(request)
    if not u:
        return JSONResponse({"user": None, "setup": not auth.users_exist(), "google": google_auth.configured()}, status_code=401)
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
    b = await request.json()
    acct = (b.get("email") or "").strip().lower()
    auth.throttle(ip, acct)
    u = db.q1("SELECT * FROM users WHERE email=?", (acct,))
    if not u or not u["active"] or not auth.check_pw(b.get("password") or "", u["pw"]):
        auth.failed(ip, acct)
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
    if email.split("@")[-1] in DISPOSABLE:
        raise HTTPException(400, "Please use your real work or personal email, not a temporary inbox.")
    try:
        cid = int(b.get("county_id") or 0)
    except ValueError:
        cid = 0
    if not _county_ok(cid):
        raise HTTPException(400, "Choose your first county.")
    uid = _new_trial(request, name, email, auth.hash_pw(pw), b.get("company"), cid, ip, "website")
    resp = JSONResponse({"ok": True})
    auth.set_cookie(resp, request, uid)
    return resp


DISPOSABLE = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "guerrillamail.net", "sharklasers.com", "yopmail.com",
              "tempmail.com", "temp-mail.org", "trashmail.com", "getnada.com", "dispostable.com", "maildrop.cc", "throwawaymail.com",
              "mintemail.com", "fakeinbox.com", "mohmal.com", "emailondeck.com", "tempmailo.com", "moakt.com", "mailnesia.com"}


def _verify_link(request, uid):
    return f"{site.base_url(request)}/verify-email?token={auth.make_reset(uid, 'verify')}"


def _county_ok(cid):
    """Open for new trials: enabled, real, and most leads come with an address or a map point."""
    if not cid or not db.q1("SELECT 1 FROM counties WHERE id=? AND enabled=1 AND demo=0", (cid,)):
        return False
    r = db.q1("""SELECT COUNT(*) n, SUM(CASE WHEN lat IS NOT NULL OR COALESCE(street,'') <> '' THEN 1 ELSE 0 END) good
                 FROM parcels WHERE county_id=? AND is_active=1""", (cid,))
    return bool(r and r["n"] and (r["good"] or 0) >= 0.6 * r["n"])


def _new_trial(request, name, email, pw_hash, company, cid, ip, how):
    """A new company on the 14-day trial with one county, its admin login, and the welcome email. Returns the user id."""
    ends = (dt.date.today() + dt.timedelta(days=plans.PLANS["trial"]["days"])).isoformat()
    company = (company or "").strip()[:80] or f"{name}'s team"
    oid = db.run("INSERT INTO orgs(name,plan,status,trial_ends,created,notes) VALUES(?,?,?,?,?,?)",
                 (company, "trial", "active", ends, jobs.now(), "Signed up on the website" + (" with Google" if how == "google" else "")))
    db.run("INSERT INTO org_counties(org_id, county_id) VALUES(?,?)", (oid, cid))
    uid = db.run("INSERT INTO users(email,name,pw,role,created,org_id,email_verified) VALUES(?,?,?,?,?,?,?)",
                 (email, name, pw_hash, "admin", jobs.now(), oid, 1 if how == "google" else 0))
    u = db.q1("SELECT * FROM users WHERE email=?", (email,))
    auth.audit("signed up", f"{company} ({email}) trial" + (" via Google" if how == "google" else ""), user=u, org=oid, ip=ip)
    cname = (db.q1("SELECT name FROM counties WHERE id=?", (cid,)) or {}).get("name", "your county")
    site_url = site.base_url(request)
    rid = u["id"] if u else uid
    confirm = how != "google"
    mailer.send(email, "Welcome to EstateHawk: confirm your email" if confirm else "Welcome to EstateHawk: your 14-day trial is on", f"Welcome, {name.split(' ')[0]}",
                [f"Your free trial is ready. You have 14 days and {plans.PLANS['trial']['reveals']} full leads to open in <b>{mailer.esc(cname)}</b>.",
                 ("Confirm your email with the button below, then open your first leads. The link works for 7 days." if confirm else
                  "Start with the highest deal scores: they owe the most for the longest and have the most equity."),
                 "If you need anything, just reply to this email."],
                ("Confirm my email", _verify_link(request, rid)) if confirm else ("Open my leads", f"{site_url}/app"))
    return u["id"] if u else uid


# ------------------------------------------------------------------ sign in with Google
def _back(path, msg=None):
    from fastapi.responses import RedirectResponse
    from urllib.parse import quote
    r = RedirectResponse(path + (("&" if "?" in path else "?") + "error=" + quote(msg) if msg else ""), status_code=303)
    r.delete_cookie(google_auth.COOKIE, path="/api/auth/google")
    return r


@app.get("/api/auth/google/start")
def google_start(request: Request, county_id: str = "", company: str = "", mode: str = "login"):
    from fastapi.responses import RedirectResponse
    if not google_auth.configured():
        return _back("/login", "Google sign-in is not turned on yet. Use your email and password.")
    auth.throttle(_client_ip(request))
    cid = int(county_id) if county_id.isdigit() and _county_ok(int(county_id)) else None
    url, cookie = google_auth.start(site.base_url(request), cid, company)
    r = RedirectResponse(url, status_code=303)
    https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    r.set_cookie(google_auth.COOKIE, cookie, max_age=600, httponly=True, samesite="lax", secure=https, path="/api/auth/google")
    return r


@app.get("/api/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    ip = _client_ip(request)
    if error or not code:
        return _back("/login", "Google sign-in was cancelled.")
    auth.throttle(ip)
    try:
        p = google_auth.finish(site.base_url(request), code, state, request.cookies.get(google_auth.COOKIE))
    except ValueError as e:
        auth.failed(ip)
        return _back("/login", str(e))
    except Exception:  # noqa: BLE001  Google unreachable
        return _back("/login", "Could not reach Google. Please try again.")
    u = db.q1("SELECT * FROM users WHERE email=?", (p["email"],))
    if u:
        if not u["active"]:
            return _back("/login", "This login is turned off. Ask your company admin.")
        o = db.q1("SELECT status FROM orgs WHERE id=?", (u.get("org_id") or 1,))
        if o and o["status"] == "suspended" and u["role"] != "superadmin":
            return _back("/login", "Your company account is paused. Contact EstateHawk.")
        db.run("UPDATE users SET last_login=? WHERE id=?", (jobs.now(), u["id"]))
        auth.audit("login", "with Google", user=u, org=u.get("org_id"), ip=ip)
        uid = u["id"]
    else:
        if not p["county"] or not _county_ok(p["county"]):
            return _back("/signup?google=1", "No account with that Google email yet. Choose your first county, then continue with Google.")
        uid = _new_trial(request, p["name"], p["email"], "", p["company"], p["county"], ip, "google")
    r = _back("/app")
    auth.set_cookie(r, request, uid)
    return r


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
    nm = (b.get('name') or '').strip()[:80]
    auth.audit("website message", f"{nm} <{email}>: {msg}", org=1, ip=ip)
    auth.failed(ip)  # counts toward the hourly limit, stops floods
    mailer.send(os.environ.get("SUPPORT_EMAIL") or "support@getestatehawk.com", f"Website message from {nm or email}", "New website message",
                [f"<b>From:</b> {mailer.esc(nm)} &lt;{mailer.esc(email)}&gt;", mailer.esc(msg).replace("\n", "<br>")], reply_to=email,
                foot="Sent from the contact form on getestatehawk.com.")
    mailer.send(email, "We got your message", "Thanks for writing to EstateHawk",
                ["We got your message and will reply within one business day.", f"<i>{mailer.esc(msg[:600])}</i>"],
                foot="You get this email because you used the contact form on getestatehawk.com.")
    return {"ok": True}


@app.post("/api/auth/logout")
def auth_logout(request: Request):
    u = auth.current(request)
    if u:
        auth.end_sessions(u["id"])  # the cookie is now useless everywhere, even if someone copied it
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
    if row["pw"] and not auth.check_pw(b.get("old") or "", row["pw"]):  # Google-only logins have no password yet
        raise HTTPException(400, "Current password is wrong")
    if len(b.get("new") or "") < 8:
        raise HTTPException(400, "New password needs at least 8 characters")
    db.run("UPDATE users SET pw=? WHERE id=?", (auth.hash_pw(b["new"]), u["id"]))
    auth.end_sessions(u["id"])  # other devices are logged out; this one gets a fresh session
    resp = JSONResponse({"ok": True})
    auth.set_cookie(resp, request, u["id"])
    return resp


@app.get("/verify-email")
def verify_email(request: Request, token: str = ""):
    from fastapi.responses import RedirectResponse
    uid = auth.read_reset(token, purposes=("verify",))
    if not uid:
        return RedirectResponse("/login?error=" + "This confirmation link is old or already used. Sign in and resend it from the banner.", status_code=303)
    db.run("UPDATE users SET email_verified=1 WHERE id=?", (uid,))
    u = db.q1("SELECT * FROM users WHERE id=?", (uid,))
    auth.audit("email confirmed", u.get("email") if u else "", user=u, org=(u or {}).get("org_id"), ip=_client_ip(request))
    r = RedirectResponse("/app#/deals", status_code=303)
    auth.set_cookie(r, request, uid)
    return r


@app.post("/api/auth/resend-verify")
def resend_verify(request: Request):
    u = auth.current(request)
    if not u:
        raise HTTPException(401, "Please log in")
    if u.get("email_verified") != 0:
        return {"ok": True, "already": True}
    ip = _client_ip(request)
    auth.throttle(ip, u["email"])
    auth.failed(ip, u["email"])  # counts toward the limit, so the button cannot flood an inbox
    mailer.send(u["email"], "Confirm your EstateHawk email", "Confirm your email",
                ["Click the button to confirm this is your email. Then you can open your free leads.", "The link works for 7 days."],
                ("Confirm my email", _verify_link(request, u["id"])))
    return {"ok": True}


@app.post("/api/auth/forgot")
async def auth_forgot(request: Request):
    """Email a one-time reset link. Same answer whether or not the email exists."""
    ip = _client_ip(request)
    auth.throttle(ip)
    auth.failed(ip)  # every request counts, stops floods
    b = await request.json()
    email = (b.get("email") or "").strip().lower()[:120]
    u = db.q1("SELECT id, name, active FROM users WHERE email=?", (email,))
    if u and u["active"]:
        link = f"{site.base_url(request)}/reset-password?token={auth.make_reset(u['id'])}"
        mailer.send(email, "Reset your EstateHawk password", "Reset your password",
                    ["Someone (hopefully you) asked to reset the password for this EstateHawk account.",
                     f"The link works once and expires in {auth.RESET_MINUTES} minutes. If you did not ask, ignore this email."],
                    ("Choose a new password", link))
        auth.audit("password reset requested", email, user=u, org=None, ip=ip)
    return {"ok": True}


@app.post("/api/auth/reset")
async def auth_reset(request: Request):
    ip = _client_ip(request)
    auth.throttle(ip)
    b = await request.json()
    uid = auth.read_reset(b.get("token") or "")
    if not uid:
        auth.failed(ip)
        raise HTTPException(400, "This link has expired or was already used. Ask for a new one.")
    if len(b.get("password") or "") < 8:
        raise HTTPException(400, "Choose a password of at least 8 characters.")
    db.run("UPDATE users SET pw=? WHERE id=?", (auth.hash_pw(b["password"]), uid))
    auth.end_sessions(uid)
    auth.audit("password reset", "", user={"id": uid}, org=None, ip=ip)
    resp = JSONResponse({"ok": True})
    auth.set_cookie(resp, request, uid)
    return resp


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
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Enter a valid email")
    if pw and len(pw) < 8:
        raise HTTPException(400, "A temporary password needs at least 8 characters (or leave it empty to send an invite link)")
    if db.q1("SELECT 1 FROM users WHERE email=?", (email,)):
        raise HTTPException(400, "This email already has an account")
    info = ctx.get()["org"]
    limit = info["limits"]["users"]
    if limit and info["users"] >= limit and not ctx.get().get("super"):
        raise HTTPException(402, f"Your {info['label']} plan allows {limit} user(s). Upgrade to add more.")
    import secrets as _s
    uid = db.run("INSERT INTO users(email,name,pw,role,created,org_id) VALUES(?,?,?,?,?,?)",
                 (email, (b.get("name") or "").strip() or email.split("@")[0], auth.hash_pw(pw or _s.token_urlsafe(24)),
                  b.get("role") if b.get("role") in ("admin", "member") else "member", jobs.now(), _team_org()))
    me = ctx.get().get("user") or {}
    link = f"{site.base_url(request)}/reset-password?invite=1&token={auth.make_reset(uid, 'invite')}"
    sent = mailer.send(email, f"{me.get('name') or 'Your team'} invited you to EstateHawk", "You are invited to EstateHawk",
                       [f"{mailer.esc(me.get('name') or 'A teammate')} added you to <b>{mailer.esc(info['name'])}</b> on EstateHawk, where your team finds and works tax-delinquent property leads.",
                        "Choose your password to get started. The link works for 7 days."], ("Set my password", link))
    return {"ok": True, "invite_sent": sent}


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
        auth.end_sessions(uid)
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
    if params.get("owner_status") == "available":
        w += " AND TRIM(COALESCE(p.owner_name,'')) != ''"
    elif params.get("owner_status") == "missing":
        w += " AND TRIM(COALESCE(p.owner_name,'')) = ''"
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
            "plans": {k: plans.PLANS[k] for k in plans.PUBLIC},
            "team": db.q("SELECT id, name, email FROM users WHERE org_id=? AND active=1 ORDER BY name", (OID(),))}


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
    homes = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.is_active=1 AND (p.property_type IN ('Single family','Residential') OR p.property_type IS NULL OR p.property_type IN ('Unknown','Other')){s}", a)["n"]
    pct = lambda n, o: (round((n - o) * 100 / o) if o else None)
    return {"new_today": new_today, "new_change": pct(new_today, new_y), "high_score": hi, "high_change": pct(hi, hi_wk),
            "avg_equity": round(eq or 0), "counties": ct["n"], "states": ct["st"], "active": active, "homes": homes}


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
    allow = plans.export_allowance(INFO())
    name = f"estatehawk-leads-{dt.date.today()}"
    if allow is not None:
        left, lim = allow
        if left <= 0:
            return HTMLResponse(f"<p style='font:16px sans-serif;padding:40px'>Your plan's daily export limit ({lim} leads) is used up for today. "
                                "It resets tomorrow. Every lead stays open in the app.</p><p style='font:16px sans-serif;padding:0 40px'><a href='/app'>Back to EstateHawk</a></p>", status_code=429)
        if len(rows) > left:
            name += f"-top-{left}-of-{len(rows)}"
            rows = rows[:left]
        plans.export_used(INFO(), len(rows))
    auth.audit("export", f"{len(rows)} leads")
    buf = io.StringIO()
    if rows:
        wr = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        wr.writeheader(); wr.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={name}.csv"})


def get_parcel(pid, unlocked=False):
    cf, _ = county_filter(None)
    p = db.q1(f"""SELECT p.*, c.name county_name, c.host county_host, c.tax_sale_date, pl.stage, pl.fee, pl.assigned_to
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
    county = db.q1("SELECT host, last_sync, sync_status FROM counties WHERE id=?", (p["county_id"],)) or {}
    check = quality.lead(p, county)
    if plans.is_locked(info, pid):
        check["record_url"] = None  # the county record link shows the address
        br = json.loads(p.get("score_breakdown") or "{}")
        p["score_parts"] = br.get("parts", {})
        p["reasons"] = scoring.reasons(p, br)
        p = plans.mask(p)
        p.update(snapshots=[], activities=[], offers=[], tasks=[], contacts=[], offer_defaults=db.get_setting("offer_defaults"),
                 ai=False, reveals_left=info["reveals_left"], reveals_total=info["limits"]["reveals"])
        p["reasons"] = [(t, x) for t, x in p["reasons"] if "Tax bills go to" not in x] + ([("Out-of-state owner", "Owner lives in another state.")] if p.get("mail_state") and p.get("mail_state") != p.get("state") else [])
        p["data_check"] = check
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
    p["data_check"] = check
    return p


def _num_or_none(v, lo=0, hi=1e9):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or x < lo or x > hi:
        raise ValueError("Numbers must be between 0 and 1,000,000,000")
    return x


@app.get("/api/parcels/{pid:path}/research")
def parcel_research(pid: str):
    """Flood zone, state tax-sale rules, cached comps and the deal calculator for one lead."""
    p = get_parcel(pid)
    locked = plans.is_locked(INFO(), pid)
    fl = research.flood_for(p)
    out = {"flood": fl, "rules": research.rules_for(p), "comps_available": bool(research.rentcast_key()),
           "calc_defaults": db.get_setting("calc_defaults"), "locked": locked}
    if locked:
        return out  # the rest needs the address
    c = db.q1("SELECT data FROM research_cache WHERE parcel_id=? AND kind='comps'", (pid,))
    out["comps"] = json.loads(c["data"]) if c else None
    out["calc"] = research.calc(p, db.get_setting("calc_defaults"))
    return out


COMPARE_BY = {
    "margin": ("Room under your maximum offer", "max_bid"),
    "equity": ("Estimated equity", "est_equity"),
    "score": ("Deal score", "score"),
    "cheap": ("Lowest taxes to clear", "taxes"),
}


@app.get("/api/auctions")
def auctions(days: int = 120):
    """Upcoming tax sales: a date per county (county sale dates) and per property (Texas sale lists)."""
    today = dt.date.today().isoformat()
    end = (dt.date.today() + dt.timedelta(days=max(1, min(days, 365)))).isoformat()
    cf, a = county_filter("all")
    per = db.q(f"""SELECT p.sale_date d, p.county_id, c.name county, c.state, COUNT(*) n, SUM(COALESCE(p.min_bid, p.amount_owed, 0)) bids,
                   MIN(COALESCE(p.min_bid, p.amount_owed)) low, MAX(p.appraised_total) top_value,
                   SUM(CASE WHEN p.score >= 80 THEN 1 ELSE 0 END) strong
                   FROM parcels p JOIN counties c ON c.id=p.county_id
                   WHERE p.is_active=1 AND p.sale_date>=? AND p.sale_date<=?{cf} GROUP BY p.sale_date, p.county_id, c.name, c.state""", [today, end] + a)
    seen = {(r["d"], r["county_id"]) for r in per}
    cc, _ = county_filter(None, "x")
    for c in db.q(f"SELECT id, name, state, tax_sale_date FROM counties x WHERE enabled=1 AND tax_sale_date>=? AND tax_sale_date<=?{cc.replace('x.county_id', 'x.id')}", (today, end)):
        if (c["tax_sale_date"], c["id"]) in seen:
            continue
        n = db.q1("SELECT COUNT(*) n FROM parcels WHERE county_id=? AND is_active=1", (c["id"],))["n"]
        per.append({"d": c["tax_sale_date"], "county_id": c["id"], "county": c["name"], "state": c["state"], "n": None, "listed": n,
                    "bids": None, "low": None, "top_value": None, "strong": None, "kind": "county"})
    for r in per:
        r.setdefault("kind", "list")
        r["days"] = (dt.date.fromisoformat(r["d"][:10]) - dt.date.today()).days
    per.sort(key=lambda r: (r["d"], r["county"]))
    return {"rows": per, "today": today, "until": end,
            "note": "Sale dates come from county and tax-attorney sale lists and can change or be cancelled. Confirm with the county before the sale."}


@app.get("/api/parcels-by-sale")
def parcels_by_sale(county_id: int, date: str):
    cf, a = county_filter("all")
    rows = db.q(f"""SELECT p.id, p.street, p.city, p.zip, p.state, p.min_bid, p.amount_owed, p.appraised_total, p.score, p.sale_status, p.lat, p.lng
                    FROM parcels p WHERE p.is_active=1 AND p.county_id=? AND p.sale_date=?{cf} ORDER BY p.score DESC LIMIT 200""", [county_id, date] + a)
    info = INFO()
    if info["limits"]["reveals"]:
        seen = plans.revealed_set(info, [r["id"] for r in rows]) or set()
        for r in rows:
            if r["id"] not in seen:
                r["street"] = "Address hidden"
    return rows


@app.post("/api/compare")
async def compare(request: Request):
    """2 to 4 leads side by side, ranked by the measure the user picks, with the reason for each rank."""
    b = await request.json()
    ids = [i for i in (b.get("ids") or []) if isinstance(i, str)][:4]
    by = b.get("by") if b.get("by") in COMPARE_BY else "margin"
    if len(ids) < 2:
        raise HTTPException(400, "Pick 2 to 4 leads to compare")
    info, d = INFO(), db.get_setting("calc_defaults")
    rows = []
    for pid in ids:
        p = get_parcel(pid)
        locked = plans.is_locked(info, pid)
        county = db.q1("SELECT host, last_sync, sync_status FROM counties WHERE id=?", (p["county_id"],)) or {}
        dc = quality.lead(p, county)
        k = research.calc(p, d)
        fz = p.get("flood_zone")
        row = {"id": pid, "locked": locked, "title": "Address hidden" if locked else (p.get("street") or f"Parcel {p.get('parcel_number')}"),
               "place": ", ".join(x for x in (p.get("city"), p.get("state")) if x), "county": p.get("county_name"),
               "value": p.get("appraised_total"), "taxes": p.get("total_due") or p.get("amount_owed") or 0, "est_equity": p.get("est_equity"),
               "years_behind": p.get("years_behind"), "score": p.get("score"), "max_bid": k["max_bid"], "repairs": k["repairs"],
               "roi_pct": k["roi_pct"], "property_type": p.get("property_type"), "status": dc["status"],
               "missing": len(dc["missing"]), "complete": round(100 * (6 - len(dc["missing"])) / 6),
               "flood": (f"Zone {fz}" + (" (high risk)" if p.get("flood_sfha") else "")) if fz else "Not checked",
               "out_of_state": bool(p.get("mail_state") and p.get("mail_state") != p.get("state"))}
        rows.append(row)
    label, key = COMPARE_BY[by]
    rev = by != "cheap"
    rows.sort(key=lambda r: ((r.get(key) or 0) * (1 if rev else -1), r["complete"]), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        bits = [f"{label.lower()}: " + (f"${r[key]:,.0f}" if key in ("max_bid", "est_equity", "taxes") and r.get(key) is not None else f"{r.get(key) or 0:g}")]
        if r["missing"]:
            bits.append(f"{r['missing']} county fields missing")
        if r["status"] in ("stale", "removed", "conflict"):
            bits.append({"stale": "not on the latest list", "removed": "off the county list", "conflict": "amounts differ"}[r["status"]])
        if "high risk" in r["flood"]:
            bits.append("high flood risk")
        r["why"] = "; ".join(bits)
    return {"by": by, "label": label, "rows": rows, "options": {k2: v[0] for k2, v in COMPARE_BY.items()},
            "note": "Ranked by one measure you choose, using county records and your calculator settings. Estimates, not predictions."}


@app.post("/api/parcels/{pid:path}/comps")
def parcel_comps(pid: str):
    p = get_parcel(pid, unlocked=True)
    if not research.rentcast_key():
        raise HTTPException(400, "Comps are not switched on yet (needs a RentCast key in Render).")
    key = f"comps:{dt.date.today().isoformat()}"
    used = db.q1("SELECT value FROM org_settings WHERE org_id=? AND key=?", (OID(), key))
    n = int((used or {}).get("value") or 0)
    if n >= 25 and OID() != 1:
        raise HTTPException(429, "25 comp lookups a day are used up. Cached results still show.")
    data = research.comps(p)  # a fresh cached result (under 30 days) costs nothing
    db.run("""INSERT INTO org_settings(org_id,key,value) VALUES(?,?,?)
              ON CONFLICT(org_id,key) DO UPDATE SET value=excluded.value""", (OID(), key, str(n + 1)))
    return data or {"error": "No result"}


@app.post("/api/parcels/{pid:path}/calc")
async def parcel_calc(pid: str, request: Request):
    p = get_parcel(pid, unlocked=True)
    b = await request.json()
    d = {**db.get_setting("calc_defaults"), **{k: v for k, v in (b.get("settings") or {}).items() if k in db.DEFAULT_SETTINGS["calc_defaults"]}}
    if d.get("risk") not in research.RISK:
        d["risk"] = "medium"
    for k in ("profit_pct", "repair_per_sqft", "buy_closing_pct", "sell_closing_pct", "hold_months", "monthly_hold"):
        d[k] = _num_or_none(d.get(k), 0, 1e6) or 0
    if b.get("save"):
        db.set_setting("calc_defaults", d)
    return research.calc(p, d, arv=_num_or_none(b.get("arv")), repairs=_num_or_none(b.get("repairs")), liens=_num_or_none(b.get("liens")) or 0)


@app.post("/api/parcels/{pid:path}/reveal")
def reveal(pid: str):
    get_parcel(pid)
    info = INFO()
    if not plans.is_locked(info, pid):
        return {"ok": True, "reveals_left": info["reveals_left"]}
    if info["reveals_left"] is not None and info["reveals_left"] <= 0:
        raise HTTPException(402, f"You have opened all {info['limits']['reveals']} free leads. Upgrade to see every lead.")
    me = ctx.get().get("user") or {}
    if me.get("email_verified") == 0:
        raise HTTPException(403, "Confirm your email first: open the link we sent you, or resend it from the banner at the top.")
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
    if terms["price"] <= 0 or terms["earnest"] < 0 or terms["closing_days"] <= 0:
        raise HTTPException(400, "Offer price and closing days must be more than zero")
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


@app.post("/api/parcels/{pid:path}/assign")
async def assign(pid: str, request: Request):
    """Give a pipeline lead to a team member (or nobody)."""
    get_parcel(pid, unlocked=True)
    b = await request.json()
    uid = b.get("user_id")
    if uid is not None:
        u = db.q1("SELECT id, name, email FROM users WHERE id=? AND org_id=? AND active=1", (int(uid), OID()))
        if not u:
            raise HTTPException(400, "Pick someone on your team")
    if not db.q1("SELECT 1 FROM pipeline WHERE parcel_id=? AND org_id=?", (pid, OID())):
        db.run("INSERT INTO pipeline(org_id,parcel_id,stage,updated_at) VALUES(?,?,?,?)", (OID(), pid, "new", jobs.now()))
    db.run("UPDATE pipeline SET assigned_to=?, updated_at=? WHERE parcel_id=? AND org_id=?", (uid, jobs.now(), pid, OID()))
    db.run("INSERT INTO activities(parcel_id,ts,kind,text,author,org_id) VALUES(?,?,?,?,?,?)",
           (pid, jobs.now(), "note", f"Assigned to {u['name'] or u['email']}" if uid is not None else "Unassigned", me_name(), OID()))
    return {"ok": True}


@app.post("/api/parcels/{pid:path}/activity")
async def add_activity(pid: str, request: Request):
    get_parcel(pid, unlocked=True)
    b = await request.json()
    kind = b.get("kind", "note")
    if len(b.get("text") or "") > 10000:
        raise HTTPException(400, "Notes can be up to 10,000 characters")
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
    qual = quality.counties([c["id"] for c in rows]) if rows else {}
    for c in rows:
        c["quality"] = qual.get(c["id"])
        c["grade"] = quality.grade(c["quality"])
        c["list_url"] = quality.list_url(c.get("host"))
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
def pipeline(county: str = "all", q: str = "", who: str = "all"):
    s, a = county_filter(county)
    if q:
        s += " AND (p.street LIKE ? OR p.owner_name LIKE ?)"; a += [f"%{q}%"] * 2
    if who == "me":
        s += " AND pl.assigned_to=?"; a.append((ctx.get().get("user") or {}).get("id"))
    elif who == "none":
        s += " AND pl.assigned_to IS NULL"
    elif who.isdigit():
        s += " AND pl.assigned_to=?"; a.append(int(who))
    o = OID()
    rows = db.q(f"""SELECT pl.*, p.street, p.city, p.zip, p.owner_name, p.score, p.lat, p.lng, p.county_id, p.total_due, p.amount_owed,
                    (SELECT u.name FROM users u WHERE u.id=pl.assigned_to) assignee,
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
    if not (b.get("text") or "").strip():
        raise HTTPException(400, "Write what the task is")
    b["text"] = b["text"].strip()[:500]
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


@app.get("/report/{pid:path}", response_class=HTMLResponse)
def lead_report(pid: str):
    """Printable due-diligence report for one lead: verified facts, estimates, sources, gaps and warnings."""
    import html as H
    p = get_parcel(pid)
    if plans.is_locked(INFO(), pid):
        raise HTTPException(403, "Open this lead first (free trial), then download its report.")
    e = lambda x: H.escape(str(x)) if x not in (None, "") else "--"
    m = lambda x, c=0: f"${x:,.{c}f}" if isinstance(x, (int, float)) else "--"
    county = db.q1("SELECT host, last_sync, sync_status FROM counties WHERE id=?", (p["county_id"],)) or {}
    dc = quality.lead(p, county)
    fl = research.flood_for(p)
    rules = research.rules_for(p)
    cache = db.q1("SELECT data FROM research_cache WHERE parcel_id=? AND kind='comps'", (pid,))
    cp = json.loads(cache["data"]) if cache else None
    k = research.calc(p, db.get_setting("calc_defaults"))
    snaps = db.q("SELECT date, amount, owner_name FROM snapshots WHERE parcel_id=? ORDER BY date", (pid,))
    br = json.loads(p.get("score_breakdown") or "{}")
    why = scoring.reasons(p, br)
    rec = lambda label, val, src: f"<tr><td>{label}</td><td>{val}</td><td class=src>{src}</td></tr>"
    county_src = f"{e(dc['source'])}" + (f' (<a href="{e(dc["list_url"])}">list</a>)' if dc.get("list_url") else "")
    record_src = f'<a href="{e(p["property_url"])}">county property record</a>' if p.get("property_url") else county_src
    facts = "".join([
        rec("Address", e(", ".join(x for x in (p.get("street"), p.get("city"), f"{p.get('state') or ''} {p.get('zip') or ''}".strip()) if x)), county_src),
        rec("Parcel number", e(p.get("parcel_number")), county_src),
        rec("Owner on record", e(p.get("owner_full_name") or p.get("owner_name")), record_src),
        rec("Tax bill mailed to", e(p.get("mail_address")), record_src),
        rec("Taxes owed (county list)", m(p.get("amount_owed"), 2), county_src),
        rec("Total due (county record)", m(p.get("total_due"), 2), record_src),
        rec("Yearly tax", m(p.get("annual_tax"), 2), record_src),
        rec("County value", m(p.get("appraised_total")), record_src + ", for tax purposes"),
        rec("Land / building value", f"{m(p.get('land_value'))} / {m(p.get('improvement_value'))}", record_src),
        rec("Land use", e(p.get("land_use") or p.get("property_type")), record_src),
        rec("Acres", e(p.get("acres")), record_src),
        rec("Beds / baths / sq ft / built", f"{e(p.get('beds'))} / {e(p.get('baths_full'))} / {e(p.get('living_area'))} / {e(p.get('year_built'))}", record_src),
        rec("Flood zone", e(fl.get("words")), e(fl.get("source") or "FEMA National Flood Hazard Layer") + (f", checked {e(fl.get('checked'))}" if fl.get("checked") else "")),
        rec("First / last seen on the county list", f"{e(dc['first_seen'])} / {e(dc['last_seen'])}", "EstateHawk nightly download"),
    ])
    ests = "".join([
        rec("Years behind", e(p.get("years_behind")), "Estimated from the amount owed and the yearly tax" if not p.get("cert_year") else f"Certified delinquent {p['cert_year']}"),
        rec("Equity", m(p.get("est_equity")), "County value minus taxes owed; mortgages unknown"),
        rec("Rent", m(p.get("rent_est")) + " / month" if p.get("rent_est") else "--", "Rule of thumb, about 0.9% of value a month"),
        rec("Market value", f"{m(cp.get('value'))} ({m(cp.get('low'))} to {m(cp.get('high'))})" if cp and cp.get("value") else "--", f"{e(cp.get('source'))}, {e(cp.get('fetched'))}" if cp and cp.get("value") else "Not looked up"),
        rec("Deal score", e(round(p["score"]) if p.get("score") is not None else None), "Ranks public-record signals; not a prediction that the owner will sell"),
    ])
    hist = "".join(f"<tr><td>{e(s_['date'])}</td><td>{m(s_['amount'], 2)}</td><td>{e(s_['owner_name'])}</td></tr>" for s_ in snaps[-12:]) or "<tr><td colspan=3>No history yet</td></tr>"
    comps_html = ("".join(f"<tr><td>{e(c['address'])}</td><td>{m(c['price'])}</td><td>{e(c['sqft'])}</td><td>{e(c['miles'])}</td><td>{e(c['date'])}</td></tr>" for c in cp["comps"])
                  if cp and cp.get("comps") else "<tr><td colspan=5>No comparable sales looked up yet.</td></tr>")
    calc_rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td class=src>{c}</td></tr>" for a, b, c in [
        ("After-repair value", m(k["arv"]), e(k["sources"].get("arv"))), ("Repairs", m(k["repairs"]), e(k["sources"].get("repairs"))),
        ("Back taxes", m(k["taxes"], 2), "County"), ("Closing, buy + sell", m(k["buy_closing"] + k["sell_closing"]), "Your settings"),
        ("Holding", m(k["holding"]), f"{k['hold_months']:g} months"), ("Profit target", m(k["profit"]), f"{k['profit_pct']:g}% of value"),
        ("<b>Maximum offer</b>", f"<b>{m(k['max_bid'])}</b>", "Value minus all of the above"), ("70% rule", m(k["rule70"]), "For comparison")])
    gaps = [f"Not published by the county: {', '.join(dc['missing'])}." for _ in [0] if dc["missing"]]
    gaps += ["Mortgages, liens and judgments are not in county tax records. Order a title search."]
    if dc["amount_differs"]:
        gaps.append(f"The county list says {m(dc['amount_list'], 2)} but the property record says {m(dc['amount_record'], 2)}. Get a payoff letter from the treasurer.")
    if dc["status"] in ("stale", "removed"):
        gaps.append(dc["note"])
    if fl.get("sfha"):
        gaps.append("Inside a FEMA high-risk flood zone: lenders require flood insurance and resale buyers may be fewer.")
    if not p.get("street") or p.get("lat") is None:
        gaps.append("No street address or map location: confirm the property on the county map before any offer.")
    rule_html = ""
    if rules:
        rule_html = (f"<h2>{e(rules['name'])} tax sale rules</h2><p>{e(rules['kind'])}. Reviewed {e(rules['reviewed'])}.</p><ul>"
                     + "".join(f'<li><b>{e(h)}:</b> {e(t)} <a href="{e(u)}">Statute</a></li>' for h, t, u in rules["points"]) + "</ul>"
                     + (f"<p><b>Sale date:</b> {e(rules['sale_date'])}</p>" if rules.get("sale_date") else "")
                     + (f"<p><b>Redemption until about:</b> {e(rules['redemption']['ends'])} ({e(rules['redemption']['basis'])}). {e(rules['redemption']['assumes'])}</p>" if rules.get("redemption") else "")
                     + "<p><b>Checklist:</b></p><ul>" + "".join(f"<li>{e(c)}</li>" for c in rules["checklist"]) + f"</ul><p class=note>{e(rules['note'])}</p>")
    title = H.escape((p.get("street") or f"Parcel {p.get('parcel_number')}").title())
    css = ("body{font:13.5px/1.5 -apple-system,Segoe UI,Arial,sans-serif;color:#1d2420;margin:0;padding:32px;max-width:900px}h1{font-size:24px;margin:0}"
           "h2{font-size:16px;margin:26px 0 8px;padding-bottom:4px;border-bottom:2px solid #1A4A30}table{width:100%;border-collapse:collapse}"
           "td,th{padding:6px 8px;border-bottom:1px solid #e3e0d6;text-align:left;vertical-align:top}th{font-size:12px;color:#5E675F}.src{color:#5E675F;font-size:12px}"
           ".tag{display:inline-block;padding:2px 8px;border-radius:99px;background:#E8F1EA;color:#1A4A30;font-weight:600;font-size:12px}.note{color:#5E675F;font-size:12px}"
           "a{color:#1A4A30}.bar{display:flex;gap:8px;margin:0 0 20px}.bar button{padding:8px 14px;border-radius:8px;border:1px solid #1A4A30;background:#1A4A30;color:#fff;font-weight:600;cursor:pointer}"
           "@media print{.bar{display:none}body{padding:0}a{color:inherit;text-decoration:none}}")
    return (f"<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Report: {title}</title><style>{css}</style>"
            f"<div class=bar><button onclick='print()'>Print or save as PDF</button></div>"
            f"<p class=note>EstateHawk due-diligence report · {dt.date.today():%B %d, %Y}</p><h1>{title}</h1>"
            f"<p>{e(p.get('county_name'))} · Parcel {e(p.get('parcel_number'))} · <span class=tag>{e(dc['status'].title())}</span> {e(dc['note'])}</p>"
            f"<h2>Verified facts</h2><table><tr><th>Item</th><th>Value</th><th>Source</th></tr>{facts}</table>"
            f"<h2>Estimates</h2><table><tr><th>Item</th><th>Value</th><th>How it is worked out</th></tr>{ests}</table>"
            f"<h2>Why this score</h2><ul>{''.join(f'<li><b>{e(t)}:</b> {e(x)}</li>' for t, x in why)}</ul>"
            f"<h2>Tax history (county list)</h2><table><tr><th>Date</th><th>Amount owed</th><th>Owner</th></tr>{hist}</table>"
            f"<h2>Comparable sales</h2><table><tr><th>Address</th><th>Price</th><th>Sq ft</th><th>Miles</th><th>Date</th></tr>{comps_html}</table>"
            f"<h2>Deal math (estimates)</h2><table>{calc_rows}</table>"
            f"<h2>Missing information and warnings</h2><ul>{''.join(f'<li>{e(g)}</li>' for g in gaps)}</ul>{rule_html}"
            "<p class=note style='margin-top:28px'>Facts come from public county records as downloaded by EstateHawk; estimates are marked. "
            "This report is research, not an appraisal, title opinion or legal advice.</p></html>")


# ------------------------------------------------------------------ public API (read-only, key per company)
import hashlib as _hl, secrets as _sec, time as _time
_api_hits = {}  # key id -> [timestamps]
API_FIELDS = ["id", "county_name", "parcel_number", "owner_name", "street", "city", "state", "zip", "amount_owed", "total_due",
              "appraised_total", "est_equity", "years_behind", "score", "property_type", "lat", "lng", "mail_address", "mail_state",
              "first_seen", "last_seen", "is_active", "property_url", "sale_date", "min_bid", "flood_zone"]


@app.get("/api/keys")
def keys_list():
    return db.q("SELECT id, prefix, label, created, last_used, revoked FROM api_keys WHERE org_id=? ORDER BY id DESC", (OID(),))


@app.post("/api/keys")
async def keys_create(request: Request):
    require_export()  # paid plans only
    b = await request.json()
    if (db.q1("SELECT COUNT(*) n FROM api_keys WHERE org_id=? AND revoked=0", (OID(),)) or {}).get("n", 0) >= 5:
        raise HTTPException(400, "Up to 5 active keys. Revoke one first.")
    raw = "eh_" + _sec.token_urlsafe(30)
    db.run("INSERT INTO api_keys(org_id,key_hash,prefix,label,created) VALUES(?,?,?,?,?)",
           (OID(), _hl.sha256(raw.encode()).hexdigest(), raw[:10], (b.get("label") or "API key")[:60], jobs.now()))
    auth.audit("api key created", (b.get("label") or "")[:60])
    return {"key": raw, "note": "Copy it now: it is shown only once."}


@app.delete("/api/keys/{kid}")
def keys_revoke(kid: int):
    db.run("UPDATE api_keys SET revoked=1 WHERE id=? AND org_id=?", (kid, OID()))
    auth.audit("api key revoked", str(kid))
    return {"ok": True}


def _api_ctx(request: Request):
    """Bearer key -> the company's context (counties, plan, masking), 60 requests a minute per key."""
    h = request.headers.get("authorization", "")
    raw = h[7:].strip() if h.lower().startswith("bearer ") else request.headers.get("x-api-key", "").strip()
    if not raw:
        raise HTTPException(401, "Send your key: Authorization: Bearer eh_...")
    k = db.q1("SELECT * FROM api_keys WHERE key_hash=? AND revoked=0", (_hl.sha256(raw.encode()).hexdigest(),))
    if not k:
        raise HTTPException(401, "Unknown or revoked key")
    now_ = _time.time()
    hits = [t for t in _api_hits.get(k["id"], []) if now_ - t < 60]
    if len(hits) >= 60:
        raise HTTPException(429, "60 requests a minute. Slow down.")
    _api_hits[k["id"]] = hits + [now_]
    info = plans.org_info(k["org_id"])
    if not info or info["expired"] or not info["limits"]["export"]:
        raise HTTPException(402, "The API is on paid plans")
    u = db.q1("SELECT id, email, name, role, active, org_id FROM users WHERE org_id=? AND role='admin' AND active=1 ORDER BY id LIMIT 1", (k["org_id"],)) or {}
    db.run("UPDATE api_keys SET last_used=? WHERE id=?", (jobs.now(), k["id"]))
    return ctx.current.set({"user": u, "org_id": k["org_id"], "org": info, "super": False, "ip": auth.client_ip(request)})


@app.get("/v1/leads")
def api_leads(request: Request, county: int = 0, min_score: float = 0, updated_since: str = "", page: int = 1, per: int = 100):
    tok = _api_ctx(request)
    try:
        s, a = county_filter(county or "all")
        if min_score:
            s += " AND p.score>=?"; a.append(min_score)
        if updated_since:
            s += " AND p.last_seen>=?"; a.append(updated_since[:10])
        per, page = max(1, min(per, 500)), max(1, page)
        total = db.q1(f"SELECT COUNT(*) n FROM parcels p WHERE p.is_active=1 AND p.demo=0{s}", a)["n"]
        rows = db.q(f"""SELECT p.*, c.name county_name FROM parcels p JOIN counties c ON c.id=p.county_id
                        WHERE p.is_active=1 AND p.demo=0{s} ORDER BY p.score DESC, p.id LIMIT ? OFFSET ?""", a + [per, (page - 1) * per])
        rows = [{k2: r.get(k2) for k2 in API_FIELDS} for r in apply_mask(rows)]
        return {"total": total, "page": page, "per": per, "data": rows}
    finally:
        ctx.current.reset(tok)


@app.get("/v1/leads/{pid:path}")
def api_lead(pid: str, request: Request):
    tok = _api_ctx(request)
    try:
        p = get_parcel(pid)
        if plans.is_locked(INFO(), pid):
            p = plans.mask(p)
        out = {k2: p.get(k2) for k2 in API_FIELDS}
        out["history"] = db.q("SELECT date, amount, owner_name FROM snapshots WHERE parcel_id=? ORDER BY date", (pid,))
        return out
    finally:
        ctx.current.reset(tok)


@app.get("/v1/counties")
def api_counties(request: Request):
    tok = _api_ctx(request)
    try:
        cf, _ = county_filter(None, "x")
        rows = db.q(f"SELECT id, name, state, last_sync, sync_status, tax_sale_date FROM counties x WHERE enabled=1 AND demo=0{cf.replace('x.county_id', 'x.id')} ORDER BY state, name")
        q = quality.counties([r["id"] for r in rows]) if rows else {}
        for r in rows:
            r["leads"] = (q.get(r["id"]) or {}).get("n", 0)
            r["data_grade"] = quality.grade(q.get(r["id"]))
        return {"data": rows}
    finally:
        ctx.current.reset(tok)


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
    conv = db.q(f"""SELECT c.name county, COUNT(*) leads,
                    SUM(CASE WHEN pl.stage <> 'new' THEN 1 ELSE 0 END) contacted,
                    SUM(CASE WHEN pl.stage IN ('replied','negotiating','under_contract','closed') THEN 1 ELSE 0 END) replied,
                    SUM(CASE WHEN pl.stage='closed' THEN 1 ELSE 0 END) closed, COALESCE(SUM(CASE WHEN pl.stage='closed' THEN pl.fee END),0) fees,
                    AVG(p.score) avg_score FROM pipeline pl JOIN parcels p ON p.id=pl.parcel_id JOIN counties c ON c.id=p.county_id
                    WHERE pl.org_id={o}{s} GROUP BY c.name ORDER BY closed DESC, replied DESC, leads DESC""", a)
    for r in conv:
        r["reply_rate"] = round(100 * (r["replied"] or 0) / r["contacted"]) if r["contacted"] else None
        r["close_rate"] = round(100 * (r["closed"] or 0) / r["contacted"]) if r["contacted"] else None
        r["avg_score"] = round(r["avg_score"]) if r["avg_score"] is not None else None
    return {"conversion": conv,
            "kpi": {"found": found, "found_change": round((found - found_prev) * 100 / found_prev) if found_prev else None,
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
    role = (ctx.get().get("user") or {}).get("role")
    member_ok = {"calc_defaults", "onboarded"}  # a team member may change these; the rest is the company admin's
    if role not in ("admin", "superadmin") and any(k not in member_ok for k in b):
        raise HTTPException(403, "Only your company admin can change these settings")
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


# ------------------------------------------------------------------ online payment (Creem)
@app.get("/api/billing")
def billing_status():
    b = billing.get(OID())
    return {"online": billing.configured(), "mode": billing.mode(), "plan": INFO()["plan"], "status": b.get("status"),
            "period_end": b.get("period_end"), "has_portal": bool(b.get("customer_id")), "pending_plan": b.get("pending_plan") or None}


@app.post("/api/billing/request")
async def billing_request(request: Request):
    """Upgrade request while card payment is not switched on: emails EstateHawk and confirms to the customer."""
    b = await request.json()
    plan = b.get("plan") or ""
    if plan and (plan not in plans.PUBLIC or plan == "trial"):
        raise HTTPException(400, "Pick a plan")
    msg = (b.get("message") or "").strip()[:1500]
    if not plan and len(msg) < 3:
        raise HTTPException(400, "Write a short message")
    c = ctx.get()
    u, o = c.get("user") or {}, c.get("org") or {}
    if plan and u.get("role") not in ("admin", "superadmin"):
        raise HTTPException(403, "Only your company admin can change the plan")
    label = plans.PLANS[plan]["label"] if plan else ""
    import hashlib
    key = f"upgrade_req:{dt.date.today().isoformat()}:{plan or hashlib.sha1(msg.encode()).hexdigest()[:10]}"
    if db.q1("SELECT 1 FROM org_settings WHERE org_id=? AND key=?", (OID(), key)):
        return {"ok": True, "again": True}  # same request twice today: no second email
    db.run("INSERT INTO org_settings(org_id,key,value) VALUES(?,?,?)", (OID(), key, msg[:300]))
    auth.audit("upgrade request", f"{label or 'message'}: {msg[:300]}")
    details = [f"<b>Company:</b> {mailer.esc(o.get('name') or '')} (id {OID()}), now on {mailer.esc(o.get('label') or o.get('plan') or '')}",
               f"<b>From:</b> {mailer.esc(u.get('name') or '')} &lt;{mailer.esc(u.get('email') or '')}&gt;"]
    if label:
        details.append(f"<b>Wants:</b> {mailer.esc(label)} (${plans.PLANS[plan]['price']}/month)")
    if msg:
        details.append(mailer.esc(msg).replace("\n", "<br>"))
    details.append("Switch the plan in Admin > Companies > Edit, then reply to the customer.")
    mailer.send(os.environ.get("SUPPORT_EMAIL") or "support@getestatehawk.com",
                f"Upgrade request: {o.get('name') or ''} wants {label or 'to talk'}", "New upgrade request", details,
                reply_to=u.get("email"), foot="Sent from the Plans window in the EstateHawk app.")
    mailer.send(u.get("email"), f"We got your request{': ' + label if label else ''}", "Thanks, we are on it",
                [f"We got your request{' for the <b>' + mailer.esc(label) + '</b> plan' if label else ''}. "
                 "We will switch your account and email you the payment link the same business day.",
                 "Your trial keeps working in the meantime."])
    return {"ok": True}


@app.post("/api/billing/checkout")
async def billing_checkout(request: Request):
    b = await request.json()
    plan = b.get("plan")
    if plan not in billing.PLAN_PRODUCTS:
        raise HTTPException(400, "Pick a plan")
    if OID() == 1:
        raise HTTPException(400, "The owner company does not need a plan")
    u = ctx.get().get("user") or {}
    try:
        url = billing.start_checkout(OID(), plan, u.get("email"), site.base_url(request))
    except Exception as e:
        raise HTTPException(400, str(e))
    auth.audit("checkout started", plan)
    return {"url": url}


@app.post("/api/billing/confirm")
def billing_confirm():
    try:
        b = billing.confirm(OID())
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"plan": plans.org_info(OID())["plan"], "status": b.get("status")}


@app.post("/api/billing/portal")
def billing_portal():
    try:
        return {"url": billing.portal(OID())}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/public/creem/webhook")
async def creem_webhook(request: Request):
    raw = await request.body()
    if not billing.verify(raw, request.headers.get("creem-signature", "")):
        raise HTTPException(401, "Bad signature")
    try:
        note = billing.handle_event(json.loads(raw))
    except Exception as e:
        auth.audit("payment webhook failed", str(e)[:200], org=1)
        raise HTTPException(503, "Payment event could not be processed")
    auth.audit("payment webhook", note, org=1)
    return {"ok": True}


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
