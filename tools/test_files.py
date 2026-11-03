import sys, json
sys.path.insert(0, ".")
from app.scraper.files import FileClient
for key in sys.argv[1:]:
    c = FileClient("file:" + key)
    try:
        rows, year = c.all_rows()
    except Exception as e:
        print("T", key, "ERROR", e); continue
    print("T", key, len(rows), "rows, year", year)
    for r in rows[:3]:
        print("T   ", json.dumps(r)[:300])
    with_url = [r for r in rows if r.get("property_url")][:3]
    for r in with_url:
        print("T   P", json.dumps(c.property(r["property_url"]))[:500])
