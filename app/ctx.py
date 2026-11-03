"""Who is making the current request: user, company (org) and its plan. Set by auth.middleware."""
import contextvars

current = contextvars.ContextVar("eh_ctx", default=None)


def get():
    return current.get() or {}


def org_id():
    return get().get("org_id")
