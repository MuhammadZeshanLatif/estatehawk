"""Command line jobs (used by GitHub Actions for the hosted version).

  python -m app.cli sync        download all counties, alerts, owner contacts, then the daily digest
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
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
