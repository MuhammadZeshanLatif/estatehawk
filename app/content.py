"""First-party blog publishing and source-attributed traffic funnel."""
import base64
import binascii
import datetime as dt
import html
import json
import re
import secrets
from urllib.parse import urlparse

from fastapi import HTTPException

from . import db

COOKIE = "eh_visitor"
SOURCES = ("Meta ad", "Google ad", "Other paid", "Google organic", "Other organic", "Referral", "Direct / unknown")
EVENTS = ("landed", "signup", "verified", "paid")


def source(request):
    q = request.query_params
    utm = (q.get("utm_source") or "").lower()[:60]
    medium = (q.get("utm_medium") or "").lower()[:60]
    if q.get("fbclid") or (utm in ("meta", "facebook", "instagram", "fb", "ig") and medium in ("cpc", "paid", "ppc", "paid_social")):
        return "Meta ad"
    if q.get("gclid") or (utm == "google" and medium in ("cpc", "paid", "ppc")):
        return "Google ad"
    if medium in ("cpc", "paid", "ppc", "paid_social", "display"):
        return "Other paid"
    if utm == "google" and medium in ("organic", "search"):
        return "Google organic"
    if medium in ("organic", "search"):
        return "Other organic"
    if utm:
        return "Referral"
    ref = urlparse(request.headers.get("referer", ""))
    host = (ref.hostname or "").lower()
    if host and host != (request.url.hostname or "").lower():
        if host.endswith("google.com") or host.startswith("google."):
            return "Google organic"
        if any(host.endswith(x) for x in ("bing.com", "yahoo.com", "duckduckgo.com")):
            return "Other organic"
        return "Referral"
    return "Direct / unknown"


def visitor(request):
    value = request.cookies.get(COOKIE, "")
    return value if re.fullmatch(r"[0-9a-f]{32}", value) else secrets.token_hex(16)


def track(request, event, visitor_id=None):
    if event not in EVENTS:
        return
    vid = visitor_id or visitor(request)
    first = db.q1("SELECT source,entry_type,entry_path FROM traffic_events WHERE visitor_id=? ORDER BY id LIMIT 1", (vid,))
    path = request.url.path[:180]
    entry = "blog" if path == "/blog" or path.startswith("/blog/") else "non_blog"
    fields = first or {"source": source(request), "entry_type": entry, "entry_path": path}
    try:
        db.run("INSERT INTO traffic_events(visitor_id,event,source,entry_type,entry_path,occurred) VALUES(?,?,?,?,?,?)",
               (vid, event, fields["source"], fields["entry_type"], fields["entry_path"], dt.datetime.now(dt.timezone.utc).isoformat()))
    except Exception as exc:
        # A repeated step is expected. Any other storage failure should surface.
        if "unique" not in str(exc).lower() and "duplicate" not in str(exc).lower():
            raise


def track_safely(request, event, visitor_id=None):
    """Measurement must never prevent a visit, signup or email confirmation."""
    try:
        track(request, event, visitor_id)
    except Exception:
        pass


def visitor_for_user(user_id):
    try:
        row = db.q1("SELECT visitor_id FROM traffic_users WHERE user_id=?", (user_id,))
        return row["visitor_id"] if row else None
    except Exception:
        return None


def paid_org(org_id):
    """Record a verified paid transition even when the customer never returns from checkout."""
    row = db.q1("SELECT t.visitor_id FROM traffic_users t JOIN users u ON u.id=t.user_id WHERE u.org_id=? AND u.role='admin' ORDER BY u.id LIMIT 1", (org_id,))
    if not row:
        return
    first = db.q1("SELECT source,entry_type,entry_path FROM traffic_events WHERE visitor_id=? ORDER BY id LIMIT 1", (row["visitor_id"],))
    if not first:
        return
    try:
        db.run("INSERT INTO traffic_events(visitor_id,event,source,entry_type,entry_path,occurred) VALUES(?,?,?,?,?,?)",
               (row["visitor_id"], "paid", first["source"], first["entry_type"], first["entry_path"], dt.datetime.now(dt.timezone.utc).isoformat()))
    except Exception as exc:
        if "unique" not in str(exc).lower() and "duplicate" not in str(exc).lower():
            raise


def funnel(days=30):
    days = max(1, min(int(days), 365))
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat()
    rows = db.q("SELECT source,entry_type,event,COUNT(*) n FROM traffic_events WHERE occurred>=? GROUP BY source,entry_type,event", (since,))
    path_rows = db.q("SELECT source,entry_path,event,COUNT(*) n FROM traffic_events WHERE occurred>=? GROUP BY source,entry_path,event", (since,))
    groups = {(s, e): {k: 0 for k in EVENTS} for s in SOURCES for e in ("blog", "non_blog")}
    for row in rows:
        if row["event"] in EVENTS:
            groups.setdefault((row["source"], row["entry_type"]), {k: 0 for k in EVENTS})[row["event"]] = row["n"]
    paths = {}
    for row in path_rows:
        key = (row["source"], row["entry_path"])
        if row["event"] in EVENTS:
            paths.setdefault(key, {k: 0 for k in EVENTS})[row["event"]] = row["n"]
    landing = sorted(({"source": s, "path": p, **v} for (s, p), v in paths.items()),
                     key=lambda row: row["landed"], reverse=True)[:20]
    return {"days": days, "rows": [{"source": s, "entry_type": e, **v} for (s, e), v in groups.items()], "landing": landing,
            "totals": {k: sum(v[k] for v in groups.values()) for k in EVENTS}}


def posts(status=None):
    if status == "published":
        return db.q("SELECT * FROM blog_posts WHERE status='published' ORDER BY published DESC, id DESC")
    return db.q("SELECT * FROM blog_posts ORDER BY updated DESC, id DESC")


def post(slug, published_only=True):
    sql = "SELECT * FROM blog_posts WHERE slug=?" + (" AND status='published'" if published_only else "")
    return db.q1(sql, (slug,))


def save(payload, post_id=None):
    title = str(payload.get("title") or "").strip()[:140]
    slug = str(payload.get("slug") or "").strip().lower()
    desc = str(payload.get("description") or "").strip()[:300]
    excerpt = str(payload.get("excerpt") or "").strip()[:600]
    body = str(payload.get("body") or "").strip()
    author = str(payload.get("author") or "EstateHawk").strip()[:100]
    hero_image = str(payload.get("hero_image") or "").strip()
    hero_alt = str(payload.get("hero_alt") or "").strip()[:180]
    status = payload.get("status") or "draft"
    if not title or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or not body or status not in ("draft", "published"):
        raise HTTPException(400, "Add a title, URL slug and article body before saving.")
    if len(body) > 100000:
        raise HTTPException(400, "Article is too long.")
    if hero_image and (not re.fullmatch(r"/blog-media/[0-9]+", hero_image) or not hero_alt):
        raise HTTPException(400, "Upload a cover image and describe it for readers using a screen reader.")
    existing = db.q1("SELECT id,published FROM blog_posts WHERE id=?", (post_id,)) if post_id else None
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    published = (existing or {}).get("published") or (now if status == "published" else None)
    try:
        if post_id:
            if not existing:
                raise HTTPException(404, "Article not found")
            db.run("UPDATE blog_posts SET slug=?,title=?,description=?,excerpt=?,body=?,author=?,hero_image=?,hero_alt=?,status=?,updated=?,published=? WHERE id=?",
                   (slug, title, desc, excerpt, body, author, hero_image, hero_alt, status, now, published, post_id))
            return db.q1("SELECT * FROM blog_posts WHERE id=?", (post_id,))
        new_id = db.run("INSERT INTO blog_posts(slug,title,description,excerpt,body,author,hero_image,hero_alt,status,created,updated,published) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (slug, title, desc, excerpt, body, author, hero_image, hero_alt, status, now, now, published))
        return db.q1("SELECT * FROM blog_posts WHERE id=?", (new_id,))
    except Exception as exc:
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise HTTPException(409, "This URL slug is already used.")
        raise


def upload_image(encoded):
    if not isinstance(encoded, str) or len(encoded) > 2_000_000:
        raise HTTPException(400, "Choose a JPG, PNG or WebP image under 1.5 MB.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(400, "Image could not be read.")
    if len(raw) > 1_500_000:
        raise HTTPException(400, "Choose an image under 1.5 MB.")
    mime = ("image/jpeg" if raw.startswith(b"\xff\xd8\xff") else
            "image/png" if raw.startswith(b"\x89PNG\r\n\x1a\n") else
            "image/webp" if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP" else None)
    if not mime:
        raise HTTPException(400, "Choose a JPG, PNG or WebP image.")
    image_id = db.run("INSERT INTO blog_images(mime,data,created) VALUES(?,?,?)",
                      (mime, encoded, dt.datetime.now(dt.timezone.utc).isoformat()))
    return f"/blog-media/{image_id}"


def body_html(body):
    """Render a small Markdown subset. Escape all user HTML and allow no raw scripts."""
    chunks, para, items = [], [], []
    def flush():
        if para:
            chunks.append("<p>" + " ".join(para) + "</p>"); para.clear()
        if items:
            chunks.append("<ul>" + "".join(f"<li>{v}</li>" for v in items) + "</ul>"); items.clear()
    def inline(value):
        value = html.escape(value)
        value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+|/[^\s)]*)\)",
                       lambda m: f'<a href="{m.group(2)}" rel="noopener noreferrer">{m.group(1)}</a>', value)
        return value
    for line in body.splitlines():
        line = line.strip()
        if not line:
            flush(); continue
        if line.startswith("## ") or line.startswith("### "):
            flush(); level = 3 if line.startswith("### ") else 2
            chunks.append(f"<h{level}>{inline(line[level+1:])}</h{level}>")
        elif line.startswith("- "):
            if para: flush()
            items.append(inline(line[2:]))
        else:
            if items: flush()
            para.append(inline(line))
    flush()
    return "".join(chunks)
