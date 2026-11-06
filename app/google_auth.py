"""Sign in with Google (OAuth 2.0, authorization code flow).

Needs GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (Google Cloud > APIs & Services > Credentials > OAuth client, type
"Web application", redirect URI <site>/api/auth/google/callback). Without them the Google buttons stay hidden.

Existing user with the same email -> logged in. New email -> a new trial company on the county picked on the signup
page; without a county the visitor goes back to /signup to pick one.
"""
import base64, hashlib, hmac, json, os, secrets, time
from urllib.parse import urlencode

import requests

from . import auth

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
COOKIE = "eh_google"


def configured():
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def redirect_uri(base):
    return base.rstrip("/") + "/api/auth/google/callback"


def _sign(data):
    raw = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(auth._secret(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def _unsign(val):
    try:
        raw, sig = val.rsplit(".", 1)
        if not hmac.compare_digest(sig, hmac.new(auth._secret(), raw.encode(), hashlib.sha256).hexdigest()):
            return None
        data = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        return data if data.get("exp", 0) > time.time() else None
    except Exception:  # noqa: BLE001
        return None


def start(base, county_id=None, company="", phone=""):
    """URL to send the visitor to, and the signed cookie that remembers the state (10 minutes)."""
    state = secrets.token_urlsafe(24)
    cookie = _sign({"state": state, "county": county_id, "company": (company or "")[:80], "phone": (phone or "")[:30], "exp": int(time.time()) + 600})
    q = {"client_id": os.environ["GOOGLE_CLIENT_ID"], "redirect_uri": redirect_uri(base), "response_type": "code",
         "scope": "openid email profile", "state": state, "prompt": "select_account", "access_type": "online"}
    return f"{AUTH_URL}?{urlencode(q)}", cookie


def finish(base, code, state, cookie):
    """Checks the state, swaps the code for Google's ID token and returns the verified profile, or raises ValueError."""
    saved = _unsign(cookie or "")
    if not saved or not state or not hmac.compare_digest(saved["state"], state):
        raise ValueError("The Google sign-in expired. Please try again.")
    r = requests.post(TOKEN_URL, timeout=20, data={"code": code, "client_id": os.environ["GOOGLE_CLIENT_ID"],
                                                   "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                                                   "redirect_uri": redirect_uri(base), "grant_type": "authorization_code"})
    if r.status_code != 200 or "id_token" not in r.json():
        raise ValueError("Google did not confirm the sign-in. Please try again.")
    info = requests.get(INFO_URL, params={"id_token": r.json()["id_token"]}, timeout=20)
    p = info.json() if info.status_code == 200 else {}
    if p.get("aud") != os.environ["GOOGLE_CLIENT_ID"] or p.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("Google did not confirm the sign-in. Please try again.")
    if str(p.get("email_verified")).lower() != "true" or not p.get("email"):
        raise ValueError("Your Google email is not verified yet.")
    return {"email": p["email"].strip().lower(), "name": (p.get("name") or p.get("given_name") or p["email"].split("@")[0])[:80],
            "county": saved.get("county"), "company": saved.get("company") or "", "phone": saved.get("phone") or ""}
