"""Copy a Postgres EstateHawk database (e.g. the Neon "testing" branch) into a local SQLite file.
The test server then runs on this local copy: live-like data, but fast and offline.

  SOURCE_DATABASE_URL=postgresql://... python tools/pg_to_sqlite.py data/estatehawk.db.new
"""
import os
import sys
import time

src = os.environ.get("SOURCE_DATABASE_URL", "").strip()
dst = sys.argv[1] if len(sys.argv) > 1 else "data/estatehawk.db.new"
if not src.startswith("postgres"):
    sys.exit("SOURCE_DATABASE_URL is missing (paste the Neon testing link in test-database.env)")
os.environ.pop("DATABASE_URL", None)  # build the local file with the SQLite schema, never touch Postgres schema
os.environ["ESTATEHAWK_DB"] = os.path.abspath(dst)
for f in (dst, dst + "-wal", dst + "-shm"):
    if os.path.exists(f):
        os.remove(f)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg  # noqa: E402
from app import db  # noqa: E402

lite = db.con()  # empty database with the full app schema
tables = [r[0] for r in lite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
t0 = time.time()
with psycopg.connect(src, prepare_threshold=None, connect_timeout=30) as pg:
    pg_tables = {r[0] for r in pg.execute("SELECT table_name::text FROM information_schema.tables WHERE table_schema='public'")}
    for t in tables:
        if t not in pg_tables:
            continue
        with pg.cursor() as c:
            c.execute(f'SELECT * FROM "{t}" LIMIT 0')
            pcols = [d.name for d in c.description]
        lcols = {r[1] for r in lite.execute(f'PRAGMA table_info("{t}")')}
        cols = [c for c in pcols if c in lcols]
        lite.execute(f'DELETE FROM "{t}"')
        n = 0
        with pg.cursor(name=f"copy_{t}") as c:  # server-side cursor: stream big tables
            c.itersize = 5000
            c.execute(f'SELECT {", ".join(chr(34) + x + chr(34) for x in cols)} FROM "{t}"')
            ins = f'INSERT OR REPLACE INTO "{t}" ({", ".join(cols)}) VALUES ({", ".join("?" * len(cols))})'
            while True:
                rows = c.fetchmany(5000)
                if not rows:
                    break
                lite.executemany(ins, [tuple(float(v) if type(v).__name__ == "Decimal" else v for v in r) for r in rows])
                n += len(rows)
        lite.commit()
        print(f"  {t}: {n:,} rows", flush=True)
lite.execute("PRAGMA wal_checkpoint(TRUNCATE)")
lite.close()
print(f"Done in {time.time() - t0:.0f}s -> {dst}")
