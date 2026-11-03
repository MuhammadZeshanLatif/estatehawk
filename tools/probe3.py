"""Try known delinquent-list URL patterns on every host found for each county. Prints JSON lines 'J {...}'."""
import json, re, concurrent.futures as cf
import requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
HOSTS = json.load(open("county_hosts.json"))


def g(u):
    try:
        return requests.get(u, headers=UA, timeout=20, allow_redirects=True)
    except requests.RequestException:
        return None


def county(name):
    s = name.lower().replace(" county", "").replace(" ", "")
    hosts = set(HOSTS.get(name, []))
    hosts |= {f"{s}countytreasurer.org", f"www.{s}countytreasurer.org", f"treasurer.co.{s}.oh.us", f"{s}countyauditor.org",
              f"www.{s}countyauditor.org", f"realestate.{s}countyauditor.org", f"{s}-auditor-public.issg.io",
              f"{s}-treasurer-public.issg.io", f"realestate.co.{s}.oh.us", f"auditor.co.{s}.oh.us"}
    res = {"county": name, "issg": [], "pan": [], "other": []}
    for h in sorted(hosts):
        r = g(f"https://{h}/DelinquentList")
        if r is not None and r.status_code == 200 and re.search(r"delinquentlist/polsub", r.text, re.I):
            res["issg"].append(h)
    for v in (f"oh-{s}-auditor", f"oh-{s}-treasurer"):
        r = g(f"https://{v}.publicaccessnow.com/DelinquentOwnerSearch.aspx")
        if r is not None and r.status_code == 200 and "delinquent" in r.text.lower():
            res["pan"].append(r.url)
    return res


if __name__ == "__main__":
    with cf.ThreadPoolExecutor(16) as ex:
        for o in ex.map(county, sorted(HOSTS)):
            print("J " + json.dumps(o))
