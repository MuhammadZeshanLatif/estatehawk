import sys, traceback
sys.path.insert(0, ".")
from app.scraper.issg import IssgClient
for host in sys.argv[1:]:
    c = IssgClient(host, delay=0.2)
    subs = c.polsubs()
    print("T", host, "polsubs", len(subs), subs[:1])
    rows, y = c.fetch_rows(subs[0][0], subs[0][2])
    print("T rows", len(rows), rows[:1])
    u = rows[0]["property_url"]
    print("T url", u)
    try:
        r = c.s.get(u, timeout=40, allow_redirects=False)
        print("T status", r.status_code, r.headers.get("location"), len(r.text))
        print("T prop", c.property(u))
    except Exception as e:
        traceback.print_exc()
