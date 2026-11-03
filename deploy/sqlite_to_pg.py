"""Copy an EstateHawk SQLite file into PostgreSQL (Neon).

Usage:  DATABASE_URL=postgresql://... python deploy/sqlite_to_pg.py data/estatehawk.db
Tables are created by the app's own schema; existing rows with the same key are replaced.
"""
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db  # noqa: E402

TABLES = ["counties", "parcels", "snapshots", "sync_runs", "alerts", "pipeline", "contacts", "activities",
          "tasks", "offers", "settings", "users"]
KEYS = {"snapshots": ["parcel_id", "date"], "pipeline": ["parcel_id"], "settings": ["key"], "parcels": ["id"]}


def main(path):
    assert db.PG, "Set DATABASE_URL to a postgresql:// address first"
    src = sqlite3.connect(path)
    src.row_factory = sqlite3.Row
    pg = db.con()
    pg_cols = {}
    for t in TABLES:
        pg_cols[t] = {r["column_name"] for r in pg.execute(
            "SELECT column_name::text AS column_name FROM information_schema.columns WHERE table_name=?", (t,)).fetchall()}
    for t in TABLES:
        try:
            rows = src.execute(f"SELECT * FROM {t}").fetchall()
        except sqlite3.OperationalError:
            continue
        if not rows:
            continue
        cols = [c for c in rows[0].keys() if c in pg_cols[t]]
        keys = KEYS.get(t, ["id"])
        upd = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in keys) or None
        sql = (f"INSERT INTO {t}({','.join(cols)}) VALUES({','.join(['%s'] * len(cols))}) "
               f"ON CONFLICT ({','.join(keys)}) DO " + (f"UPDATE SET {upd}" if upd else "NOTHING"))
        cur = pg._c.cursor()
        cur.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
        if "id" in cols and t not in KEYS:  # keep SERIAL counters ahead of copied ids
            cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}','id'), (SELECT COALESCE(MAX(id),1) FROM {t}))")
        pg.commit()
        print(f"{t}: {len(rows)} rows")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(db.ROOT, "data", "estatehawk.db"))
