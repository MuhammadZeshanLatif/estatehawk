"""Login for the hosted version: users, password hashing, signed session cookie, access rules.

First visit with no users shows "Create admin account". The admin adds team members in Settings > Team.
"""
import base64, hashlib, hmac, os, secrets, time

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from . import db

COOKIE = "eh_session"
DAYS = 30
_fails = {}  # ip -> [timestamps]

# open without login
PUBLIC = ("/api/auth/", "/static/", "/manifest.webmanifest")
# admin only (method, path prefix)
ADMIN = [("PUT", "/api/settings"), ("POST", "/api/integrations"), ("POST", "/api/counties"), ("PUT", "/api/counties"),
         ("DELETE", "/api/counties"), ("POST", "/api/demo"), ("*", "/api/users")]


def _secret():
    k = os.environ.get("SECRET_KEY")
    if k:
        return k.encode()
    path = os.path.join(db.ROOT, "data", "secret.key")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    return open(path).read().strip().encode()


def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2${salt}${h}"


def check_pw(pw, stored):
    try:
        _, salt, _h = stored.split("$")
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(hash_pw(pw, salt), stored)


def make_token(uid):
    exp = int(time.time()) + DAYS * 86400
    msg = f"{uid}.{exp}"
    sig = hmac.new(_secret(), msg.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{msg}.{sig}".encode()).decode()


def read_token(tok):
    try:
        uid, exp, sig = base64.urlsafe_b64decode(tok.encode()).decode().split(".")
    except Exception:
        return None
    good = hmac.new(_secret(), f"{uid}.{exp}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, good) or int(exp) < time.time():
        return None
    u = db.q1("SELECT id, email, name, role, active FROM users WHERE id=?", (int(uid),))
    return u if u and u["active"] else None


def current(request: Request):
    tok = request.cookies.get(COOKIE)
    return read_token(tok) if tok else None


def set_cookie(resp, request, uid):
    https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    resp.set_cookie(COOKIE, make_token(uid), max_age=DAYS * 86400, httponly=True, samesite="lax", secure=https)


def users_exist():
    return db.q1("SELECT COUNT(*) n FROM users")["n"] > 0


def throttle(ip):
    now = time.time()
    lst = [t for t in _fails.get(ip, []) if now - t < 600]
    _fails[ip] = lst
    if len(lst) >= 8:
        raise HTTPException(429, "Too many tries. Wait 10 minutes.")


def failed(ip):
    _fails.setdefault(ip, []).append(time.time())


async def middleware(request: Request, call_next):
    path = request.url.path
    needs = path.startswith("/api/") or path.startswith("/letters")
    if not needs or any(path.startswith(p) for p in PUBLIC):
        return await call_next(request)
    u = current(request)
    if not u:
        return JSONResponse({"detail": "Please log in", "login": True, "setup": not users_exist()}, status_code=401)
    for m, pre in ADMIN:
        if (m == "*" or m == request.method) and path.startswith(pre) and u["role"] != "admin":
            return JSONResponse({"detail": "Only the admin can change this"}, status_code=403)
    request.state.user = u
    return await call_next(request)
