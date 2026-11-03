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
  parcel_id TEXT PRIMARY KEY, stage TEXT NOT NULL, updated_at TEXT, fee REAL, closed_at TEXT
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
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE COLLATE NOCASE, name TEXT, pw TEXT,
  role TEXT DEFAULT 'member', active INTEGER DEFAULT 1, created TEXT, last_login TEXT
);
"""


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))

# tables whose INSERT should hand back the new id, and the conflict keys used for INSERT OR REPLACE
_SERIAL = {"counties", "sync_runs", "alerts", "contacts", "activities", "tasks", "offers", "users"}
_PK = {"parcels": ["id"], "snapshots": ["parcel_id", "date"], "pipeline": ["parcel_id"], "settings": ["key"]}


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
                   "contact_status": "TEXT", "contact_checked": "TEXT"}


def con():
    global _con
    if _con is None and PG:
        c = _PGConn()
        for st in pg_schema():
            c.execute(st)
        for k, t in NEW_PARCEL_COLS.items():
            c.execute(f"ALTER TABLE parcels ADD COLUMN IF NOT EXISTS {k} {t.replace('REAL', 'DOUBLE PRECISION')}")
        c.commit()
        _con = c
    if _con is None:
        _con = connect()
        _con.executescript(SCHEMA)
        have = {r[1] for r in _con.execute("PRAGMA table_info(parcels)")}
        for k, t in NEW_PARCEL_COLS.items():
            if k not in have:
                _con.execute(f"ALTER TABLE parcels ADD COLUMN {k} {t}")
        _con.commit()
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
        return [dict(r) for r in con().execute(sql, args).fetchall()]


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
    "profile": {"name": "Ashhad", "company": "EstateHawk", "email": "", "phone": "", "city": "Ohio"},
    "offer_defaults": {"discount_pct": 65, "financing": "Cash", "closing_days": 21, "earnest": 1000,
                       "seller_credits": "Buyer pays all closing costs", "sequence": "Tax-delinquent v2"},
    "deal_types": ["wholesale"],
    # owner phone/email search with Gemini + Google Search after each sync (free key: keep it small)
    "contact_lookup": {"enabled": True, "per_day": 50, "min_score": 0},
    "onboarded": False,
    "demo": False,
}


def get_setting(key):
    r = q1("SELECT value FROM settings WHERE key=?", (key,))
    if r is None:
        return json.loads(json.dumps(DEFAULT_SETTINGS.get(key)))
    return json.loads(r["value"])


def set_setting(key, value):
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
