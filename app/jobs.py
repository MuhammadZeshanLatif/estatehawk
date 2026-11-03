"""Daily sync: download each county's delinquent list, compare with yesterday, enrich new parcels,
score everything, create alerts, and send the daily digest."""
import re
import datetime as dt, json, threading, time, traceback

from . import db, scoring, notify, geocode, contacts
from .scraper.issg import IssgClient
from .scraper.files import FileClient

FILE_PREFIXES = ("file", "lgbs")

ENRICH_V = 2  # bump when the property reader learns new fields: parcels are read again once
STATUS = {"running": False, "county": None, "step": "", "progress": 0}
_lock = threading.Lock()


def now():
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def today():
    return dt.date.today().isoformat()


def alert(type_, title, body="", county_id=None, parcel_id=None, score=None):
    db.run("INSERT INTO alerts(ts,type,county_id,parcel_id,title,body,score) VALUES(?,?,?,?,?,?,?)",
           (now(), type_, county_id, parcel_id, title, body, score))


def rescore(parcel_ids=None, quiet=False):
    """Recompute derived fields + score. Creates high-score alerts when a parcel crosses the threshold."""
    weights = db.get_setting("weights")
    rules = db.get_setting("alert_rules")
    disc = db.get_setting("offer_defaults").get("discount_pct", 65)
    if parcel_ids is None:
        rows = db.q("SELECT * FROM parcels")
    else:
        ids = list(parcel_ids)
        rows = []
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            rows += db.q(f"SELECT * FROM parcels WHERE id IN ({','.join('?' * len(chunk))})", chunk)
    upd, alerts = [], []
    with db.tx() as c:
        for p in rows:
            old = p.get("score")
            scoring.derive(p)
            s, br = scoring.score(p, weights)
            off = scoring.suggested_offer(p, disc)
            upd.append((p["property_type"], p["years_behind"], p["est_equity"], p["rent_est"], off, s, json.dumps(br), p["id"]))
            if not quiet and rules.get("score_above") and s >= rules.get("score_min", 85) and (old is None or old < rules.get("score_min", 85)) \
                    and p.get("is_active"):
                eq_ok = (not rules.get("equity_above")) or (p.get("est_equity") or 0) >= rules.get("equity_min", 0)
                if eq_ok:
                    alerts.append((now(), "high_score", p["county_id"], p["id"], f"New high-score deal: {p['street'].title()}",
                                   f"Deal score {s}. Est. equity ${p.get('est_equity') or 0:,.0f}.", s))
        c.executemany("""UPDATE parcels SET property_type=?, years_behind=?, est_equity=?, rent_est=?, suggested_offer=?,
                         score=?, score_breakdown=? WHERE id=?""", upd)
        c.executemany("INSERT INTO alerts(ts,type,county_id,parcel_id,title,body,score) VALUES(?,?,?,?,?,?,?)", alerts)


def enrich(client, county, parcel_ids, step_cb=None):
    done = fails = 0
    for i, pid in enumerate(parcel_ids):
        p = db.q1("SELECT id, property_url FROM parcels WHERE id=?", (pid,))
        if not p or not p["property_url"]:
            continue
        try:
            info = client.property(p["property_url"])
            fails = 0
        except Exception as e:
            fails += 1
            if fails >= 5 or (type(e).__name__ == "Blocked" and fails >= 2):
                print(f"{county['name']}: property pages not available from here ({e}); skipping details this run")
                break
            continue
        fields = {k: info.get(k) for k in ("legal_desc", "acres", "owner_full_name", "mail_address", "mail_state", "mail_zip",
                                          "land_use", "land_value", "improvement_value", "appraised_total", "owner_occupied",
                                          "prior_due", "annual_tax", "total_due", "lat", "lng", "cert_year", "beds", "baths_full",
                                          "baths_half", "year_built", "living_area", "style", "condition", "stories", "photo_url")
                  if info.get(k) is not None}
        cur = db.q1("SELECT city, zip FROM parcels WHERE id=?", (pid,))
        cur2 = db.q1("SELECT street, school_district FROM parcels WHERE id=?", (pid,)) or {}
        if info.get("street") and not re.match(r"\d", cur2.get("street") or ""):
            fields["street"] = info["street"]
        if info.get("owner_name"):
            fields["owner_name"] = info["owner_name"]
        if info.get("school_district") and not cur2.get("school_district"):
            fields["school_district"] = info["school_district"]
        if info.get("loc_city") and not (cur or {}).get("city"):
            fields["city"], fields["zip"] = info["loc_city"], info.get("loc_zip") or (cur or {}).get("zip")
        fields["enriched_at"] = now()
        fields["enrich_v"] = ENRICH_V
        sets = ", ".join(f"{k}=?" for k in fields)
        db.run(f"UPDATE parcels SET {sets} WHERE id=?", (*fields.values(), pid))
        done += 1
        if step_cb and i % 10 == 0:
            step_cb(i + 1, len(parcel_ids))
    return done


EXTRA = ("mail_address", "mail_state", "mail_zip", "land_use", "land_value", "improvement_value",
         "appraised_total", "cert_year", "legal_desc", "year_built", "acres", "lat", "lng")


def sync_county(county_id, enrich_limit=700):
    county = db.q1("SELECT * FROM counties WHERE id=?", (county_id,))
    run_id = db.run("INSERT INTO sync_runs(county_id, started, status) VALUES(?,?,?)", (county_id, now(), "running"))
    db.run("UPDATE counties SET sync_status='syncing', sync_error=NULL WHERE id=?", (county_id,))
    STATUS.update(county=county["name"], step="Downloading delinquent list", progress=0)
    try:
        if not county["host"]:
            raise RuntimeError("No website set for this county")
        client = FileClient(county["host"]) if county["host"].split(":")[0] in FILE_PREFIXES else IssgClient(county["host"])
        rows, year = client.all_rows(progress=lambda i, n, name: STATUS.update(step=f"Township {i}/{n}: {name}", progress=int(40 * i / n)))
        if not rows:
            raise RuntimeError("County site returned 0 parcels (format change or list not published)")
        d = today()
        prev_active = {r["id"]: r for r in db.q("SELECT id, owner_name, amount_owed FROM parcels WHERE county_id=? AND is_active=1 AND demo=0", (county_id,))}
        first_sync = not db.q1("SELECT 1 FROM sync_runs WHERE county_id=? AND status='ok'", (county_id,))
        new_ids, seen = [], set()
        AL = "INSERT INTO alerts(ts,type,county_id,parcel_id,title,body) VALUES(?,?,?,?,?,?)"
        have = {r["id"]: r for r in db.q("SELECT id, owner_name, amount_owed, is_active FROM parcels WHERE county_id=?", (county_id,))}
        ins, upd, snap, alerts = [], [], [], []
        for r in rows:
            pid = f"{county_id}:{r['parcel_number']}"
            if pid in seen:
                continue
            seen.add(pid)
            exists = have.get(pid)
            if exists is None:
                ins.append((pid, county_id, r["parcel_number"], r["owner_name"], r["school_district"], r["street"], r["city"],
                            r["state"], r["zip"], r["amount_owed"], r["property_url"], d, d))
                new_ids.append(pid)
                if not first_sync:
                    alerts.append((now(), "new_delinquent", county_id, pid, f"New delinquent: {r['street'].title()}, {r['city'].title()}",
                                   f"${r['amount_owed'] or 0:,.0f} owed. Owner {r['owner_name']}."))
            else:
                if exists["owner_name"] and r["owner_name"] and exists["owner_name"] != r["owner_name"]:
                    alerts.append((now(), "owner_change", county_id, pid, f"Owner change: {r['street'].title()}",
                                   f"{exists['owner_name']} -> {r['owner_name']}"))
                if exists["amount_owed"] and r["amount_owed"] and r["amount_owed"] > exists["amount_owed"] * 1.05:
                    alerts.append((now(), "amount_up", county_id, pid, f"Delinquency grew: {r['street'].title()}",
                                   f"${exists['amount_owed']:,.0f} -> ${r['amount_owed']:,.0f}"))
                upd.append((r["owner_name"], r["amount_owed"], r["property_url"], d, r["street"], r["city"], r["zip"], pid))
            snap.append((pid, d, r["amount_owed"], r["owner_name"]))
        removed = [pid for pid in prev_active if pid not in seen]
        for pid in removed:
            alerts.append((now(), "paid_off", county_id, pid, "Taxes paid / removed from list", pid.split(":", 1)[1]))
        with db.tx() as c:
            c.executemany("""INSERT INTO parcels(id, county_id, parcel_number, owner_name, school_district, street, city, state, zip,
                             amount_owed, property_url, first_seen, last_seen, is_active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)""", ins)
            c.executemany("""UPDATE parcels SET owner_name=?, amount_owed=?, property_url=?, last_seen=?, is_active=1,
                             street=?, city=?, zip=? WHERE id=?""", upd)
            c.executemany("INSERT OR REPLACE INTO snapshots(parcel_id, date, amount, owner_name) VALUES(?,?,?,?)", snap)
            c.executemany("UPDATE parcels SET is_active=0 WHERE id=?", [(pid,) for pid in removed])
            c.executemany(AL, alerts)
            # extra columns some sources give straight from the list (values, mailing address, land use)
            groups = {}
            for r in rows:
                ks = tuple(k for k in EXTRA if r.get(k) not in (None, ""))
                if ks:
                    groups.setdefault(ks, []).append((*[r[k] for k in ks], f"{county_id}:{r['parcel_number']}"))
            for ks, vals in groups.items():
                c.executemany(f"UPDATE parcels SET {', '.join(k + '=?' for k in ks)} WHERE id=?", vals)
            c.execute("UPDATE counties SET tax_year=COALESCE(?, tax_year), delinquent_count=? WHERE id=?", (year, len(rows), county_id))
        if new_ids and first_sync:
            alert("new_delinquent", f"{county['name']}: first sync found {len(new_ids)} delinquent properties",
                  "Scores are ready in Deals.", county_id)
        # enrich new + previously unenriched (cap per run so a big county finishes over a few nights)
        todo = [r["id"] for r in db.q("""SELECT id FROM parcels WHERE county_id=? AND is_active=1
                                         AND (enriched_at IS NULL OR COALESCE(enrich_v,0) < ?) ORDER BY enriched_at IS NOT NULL LIMIT ?""",
                                       (county_id, ENRICH_V, enrich_limit))]
        STATUS.update(step=f"Reading property details (0/{len(todo)})", progress=45)
        enrich(client, county, todo, step_cb=lambda i, n: STATUS.update(step=f"Reading property details ({i}/{n})", progress=45 + int(50 * i / max(n, 1))))
        # map coordinates for sites without a map link (street number needed for a match)
        # only parcels that are new or got an address today (or everything on a first sync / every Sunday), so misses are not retried daily
        recheck = first_sync or dt.date.today().weekday() == 6
        missing = db.q("SELECT id, street, city, state, zip FROM parcels WHERE county_id=? AND is_active=1 AND lat IS NULL AND street GLOB '[0-9]*'"
                       + ("" if recheck else " AND (first_seen=? OR enriched_at >= ?)"), (county_id,) if recheck else (county_id, d, d))
        if missing:
            STATUS.update(step=f"Placing {len(missing)} properties on the map", progress=96)
            found = geocode.batch([(m["id"], m["street"], m["city"], m["state"] or "OH", m["zip"]) for m in missing])
            with db.tx() as c:
                for pid, (lat, lng) in found.items():
                    c.execute("UPDATE parcels SET lat=?, lng=? WHERE id=?", (lat, lng, pid))
        rescore([r["id"] for r in db.q("SELECT id FROM parcels WHERE county_id=?", (county_id,))], quiet=first_sync)
        db.run("""UPDATE counties SET lat=(SELECT AVG(lat) FROM parcels WHERE county_id=? AND lat IS NOT NULL),
                  lng=(SELECT AVG(lng) FROM parcels WHERE county_id=? AND lng IS NOT NULL) WHERE id=? AND lat IS NULL""",
               (county_id, county_id, county_id))
        db.run("UPDATE counties SET sync_status='synced', last_sync=?, sync_error=NULL WHERE id=?", (now(), county_id))
        db.run("UPDATE sync_runs SET finished=?, status='ok', found=?, new_count=?, removed_count=? WHERE id=?",
               (now(), len(rows), len(new_ids), len(removed), run_id))
        return {"ok": True, "found": len(rows), "new": len(new_ids), "removed": len(removed)}
    except Exception as e:
        err = str(e)[:300]
        traceback.print_exc()
        db.run("UPDATE counties SET sync_status='error', sync_error=? WHERE id=?", (err, county_id))
        db.run("UPDATE sync_runs SET finished=?, status='error', error=? WHERE id=?", (now(), err, run_id))
        return {"ok": False, "error": err}


def sync_all(ids=None):
    if not _lock.acquire(blocking=False):
        return {"ok": False, "error": "A sync is already running"}
    try:
        STATUS.update(running=True)
        res = {}
        counties = db.q("SELECT id FROM counties WHERE enabled=1 AND demo=0" + (f" AND id IN ({','.join('?' * len(ids))})" if ids else ""), tuple(ids or ()))
        for c in counties:
            res[c["id"]] = sync_county(c["id"])
        check_auctions()
        send_instant_alerts()
        try:
            STATUS.update(county="Owner contacts", step="Finding owner phones and emails", progress=97)
            res["contacts"] = contacts.run_batch(lambda i, n: STATUS.update(step=f"Finding owner phones and emails ({i}/{n})"))
        except Exception:
            traceback.print_exc()
        return {"ok": True, "results": res}
    finally:
        STATUS.update(running=False, county=None, step="", progress=0)
        _lock.release()


def sync_in_background(ids=None):
    threading.Thread(target=sync_all, args=(ids,), daemon=True).start()


def check_auctions():
    rules = db.get_setting("alert_rules")
    if not rules.get("auction_within"):
        return
    days = rules.get("auction_days", 30)
    for c in db.q("SELECT * FROM counties WHERE tax_sale_date IS NOT NULL AND tax_sale_date != ''"):
        try:
            when = dt.date.fromisoformat(c["tax_sale_date"])
        except ValueError:
            continue
        left = (when - dt.date.today()).days
        if 0 <= left <= days and not db.q1("SELECT 1 FROM alerts WHERE type='auction' AND county_id=? AND body LIKE ?", (c["id"], f"%{c['tax_sale_date']}%")):
            alert("auction", f"Tax sale scheduled {when:%b %d}, {c['name']}", f"Auction date {c['tax_sale_date']} ({left} days left)", c["id"])


def send_instant_alerts():
    """High-score and new-delinquent alerts go out right away on the switched-on channels."""
    channels = db.get_setting("channels")
    rows = db.q("SELECT * FROM alerts WHERE sent=0 AND type IN ('high_score','auction') ORDER BY id LIMIT 20")
    if not rows or not any(channels.values()):
        return
    body = "\n".join(f"- {a['title']} ({a['body']})" for a in rows)
    notify.deliver(channels, f"EstateHawk: {len(rows)} new alerts", body)
    db.run(f"UPDATE alerts SET sent=1 WHERE id IN ({','.join(str(a['id']) for a in rows)})")


def digest_text():
    since = (dt.datetime.now() - dt.timedelta(days=1)).isoformat(sep=" ")
    new = db.q1("SELECT COUNT(*) n FROM parcels WHERE first_seen>=? AND demo=0", (since[:10],))["n"]
    top = db.q("SELECT street, city, score, total_due, amount_owed FROM parcels WHERE is_active=1 AND score IS NOT NULL ORDER BY score DESC LIMIT 5")
    lines = [f"New delinquent properties since yesterday: {new}", "", "Top deals right now:"]
    for t in top:
        lines.append(f"- {(t['street'] or '').title()}, {(t['city'] or '').title()}: score {t['score']:.0f}, ${(t['total_due'] or t['amount_owed'] or 0):,.0f} owed")
    return "EstateHawk daily digest", "\n".join(lines)


def synced_today():
    r = db.q1("SELECT MAX(started) t FROM sync_runs WHERE status='ok'")
    return bool(r and r["t"] and r["t"][:10] == today())


def scheduler_loop():
    ran = {"sync": None, "digest": None}
    time.sleep(20)  # let the app finish starting
    while True:
        try:
            hm = dt.datetime.now().strftime("%H:%M")
            d = today()
            # daily sync at the set time; if the computer was off/asleep then, catch up as soon as the app is running
            if ran["sync"] != d and hm >= db.get_setting("sync_time") and not synced_today() \
                    and db.q1("SELECT 1 FROM counties WHERE enabled=1 AND demo=0"):
                ran["sync"] = d
                sync_all()
            dg = db.get_setting("digest")
            if dg.get("enabled") and hm == dg.get("time") and ran["digest"] != d:
                ran["digest"] = d
                s, b = digest_text()
                notify.deliver(db.get_setting("channels"), s, b)
        except Exception:
            traceback.print_exc()
        time.sleep(30)


def start_scheduler():
    threading.Thread(target=scheduler_loop, daemon=True).start()
