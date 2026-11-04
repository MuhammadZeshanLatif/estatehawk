"""Online payments through Creem (merchant of record).

Flow: a company admin picks a plan -> we create a Creem checkout -> the customer pays on Creem's page ->
Creem sends a webhook (and the customer comes back to /app#/billing) -> the company's plan switches.
Test mode (CREEM_MODE=test, the default) uses Creem's test server and test cards only.
"""
import hashlib, hmac, json, os, time

import requests

from . import db

PLAN_PRODUCTS = {"starter": "EstateHawk Starter", "pro": "EstateHawk Pro", "agency": "EstateHawk Agency"}
_cache = {"at": 0, "map": {}}


def mode():
    return "live" if (os.environ.get("CREEM_MODE") or "test").lower() == "live" else "test"


def base():
    return "https://api.creem.io/v1" if mode() == "live" else "https://test-api.creem.io/v1"


def configured():
    return bool(os.environ.get("CREEM_API_KEY"))


def _api(method, path, **kw):
    key = os.environ.get("CREEM_API_KEY")
    if not key:
        raise RuntimeError("Online payment is not set up yet")
    r = requests.request(method, base() + path, headers={"x-api-key": key, "Content-Type": "application/json"}, timeout=30, **kw)
    if r.status_code >= 400:
        try:
            msg = r.json().get("message") or r.text
        except Exception:
            msg = r.text
        raise RuntimeError(f"Payment provider error ({r.status_code}): {str(msg)[:200]}")
    return r.json()


def products():
    """plan -> Creem product id, found by product name (cached 10 minutes). CREEM_PRODUCT_<PLAN> env vars win."""
    if time.time() - _cache["at"] < 600 and _cache["map"]:
        return _cache["map"]
    found = {}
    page = 1
    while page and page < 10:
        j = _api("GET", "/products/search", params={"page_number": page, "page_size": 50})
        for p in j.get("items") or []:
            for plan, name in PLAN_PRODUCTS.items():
                if (p.get("name") or "").strip().lower() == name.lower() and (p.get("status") or "active") == "active":
                    found[plan] = p["id"]
        page = (j.get("pagination") or {}).get("next_page")
    for plan in PLAN_PRODUCTS:
        if os.environ.get(f"CREEM_PRODUCT_{plan.upper()}"):
            found[plan] = os.environ[f"CREEM_PRODUCT_{plan.upper()}"]
    _cache.update(at=time.time(), map=found)
    return found


def plan_for_product(pid):
    try:
        found = products()
    except Exception:
        return None
    for plan, p in found.items():
        if p == pid:
            return plan
    return None


# ------------------------------------------------------------------ per-company billing record (org_settings key "billing")
def get(org):
    r = db.q1("SELECT value FROM org_settings WHERE org_id=? AND key='billing'", (org,))
    try:
        return json.loads(r["value"]) if r and r["value"] else {}
    except Exception:
        return {}


def save(org, **changes):
    b = get(org)
    b.update({k: v for k, v in changes.items() if v is not None})
    b["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if db.q1("SELECT 1 FROM org_settings WHERE org_id=? AND key='billing'", (org,)):
        db.run("UPDATE org_settings SET value=? WHERE org_id=? AND key='billing'", (json.dumps(b), org))
    else:
        db.run("INSERT INTO org_settings(org_id,key,value) VALUES(?,?,?)", (org, "billing", json.dumps(b)))
    return b


def start_checkout(org, plan, email, site):
    pid = products().get(plan)
    if not pid:
        raise RuntimeError(f"The {plan} plan is not available for online payment yet")
    j = _api("POST", "/checkouts", json={
        "product_id": pid, "request_id": f"org{org}-{plan}-{int(time.time())}",
        "customer": {"email": email} if email else None,
        "success_url": f"{site}/app#/billing",
        "metadata": {"org_id": str(org), "plan": plan},
    })
    save(org, checkout_id=j.get("id"), pending_plan=plan, mode=mode())
    return j.get("checkout_url")


# ------------------------------------------------------------------ apply what Creem tells us
def set_plan(org, plan, status, sub_id=None, customer_id=None, period_end=None, source=""):
    """Paid -> the plan turns on. Canceled/expired/unpaid -> back to an ended trial (data kept, app locked until they pay)."""
    from . import auth
    if org == 1:
        return  # the owner company never changes plan
    o = db.q1("SELECT * FROM orgs WHERE id=?", (org,))
    if not o:
        return
    if status in ("active", "paid", "completed", "trialing"):
        if plan and plan != o["plan"]:
            db.run("UPDATE orgs SET plan=?, trial_ends=NULL, status='active' WHERE id=?", (plan, org))
            auth.audit("plan paid", f"{o['name']}: {o['plan']} -> {plan} ({source})", org=org)
        elif o["status"] != "active":
            db.run("UPDATE orgs SET status='active' WHERE id=?", (org,))
        save(org, plan=plan or o["plan"], status="active", subscription_id=sub_id, customer_id=customer_id, period_end=period_end,
             pending_plan="")
    elif status in ("scheduled_cancel",):
        save(org, status="canceling", subscription_id=sub_id, period_end=period_end)
    elif status in ("canceled", "expired", "unpaid", "past_due", "paused"):
        if status != "past_due":  # past_due: card retry still running, keep access for now
            yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
            db.run("UPDATE orgs SET plan='trial', trial_ends=? WHERE id=?", (yesterday, org))
            auth.audit("plan ended", f"{o['name']}: {o['plan']} ended ({status}, {source})", org=org)
        save(org, status=status, subscription_id=sub_id)


def _org_from(obj):
    md = obj.get("metadata") or {}
    if isinstance(obj.get("subscription"), dict) and not md:
        md = obj["subscription"].get("metadata") or {}
    oid = md.get("org_id")
    if oid and str(oid).isdigit():
        return int(oid)
    sub = obj.get("id") if str(obj.get("id", "")).startswith("sub_") else (obj.get("subscription") or {}).get("id") if isinstance(obj.get("subscription"), dict) else obj.get("subscription")
    if sub:
        for r in db.q("SELECT org_id, value FROM org_settings WHERE key='billing'"):
            try:
                if json.loads(r["value"]).get("subscription_id") == sub:
                    return r["org_id"]
            except Exception:
                pass
    return None


def _pid(obj):
    p = obj.get("product")
    return p.get("id") if isinstance(p, dict) else p


def handle_event(ev):
    """One webhook event from Creem. Returns a short note for the log."""
    kind, obj = ev.get("eventType") or "", ev.get("object") or {}
    org = _org_from(obj)
    if not org:
        return f"{kind}: no company found"
    cust = obj.get("customer")
    cust_id = cust.get("id") if isinstance(cust, dict) else cust
    if kind == "checkout.completed":
        sub = obj.get("subscription")
        sub_id = sub.get("id") if isinstance(sub, dict) else sub
        plan = (obj.get("metadata") or {}).get("plan") or plan_for_product(_pid(obj))
        set_plan(org, plan, "completed", sub_id, cust_id, source="checkout")
    elif kind.startswith("subscription."):
        status = obj.get("status") or kind.split(".", 1)[1]
        if kind == "subscription.paid":
            status = "paid"
        plan = (obj.get("metadata") or {}).get("plan") or plan_for_product(_pid(obj))
        set_plan(org, plan, status, obj.get("id"), cust_id, obj.get("current_period_end_date"), source=kind)
    elif kind == "refund.created":
        save(org, last_refund=time.strftime("%Y-%m-%d"))
    return f"{kind}: company {org}"


def verify(raw: bytes, signature: str):
    secret = os.environ.get("CREEM_WEBHOOK_SECRET") or ""
    if not secret or not signature:
        return False
    want = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, signature.strip())


def confirm(org):
    """After the customer comes back from Creem: ask Creem about the last checkout (works without webhooks too)."""
    b = get(org)
    cid = b.get("checkout_id")
    if not cid:
        return b
    j = _api("GET", "/checkouts", params={"checkout_id": cid})
    if (j.get("status") or "") == "completed" and str((j.get("metadata") or {}).get("org_id")) == str(org):
        sub = j.get("subscription")
        cust = j.get("customer")
        set_plan(org, (j.get("metadata") or {}).get("plan") or plan_for_product(_pid(j)), "completed",
                 sub.get("id") if isinstance(sub, dict) else sub, cust.get("id") if isinstance(cust, dict) else cust, source="return")
    return get(org)


def portal(org):
    b = get(org)
    if not b.get("customer_id"):
        raise RuntimeError("No paid subscription yet")
    return _api("POST", "/customers/billing", json={"customer_id": b["customer_id"]}).get("customer_portal_link")
