"""Fictional demo data so every screen can be seen before the first real county sync.
All names/addresses here are made up. Demo parcels have demo=1 and can be removed from Settings."""
import datetime as dt, json, random

from . import db, jobs
from .counties import KNOWN_ISSG

FIRST = ["James", "Mary", "Robert", "Linda", "Michael", "Patricia", "David", "Barbara", "William", "Susan", "Richard", "Karen",
         "Thomas", "Nancy", "Daniel", "Lisa", "Mark", "Sandra", "Steven", "Donna", "Paul", "Carol", "Kevin", "Sharon", "Brian", "Diane"]
LAST = ["Miller", "Harris", "Cooper", "White", "Carter", "Green", "Evans", "Moore", "Wright", "Hale", "Jenkins", "Clark", "Phillips",
        "Davis", "Martinez", "Anderson", "Taylor", "Thomas", "Walker", "Young", "King", "Scott", "Baker", "Adams", "Nelson", "Hill"]
STREETS = ["Maple St", "E Perkins Ave", "Cleveland Rd", "Madison St", "Harbor View Dr", "Venice Rd", "Washington St", "Jackson St",
           "Oak St", "Elm Ave", "Wheeling Ave", "Steubenville Ave", "Main St", "Church St", "Park Ave", "Lincoln Way", "Spring St",
           "Columbus Ave", "Tiffin Ave", "Huron Ave", "Franklin Blvd", "Decatur St", "Campbell St", "Perry St", "Chestnut St"]
TOWNS = {
    "Guernsey County": [("Cambridge", "43725"), ("Byesville", "43723"), ("Lore City", "43755"), ("Quaker City", "43773")],
    "Logan County": [("Bellefontaine", "43311"), ("Russells Point", "43348"), ("West Liberty", "43357")],
    "Geauga County": [("Chardon", "44024"), ("Middlefield", "44062"), ("Burton", "44021")],
    "Tuscarawas County": [("New Philadelphia", "44663"), ("Dover", "44622"), ("Uhrichsville", "44683"), ("Newcomerstown", "43832")],
}
OUT_STATES = ["FL", "TX", "AZ", "NC", "CA", "GA", "PA", "MI", "NV"]


def seed(per_county=(55, 95)):
    rnd = random.Random(7)
    today = dt.date.today()
    clear()
    for k in KNOWN_ISSG[:4]:
        c = db.q1("SELECT id FROM counties WHERE name=?", (k["name"],))
        cid = c["id"] if c else db.run("INSERT INTO counties(name,state,host,lat,lng,tax_year) VALUES(?,?,?,?,?,?)",
                                         (k["name"], k["state"], k["host"], k["lat"], k["lng"], today.year - 1))
        n = rnd.randint(*per_county)
        towns = TOWNS[k["name"]]
        for i in range(n):
            town, zp = rnd.choice(towns)
            fn, ln = rnd.choice(FIRST), rnd.choice(LAST)
            owner = f"{ln.upper()} {fn.upper()}" + (f" & {rnd.choice(FIRST).upper()}" if rnd.random() < .35 else "")
            land_use = rnd.choices(["510-SINGLE FAMILY DWELLING", "520-TWO FAMILY DWELLING", "500-RESIDENTIAL VACANT LAND",
                                    "400-COMMERCIAL VACANT LAND", "100-AGRICULTURAL VACANT LAND"], [70, 8, 10, 4, 8])[0]
            land = rnd.randint(6, 30) * 1000
            imp = 0 if "VACANT" in land_use else rnd.randint(35, 230) * 1000
            total = land + imp
            annual = round(total * 0.35 * rnd.uniform(0.045, 0.07), 2)
            years = rnd.choices([0, 1, 2, 3, 4, 5], [30, 25, 18, 12, 9, 6])[0]
            prior = round(annual * years * rnd.uniform(1.05, 1.2), 2)
            due = round(prior + annual * rnd.uniform(.5, 1.0), 2)
            out = rnd.random() < .22
            occ = 0 if out or rnd.random() < .35 else 1
            ms = rnd.choice(OUT_STATES) if out else "OH"
            first_seen = today - dt.timedelta(days=min(int(rnd.expovariate(1 / 40)), 120))
            lat = k["lat"] + rnd.uniform(-.13, .13)
            lng = k["lng"] + rnd.uniform(-.17, .17)
            pn = f"{rnd.randint(1, 45):02d}-{rnd.randint(1000, 99999):07d}.000"
            pid = f"demo:{cid}:{pn}"
            db.run("""INSERT OR REPLACE INTO parcels(id,county_id,parcel_number,owner_name,owner_full_name,school_district,street,city,state,zip,
                      amount_owed,property_url,first_seen,last_seen,is_active,enriched_at,legal_desc,acres,mail_address,mail_state,mail_zip,
                      land_use,land_value,improvement_value,appraised_total,owner_occupied,prior_due,annual_tax,total_due,lat,lng,demo)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                   (pid, cid, pn, owner, f"{fn.upper()} {ln.upper()}", f"{town.upper()} CSD",
                    f"{rnd.randint(100, 3999)} {rnd.choice(STREETS)}".upper(), town.upper(), "OH", zp, due, "",
                    first_seen.isoformat(), today.isoformat(), 1 if rnd.random() > .04 else 0, jobs.now(),
                    f"LOT {rnd.randint(1, 300)} DEMO ADDN", round(rnd.uniform(.12, 1.2), 3),
                    f"{rnd.randint(10, 9999)} DEMO RD, SOMEWHERE {ms} {rnd.randint(10000, 99999)}", ms,
                    str(rnd.randint(10000, 99999)) if out or not occ else zp, land_use, land, imp, total, occ, prior, annual, due, lat, lng))
            # 30 days of snapshot history
            for dd in range(0, (today - first_seen).days + 1, 7):
                d = first_seen + dt.timedelta(days=dd)
                db.run("INSERT OR REPLACE INTO snapshots(parcel_id,date,amount,owner_name) VALUES(?,?,?,?)",
                       (pid, d.isoformat(), round(due * (0.9 + 0.1 * dd / 120), 2), owner))
        db.run("UPDATE counties SET delinquent_count=(SELECT COUNT(*) FROM parcels WHERE county_id=? AND is_active=1), "
               "last_sync=?, sync_status='synced' WHERE id=?", (cid, (dt.datetime.now() - dt.timedelta(hours=rnd.randint(2, 9))).isoformat(sep=" ")[:19], cid))
    jobs.rescore(quiet=True)
    _seed_workflow(rnd)
    db.set_setting("demo", True)


def _seed_workflow(rnd):
    now = dt.datetime.now()
    top = db.q("SELECT * FROM parcels WHERE demo=1 AND is_active=1 AND property_type IN ('Single family','Residential') ORDER BY score DESC LIMIT 40")
    stages = ["new"] * 12 + ["contacted"] * 9 + ["replied"] * 5 + ["negotiating"] * 4 + ["under_contract"] * 2 + ["closed"] * 3
    for p, st in zip(top, stages):
        ts = (now - dt.timedelta(days=rnd.randint(0, 20), hours=rnd.randint(0, 20))).isoformat(sep=" ")[:19]
        fee = rnd.choice([8500, 11000, 12500, 14000, 18500]) if st == "closed" else None
        db.run("INSERT OR REPLACE INTO pipeline(parcel_id,stage,updated_at,fee,closed_at) VALUES(?,?,?,?,?)",
               (p["id"], st, ts, fee, ts[:10] if st == "closed" else None))
        if st != "new":
            db.run("INSERT INTO activities(parcel_id,ts,kind,text,author) VALUES(?,?,?,?,?)",
                   (p["id"], ts, rnd.choice(["email", "call", "sms", "letter"]), "First contact sent", "Ashhad"))
        if st in ("replied", "negotiating", "under_contract", "closed"):
            db.run("INSERT INTO activities(parcel_id,ts,kind,text,author) VALUES(?,?,?,?,?)",
                   (p["id"], ts, "reply", rnd.choice(["Can you send more details about the offer?", "I'm interested. What's your offer?",
                                                       "Let's discuss, I'm available next week.", "Can you make a higher offer?"]),
                    p["owner_name"].title()))
    for p in top[12:16]:
        db.run("INSERT INTO tasks(parcel_id,due,text,kind) VALUES(?,?,?,?)",
               (p["id"], now.date().isoformat(), rnd.choice(["Call back owner", "Send follow-up email", "Check reply", "Mail offer letter"]),
                rnd.choice(["call", "email", "sms"])))
    types = [("new_delinquent", "New delinquent: {s}", "${d:,.0f} owed"), ("high_score", "New high-score deal: {s}", "Deal score {sc:.0f}"),
             ("owner_change", "Owner change: {s}", "New owner recorded (quit claim deed)"), ("amount_up", "Delinquency grew: {s}", "Now ${d:,.0f} owed")]
    allp = db.q("SELECT * FROM parcels WHERE demo=1 AND is_active=1 ORDER BY RANDOM() LIMIT 24")
    hi = db.q("SELECT * FROM parcels WHERE demo=1 AND is_active=1 AND score>=85 ORDER BY RANDOM() LIMIT 6")
    for i, p in enumerate(allp):
        t, ti, bo = types[i % len(types)]
        if t == "high_score":
            if not hi:
                continue
            p = hi.pop()
        ts = (now - dt.timedelta(hours=i * 3 + rnd.randint(0, 2))).isoformat(sep=" ")[:19]
        db.run("INSERT INTO alerts(ts,type,county_id,parcel_id,title,body,score,read,sent) VALUES(?,?,?,?,?,?,?,?,1)",
               (ts, t, p["county_id"], p["id"], ti.format(s=f"{p['street'].title()}, {p['city'].title()}"),
                bo.format(d=p["total_due"] or 0, sc=p["score"] or 0), p["score"], 1 if i > 8 else 0))
    c = db.q1("SELECT id FROM counties ORDER BY id LIMIT 1")
    sale = (dt.date.today() + dt.timedelta(days=14)).isoformat()
    db.run("UPDATE counties SET tax_sale_date=? WHERE id=?", (sale, c["id"]))
    jobs.check_auctions()


def clear():
    ids = [r["id"] for r in db.q("SELECT id FROM parcels WHERE demo=1")]
    with db.tx() as c:
        for t, col in (("snapshots", "parcel_id"), ("alerts", "parcel_id"), ("pipeline", "parcel_id"), ("activities", "parcel_id"),
                       ("tasks", "parcel_id"), ("offers", "parcel_id")):
            c.execute(f"DELETE FROM {t} WHERE {col} LIKE 'demo:%'")
        c.execute("DELETE FROM parcels WHERE demo=1")
        c.execute("DELETE FROM alerts WHERE type='auction'")
    db.set_setting("demo", False)
    return len(ids)


if __name__ == "__main__":
    seed()
    print("demo data loaded")
