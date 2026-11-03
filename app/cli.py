"""Command line jobs (used by GitHub Actions for the hosted version).

  python -m app.cli sync            download all counties, alerts, owner contacts, then the daily digest
  python -m app.cli add-known       add every known ISSG county that is not in the database yet
  python -m app.cli county ID       sync one county only (first download of a new county)
"""
import sys

from . import db, jobs, notify


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "sync"
    db.con()
    db.load_env()
    if cmd == "sync":
        res = jobs.sync_all()
        print(res)
        dg = db.get_setting("digest") or {}
        if dg.get("enabled"):
            s, b = jobs.digest_text()
            print(notify.deliver(db.get_setting("channels"), s, b))
        counties = {k: r for k, r in (res.get("results") or {}).items() if k != "contacts"}
        bad = [r for r in counties.values() if not r.get("ok")]
        return 1 if counties and len(bad) == len(counties) else 0
    if cmd == "add-known":
        from .counties import KNOWN_ISSG
        have = {r["name"] for r in db.q("SELECT name FROM counties")}
        for k in KNOWN_ISSG:
            if k["host"] and k["name"] not in have:
                cid = db.run("INSERT INTO counties(name,state,host,lat,lng) VALUES(?,?,?,?,?)",
                             (k["name"], k["state"], k["host"], k["lat"], k["lng"]))
                print("added", cid, k["name"])
        print([r["id"] for r in db.q("SELECT id FROM counties WHERE enabled=1 AND demo=0 AND sync_status='never' ORDER BY id")])
        return 0
    if cmd == "county":
        res = jobs.sync_county(int(argv[2]), enrich_limit=int(argv[3]) if len(argv) > 3 else 1500)
        print(res)
        return 0 if res.get("ok") else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
