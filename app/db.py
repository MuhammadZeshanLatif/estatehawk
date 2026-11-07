"""Storage for EstateHawk.

Default: SQLite, one file data/estatehawk.db (your own computer, Oracle server).
If DATABASE_URL=postgres://... is set (hosted: Render + Neon), the same SQL runs on PostgreSQL:
the small SQLite-only bits are translated in pg_sql() below, so the rest of the app stays unchanged.
"""
import json, os, re, sqlite3, threading
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("ESTATEHAWK_DB", os.path.join(ROOT, "data", "estatehawk.db"))
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS counties (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'OH',
  host TEXT NOT NULL, platform TEXT NOT NULL DEFAULT 'issg',
  tax_year INTEGER, enabled INTEGER NOT NULL DEFAULT 1,
  lat REAL, lng REAL,
  last_sync TEXT, sync_status TEXT DEFAULT 'never', sync_error TEXT,
  delinquent_count INTEGER DEFAULT 0, tax_sale_date TEXT,
  demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS parcels (
  id TEXT PRIMARY KEY,               -- county_id:parcel_number
  county_id INTEGER NOT NULL, parcel_number TEXT NOT NULL,
  owner_name TEXT, school_district TEXT,
  street TEXT, city TEXT, state TEXT DEFAULT 'OH', zip TEXT,
  amount_owed REAL, property_url TEXT,
  first_seen TEXT, last_seen TEXT, is_active INTEGER DEFAULT 1,
  enriched_at TEXT, legal_desc TEXT, acres REAL,
  owner_full_name TEXT, mail_address TEXT, mail_state TEXT, mail_zip TEXT,
  land_use TEXT, land_value REAL, improvement_value REAL, appraised_total REAL,
  owner_occupied INTEGER, prior_due REAL, annual_tax REAL, total_due REAL,
  lat REAL, lng REAL,
  property_type TEXT, years_behind REAL, est_equity REAL, rent_est REAL,
  suggested_offer REAL, score REAL, score_breakdown TEXT,
  demo INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_parcels_county ON parcels(county_id);
CREATE INDEX IF NOT EXISTS ix_parcels_score ON parcels(score);
CREATE TABLE IF NOT EXISTS snapshots (
  parcel_id TEXT NOT NULL, date TEXT NOT NULL, amount REAL, owner_name TEXT,
  PRIMARY KEY (parcel_id, date)
);
CREATE TABLE IF NOT EXISTS sync_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, county_id INTEGER, started TEXT, finished TEXT,
  status TEXT, found INTEGER, new_count INTEGER, removed_count INTEGER, error TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, type TEXT NOT NULL,
  county_id INTEGER, parcel_id TEXT, title TEXT, body TEXT, score REAL,
  read INTEGER NOT NULL DEFAULT 0, sent INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pipeline (
  org_id INTEGER NOT NULL DEFAULT 1, parcel_id TEXT NOT NULL, stage TEXT NOT NULL, updated_at TEXT, fee REAL, closed_at TEXT,
  PRIMARY KEY (org_id, parcel_id)
);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, parcel_id TEXT, kind TEXT, value TEXT, norm TEXT, sources TEXT, note TEXT, created TEXT,
  UNIQUE(parcel_id, kind, norm)
);
CREATE TABLE IF NOT EXISTS activities (
  id INTEGER PRIMARY KEY AUTOINCREMENT, parcel_id TEXT, ts TEXT, kind TEXT, text TEXT, author TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, parcel_id TEXT, due TEXT, text TEXT, kind TEXT DEFAULT 'call', done INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS offers (
  id INTEGER PRIMARY KEY AUTOINCREMENT, parcel_id TEXT, created TEXT, price REAL,
  financing TEXT, closing_days INTEGER, earnest REAL, seller_credits TEXT,
  subject TEXT, body TEXT, source TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS orgs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, plan TEXT NOT NULL DEFAULT 'trial',
  status TEXT NOT NULL DEFAULT 'active', trial_ends TEXT, created TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS org_counties (org_id INTEGER NOT NULL, county_id INTEGER NOT NULL, PRIMARY KEY (org_id, county_id));
CREATE TABLE IF NOT EXISTS reveals (org_id INTEGER NOT NULL, parcel_id TEXT NOT NULL, ts TEXT, PRIMARY KEY (org_id, parcel_id));
CREATE TABLE IF NOT EXISTS alert_reads (org_id INTEGER NOT NULL, alert_id INTEGER NOT NULL, PRIMARY KEY (org_id, alert_id));
CREATE TABLE IF NOT EXISTS org_settings (org_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT, PRIMARY KEY (org_id, key));
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, org_id INTEGER, user_id INTEGER, user_name TEXT,
  action TEXT, detail TEXT, ip TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_ts ON audit_log(ts);
CREATE TABLE IF NOT EXISTS research_cache (parcel_id TEXT NOT NULL, kind TEXT NOT NULL, ts TEXT, data TEXT, PRIMARY KEY (parcel_id, kind));
CREATE TABLE IF NOT EXISTS api_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT, org_id INTEGER NOT NULL, key_hash TEXT NOT NULL, prefix TEXT, label TEXT,
  created TEXT, last_used TEXT, revoked INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE COLLATE NOCASE, name TEXT, pw TEXT,
  role TEXT DEFAULT 'member', active INTEGER DEFAULT 1, created TEXT, last_login TEXT
);
CREATE TABLE IF NOT EXISTS contact_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT NOT NULL, phone TEXT,
  message TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new'
);
CREATE TABLE IF NOT EXISTS blog_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', excerpt TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '', author TEXT NOT NULL DEFAULT 'EstateHawk',
  hero_image TEXT NOT NULL DEFAULT '', hero_alt TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'draft', created TEXT NOT NULL, updated TEXT NOT NULL,
  published TEXT
);
CREATE INDEX IF NOT EXISTS ix_blog_status ON blog_posts(status, published);
CREATE TABLE IF NOT EXISTS blog_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT, mime TEXT NOT NULL, data TEXT NOT NULL,
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS traffic_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, visitor_id TEXT NOT NULL, event TEXT NOT NULL,
  source TEXT NOT NULL, entry_type TEXT NOT NULL, entry_path TEXT NOT NULL,
  occurred TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_traffic_window ON traffic_events(occurred, source, entry_type);
CREATE UNIQUE INDEX IF NOT EXISTS ix_traffic_unique ON traffic_events(visitor_id, event);
CREATE TABLE IF NOT EXISTS traffic_users (user_id INTEGER PRIMARY KEY, visitor_id TEXT NOT NULL);
"""


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))

# tables whose INSERT should hand back the new id, and the conflict keys used for INSERT OR REPLACE
_SERIAL = {"counties", "sync_runs", "alerts", "contacts", "activities", "tasks", "offers", "users", "orgs", "audit_log", "contact_messages", "blog_posts", "blog_images", "traffic_events"}
_PK = {"parcels": ["id"], "snapshots": ["parcel_id", "date"], "pipeline": ["org_id", "parcel_id"], "settings": ["key"],
       "org_counties": ["org_id", "county_id"], "reveals": ["org_id", "parcel_id"], "alert_reads": ["org_id", "alert_id"],
       "org_settings": ["org_id", "key"], "traffic_users": ["user_id"]}


def pg_sql(sql):
    """Translate the SQLite dialect used in this app to PostgreSQL."""
    s = sql.replace("%", "%%")
    s = re.sub(r"(\w+(?:\.\w+)?) GLOB '\[0-9\]\*'", r"\1 ~ '^[0-9]'", s)
    s = s.replace("date('now','-1 day')", "to_char(CURRENT_DATE - 1, 'YYYY-MM-DD')")
    s = re.sub(r"\bLIKE\b", "ILIKE", s)
    s = re.sub(r"\bDESC\b(?!\s+NULLS)", "DESC NULLS LAST", s)
    m = re.match(r"\s*INSERT OR REPLACE INTO (\w+)\s*\(([^)]*)\)", s, re.I)
    if m:
        table, cols = m.group(1), [c.strip() for c in m.group(2).split(",")]
        keys = _PK[table]
        upd = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in keys)
        s = re.sub(r"INSERT OR REPLACE INTO", "INSERT INTO", s, count=1, flags=re.I).rstrip().rstrip(";")
        s += f" ON CONFLICT ({', '.join(keys)}) DO " + (f"UPDATE SET {upd}" if upd else "NOTHING")
    s = s.replace("?", "%s")
    m = re.match(r"\s*INSERT INTO (\w+)", s, re.I)
    if m and m.group(1) in _SERIAL and "RETURNING" not in s.upper():
        s = s.rstrip().rstrip(";") + " RETURNING id"
    return s


class _PGCursor:
    def __init__(self, cur, returning):
        self._cur, self._ret, self._rows = cur, returning, None

    def fetchall(self):
        return self._cur.fetchall() if self._cur.description else []

    def fetchone(self):
        return self._cur.fetchone() if self._cur.description else None

    @property
    def lastrowid(self):
        if not self._ret:
            return None
        r = self.fetchone()
        return r["id"] if r else None


class _PGConn:
    """Looks like the sqlite3 connection the app already uses (execute / commit / rollback)."""

    def __init__(self):
        self._c = None
        self._open()

    def _open(self):
        import psycopg
        from psycopg.rows import dict_row
        self._c = psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=False, connect_timeout=20,
                                  prepare_threshold=None)  # works with Neon pooled (PgBouncer) URLs too

    def execute(self, sql, args=()):
        import psycopg
        q = pg_sql(sql)
        if self._c.closed or self._c.broken:  # Neon closes idle connections (compute sleeps after 5 min)
            self._reopen()
        for attempt in (0, 1):
            try:
                cur = self._c.cursor()
                cur.execute(q, tuple(args))
                return _PGCursor(cur, q.endswith("RETURNING id"))
            except psycopg.OperationalError:
                if attempt:
                    raise
                self._reopen()

    def executemany(self, sql, seq):
        """Many rows in one go (pipelined), instead of one network round trip per row."""
        seq = [tuple(a) for a in seq]
        if not seq:
            return
        if self._c.closed or self._c.broken:
            self._reopen()
        with self._c.cursor() as cur:
            cur.executemany(pg_sql(sql), seq)

    def _reopen(self):
        try:
            self._c.close()
        except Exception:
            pass
        self._open()

    def commit(self):
        if not self._c.closed:
            self._c.commit()

    def rollback(self):
        try:
            self._c.rollback()
        except Exception:
            self._open()


def pg_schema():
    out = SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY").replace(" COLLATE NOCASE", "")
    out = re.sub(r"\bREAL\b", "DOUBLE PRECISION", out)
    return [st.strip() for st in out.split(";") if st.strip()]


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


_con = None


NEW_PARCEL_COLS = {"cert_year": "INTEGER", "beds": "INTEGER", "baths_full": "INTEGER", "baths_half": "INTEGER",
                   "year_built": "INTEGER", "living_area": "INTEGER", "style": "TEXT", "condition": "TEXT",
                   "stories": "REAL", "photo_url": "TEXT", "enrich_v": "INTEGER DEFAULT 0",
                   "contact_status": "TEXT", "contact_checked": "TEXT",
                   "flood_zone": "TEXT", "flood_sfha": "INTEGER", "flood_checked": "TEXT",
                   "sale_date": "TEXT", "min_bid": "REAL", "sale_status": "TEXT",
                   "owner_source": "TEXT", "owner_checked": "TEXT"}


def con():
    global _con
    if _con is None and PG:
        c = _PGConn()
        # an older app instance (still running during a deploy) may hold an open transaction that blocks table changes
        c.execute("""SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=current_database()
                     AND pid<>pg_backend_pid() AND state LIKE 'idle in transaction%'
                     AND now() - state_change > interval '2 minutes'""").fetchall()
        c.commit()
        c.execute("SET lock_timeout = '60s'")
        for st in pg_schema():
            c.execute(st)
        for k, t in NEW_PARCEL_COLS.items():
            c.execute(f"ALTER TABLE parcels ADD COLUMN IF NOT EXISTS {k} {t.replace('REAL', 'DOUBLE PRECISION')}")
        c.commit()
        _con = c
        migrate(c)
    if _con is None:
        _con = connect()
        _con.executescript(SCHEMA)
        have = {r[1] for r in _con.execute("PRAGMA table_info(parcels)")}
        for k, t in NEW_PARCEL_COLS.items():
            if k not in have:
                _con.execute(f"ALTER TABLE parcels ADD COLUMN {k} {t}")
        _con.commit()
        migrate(_con)
    return _con


@contextmanager
def tx():
    with _lock:
        c = con()
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise


def q(sql, args=()):
    with _lock:
        c = con()
        rows = [dict(r) for r in c.execute(sql, args).fetchall()]
        if PG:
            c.commit()  # never leave a read transaction open: it would block table changes on deploy
        return rows


def q1(sql, args=()):
    r = q(sql, args)
    return r[0] if r else None


def run(sql, args=()):
    with tx() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


DEFAULT_SETTINGS = {
    "weights": {"years_behind": 30, "equity": 30, "amount_owed": 15, "out_of_state": 15, "vacancy": 10},
    "alert_rules": {"score_above": True, "score_min": 85, "equity_above": True, "equity_min": 40000,
                    "new_in_counties": True, "auction_within": True, "auction_days": 30},
    "channels": {"email": False, "sms": False, "slack": False, "whatsapp": False},
    "digest": {"enabled": True, "time": "08:00"},
    "sync_time": "08:00",  # Pakistan time; Ohio sites refresh ~10 PM US Eastern = ~7-8 AM PKT
    "profile": {"name": "", "company": "", "email": "", "phone": "", "city": ""},
    "offer_defaults": {"discount_pct": 65, "financing": "Cash", "closing_days": 21, "earnest": 1000,
                       "seller_credits": "Buyer pays all closing costs", "sequence": "Tax-delinquent v2"},
    "deal_types": ["wholesale"],
    # owner phone/email search with Gemini + Google Search after each sync (free key: keep it small)
    "contact_lookup": {"enabled": True, "per_day": 50, "min_score": 0},
    "onboarded": False,
    "demo": False,
    # deal calculator: what the investor wants to make and how careful to be
    "calc_defaults": {"profit_pct": 20, "risk": "medium", "repair_per_sqft": 25, "buy_closing_pct": 2, "sell_closing_pct": 8,
                      "hold_months": 6, "monthly_hold": 250},
}


def _get_global(key):
    r = q1("SELECT value FROM settings WHERE key=?", (key,))
    if r is None:
        return json.loads(json.dumps(DEFAULT_SETTINGS.get(key)))
    return json.loads(r["value"])


def _set_global(key, value):
    run("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value)))


def all_settings():
    out = {k: get_setting(k) for k in DEFAULT_SETTINGS}
    return out


def load_env():
    """Hosted mode: API keys saved from Settings > Integrations live in the database (disk is not kept)."""
    if PG:
        for k, v in (get_setting("_env") or {}).items():
            if v and not os.environ.get(k):
                os.environ[k] = v


# ------------------------------------------------------------------ companies (multi-tenant) migration
def columns(c, table):
    if PG:
        return {r["column_name"] for r in c.execute(
            "SELECT column_name::text AS column_name FROM information_schema.columns WHERE table_name=?", (table,)).fetchall()}
    return {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}


def migrate(c):
    """One-time upgrade of a single-team database to companies. Existing data becomes company #1 (EstateHawk HQ)."""
    if "avatar" not in columns(c, "users"):
        c.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
    if "tour_seen" not in columns(c, "users"):
        c.execute("ALTER TABLE users ADD COLUMN tour_seen INTEGER DEFAULT 0")
    if "token_ver" not in columns(c, "users"):  # session version: logout / password change ends old sessions
        c.execute("ALTER TABLE users ADD COLUMN token_ver INTEGER DEFAULT 0")
    if "email_verified" not in columns(c, "users"):  # accounts made before this are trusted; new email signups confirm
        c.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 1")
    if "phone" not in columns(c, "users"):
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    for t in ("activities", "tasks", "offers", "users"):
        if "org_id" not in columns(c, t):
            c.execute(f"ALTER TABLE {t} ADD COLUMN org_id INTEGER")
    if "org_id" not in columns(c, "pipeline"):  # old single-team pipeline: rebuild with (org_id, parcel_id) key
        c.execute("""CREATE TABLE pipeline_new (org_id INTEGER NOT NULL DEFAULT 1, parcel_id TEXT NOT NULL, stage TEXT NOT NULL,
                     updated_at TEXT, fee REAL, closed_at TEXT, PRIMARY KEY (org_id, parcel_id))""")
        c.execute("INSERT INTO pipeline_new(org_id,parcel_id,stage,updated_at,fee,closed_at) SELECT 1,parcel_id,stage,updated_at,fee,closed_at FROM pipeline")
        c.execute("DROP TABLE pipeline")
        c.execute("ALTER TABLE pipeline_new RENAME TO pipeline")
    if "assigned_to" not in columns(c, "pipeline"):  # team member who works the lead
        c.execute("ALTER TABLE pipeline ADD COLUMN assigned_to INTEGER")
    if "lost_reason" not in columns(c, "pipeline"):
        c.execute("ALTER TABLE pipeline ADD COLUMN lost_reason TEXT")
    if not c.execute("SELECT id FROM orgs WHERE id=1").fetchone():
        from datetime import datetime
        c.execute("INSERT INTO orgs(id,name,plan,status,created) VALUES(?,?,?,?,?)",
                  (1, "EstateHawk HQ", "internal", "active", datetime.now().isoformat(sep=" ", timespec="seconds")))
        if PG:
            c.execute("SELECT setval(pg_get_serial_sequence('orgs','id'), (SELECT MAX(id) FROM orgs))")
        c.execute("UPDATE activities SET org_id=1 WHERE org_id IS NULL AND COALESCE(author,'') NOT IN ('Gemini','Google')")
        c.execute("UPDATE tasks SET org_id=1 WHERE org_id IS NULL")
        c.execute("UPDATE offers SET org_id=1 WHERE org_id IS NULL")
        c.execute("UPDATE users SET org_id=1 WHERE org_id IS NULL")
        c.execute("INSERT INTO alert_reads(org_id, alert_id) SELECT 1, id FROM alerts WHERE read=1")
    if not c.execute("SELECT 1 FROM users WHERE role='superadmin'").fetchone():
        first = c.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        if first:
            c.execute("UPDATE users SET role='superadmin', org_id=1 WHERE id=?", (first["id"] if PG else first[0],))
    c.commit()


# settings that each company keeps for itself (the rest are global, owned by the super admin)
ORG_KEYS = {"profile", "offer_defaults", "alert_rules", "channels", "digest", "deal_types", "onboarded", "calc_defaults"}


def _org():
    from . import ctx
    return ctx.org_id()


def get_setting(key, org=None):
    org = org or _org()
    if key in ORG_KEYS and org and org != 1:
        r = q1("SELECT value FROM org_settings WHERE org_id=? AND key=?", (org, key))
        if r is not None:
            return json.loads(r["value"])
        if key == "onboarded":
            return False
        if key == "profile":
            o = q1("SELECT name FROM orgs WHERE id=?", (org,))
            return {"name": "", "company": o["name"] if o else "", "email": "", "phone": "", "city": "Ohio"}
    return _get_global(key)


def set_setting(key, value, org=None):
    org = org or _org()
    if key in ORG_KEYS and org and org != 1:
        run("INSERT INTO org_settings(org_id,key,value) VALUES(?,?,?) ON CONFLICT(org_id,key) DO UPDATE SET value=excluded.value",
            (org, key, json.dumps(value)))
    else:
        _set_global(key, value)
