"""Command line jobs (used by GitHub Actions for the hosted version).

  python -m app.cli sync            download all counties, alerts, owner contacts, then the daily digest
  python -m app.cli add-known       add every known ISSG county that is not in the database yet
  python -m app.cli county ID       sync one county only (first download of a new county)
"""
import sys

from . import db, jobs, notify


def add_lgbs():
    """Every county with Linebarger tax-sale listings (Texas + Philadelphia) becomes a county here."""
    from .scraper.files import FileClient
    fc = FileClient("lgbs:TX:X")
    have = {r["host"] for r in db.q("SELECT host FROM counties")}
    added = []
    for it in fc.get("https://taxsales.lgbs.com/api/sale_counties/?limit=1000").json().get("results", []):
        st, cn = it["state"].upper(), it["county"].upper()
        host = f"lgbs:{st}:{cn}"
        if host not in have:
            added.append(db.run("INSERT INTO counties(name,state,host,platform) VALUES(?,?,?,?)", (cn.title(), st, host, "lgbs")))
            print("added", added[-1], cn.title(), st)
    return added


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
        have = {(r["name"], r["state"]) for r in db.q("SELECT name, state FROM counties")}
        added = []
        for k in KNOWN_ISSG:
            if k["host"] and (k["name"], k["state"]) not in have:
                cid = db.run("INSERT INTO counties(name,state,host,lat,lng) VALUES(?,?,?,?,?)",
                             (k["name"], k["state"], k["host"], k["lat"], k["lng"]))
                print("added", cid, k["name"])
                added.append(cid)
        added += add_lgbs()
        print(added)
        return 0
    if cmd == "add-lgbs":
        print(add_lgbs())
        return 0
    if cmd == "_old-add-lgbs":
        # every county with Linebarger tax-sale listings (Texas + Philadelphia) becomes a county here
        from .scraper.files import FileClient
        fc = FileClient("lgbs:TX:X")
        have = {r["host"] for r in db.q("SELECT host FROM counties")}
        added = []
        for it in fc.get("https://taxsales.lgbs.com/api/sale_counties/?limit=1000").json().get("results", []):
            st, cn = it["state"].upper(), it["county"].upper()
            host = f"lgbs:{st}:{cn}"
            if host in have:
                continue
            cid = db.run("INSERT INTO counties(name,state,host,platform) VALUES(?,?,?,?)", (cn.title(), st, host, "lgbs"))
            added.append(cid)
            print("added", cid, cn.title(), st)
        print(added)
        return 0
    if cmd == "reenrich":
        # read the property pages of a county again (e.g. address was not saved the first time) and drop bad map points
        cid = int(argv[2])
        db.run("UPDATE parcels SET enriched_at=NULL, lat=NULL, lng=NULL WHERE county_id=? AND (street IS NULL OR street NOT GLOB '[0-9]*')", (cid,))
        res = jobs.sync_county(cid, enrich_limit=int(argv[3]) if len(argv) > 3 else 5000)
        print(res)
        return 0 if res.get("ok") else 1
    if cmd == "fix-points":
        # one-off clean-up of badly placed map points in every county
        for r in db.q("SELECT id, name FROM counties"):
            n = jobs.drop_stray_points(r["id"])
            if n:
                print(r["name"], "removed", n)
        return 0
    if cmd == "fill-ohio":
        # map points + addresses from the Ohio statewide layers, for counties whose list has parcel numbers only
        ids = [int(x) for x in argv[2:]] or [r["id"] for r in db.q("SELECT id FROM counties WHERE state='OH' AND enabled=1 AND demo=0")]
        for cid in ids:
            c = db.q1("SELECT * FROM counties WHERE id=?", (cid,))
            if c:
                placed, addressed = jobs.fill_from_state(c, addr_limit=3000)
                jobs.fill_flood(cid, limit=1000)
                if placed or addressed:
                    jobs.rescore([r["id"] for r in db.q("SELECT id FROM parcels WHERE county_id=?", (cid,))], quiet=True)
        return 0
    if cmd == "county":
        res = jobs.sync_county(int(argv[2]), enrich_limit=int(argv[3]) if len(argv) > 3 else 1500)
        print(res)
        return 0 if res.get("ok") else 1
    if cmd == "status":
        for r in db.q("""SELECT c.id, c.name, c.sync_status, c.last_sync, c.sync_error,
                         (SELECT COUNT(*) FROM parcels p WHERE p.county_id=c.id AND p.is_active=1) AS active,
                         (SELECT COUNT(*) FROM parcels p WHERE p.county_id=c.id AND p.is_active=1 AND p.lat IS NOT NULL) AS mapped,
                         (SELECT COUNT(*) FROM parcels p WHERE p.county_id=c.id AND p.is_active=1 AND p.enriched_at IS NOT NULL) AS detailed
                         FROM counties c WHERE c.demo=0 ORDER BY c.id"""):
            print(f"C {r['id']}|{r['name']}|{r['sync_status']}|{r['last_sync']}|active={r['active']}|mapped={r['mapped']}|detailed={r['detailed']}|{(r['sync_error'] or '')[:120]}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
