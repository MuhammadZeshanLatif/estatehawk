import requests, json
UA = {"User-Agent": "Mozilla/5.0"}
g = lambda u, **k: requests.get(u, headers=UA, timeout=120, **k)
for svc in ["https://gis.cuyahogacounty.gov/server/rest/services/MyPlace/MyPLACE_Tax_Parcels/MapServer",
            "https://gis.cuyahogacounty.gov/server/rest/services/Open_Data_Parcels/MapServer"]:
    j = g(svc + "?f=json").json()
    print("S", svc, [(l["id"], l["name"]) for l in j.get("layers", [])], [(t["id"], t["name"]) for t in j.get("tables", [])])
    for l in j.get("layers", [])[:3] + j.get("tables", [])[:3]:
        lj = g(f"{svc}/{l['id']}?f=json").json()
        print("F", l["name"], [f["name"] for f in lj.get("fields") or []])
        q = g(f"{svc}/{l['id']}/query", params={"where": "1=1", "outFields": "*", "returnGeometry": "false", "resultRecordCount": 2, "f": "json"}).json()
        print("R", json.dumps(q.get("features", [])[:1])[:1500], q.get("error"))
