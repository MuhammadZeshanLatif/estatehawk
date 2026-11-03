"""Second pass: follow each auditor site's property-search links, fingerprint those hosts, try ISSG /DelinquentList.
Prints one JSON line per county (read from the Actions log)."""
import json, re, concurrent.futures as cf
from urllib.parse import urljoin, urlparse
import requests
from survey_counties import directory, get, SIGS

KEY = re.compile(r"realestate|real-estate|property|parcel|search|issg|beacon|schneider|publicaccess|iview|wedge|delinq|tax|treasurer|gis|cama|appraisal", re.I)


def links(html, base):
    return {urljoin(base, h) for h in re.findall(r"href=[\"']([^\"'#]+)[\"']", html)}


def fp(html):
    low = html.lower()
    return [k for k, p in SIGS.items() if re.search(p, low)]


def deep(slug, home):
    name = slug.replace("-county", "").replace("-", " ").title() + " County"
    out = {"county": name, "home": None, "hosts": {}, "delinquent": [], "issg_list": []}
    for u in (home or [])[:2]:
        u = u if u.startswith("http") else "http://" + u
        r = get(u)
        if isinstance(r, Exception) or r.status_code >= 400:
            continue
        out["home"] = r.url
        L = links(r.text, r.url)
        homehost = urlparse(r.url).netloc
        cand = [l for l in L if KEY.search(l)]
        out["delinquent"] += [l for l in L if re.search(r"delinq|forfeit|tax.?sale|sheriff", l, re.I)]
        hosts = {}
        for l in cand:
            h = urlparse(l).netloc
            if h and h != homehost and not re.search(r"facebook|twitter|google|ohio\.gov$|tax\.ohio|youtube|linkedin|instagram", h):
                hosts.setdefault(h, l)
        for h, l in list(hosts.items())[:8]:
            rr = get(f"https://{h}/")
            info = {"link": l}
            if not isinstance(rr, Exception):
                info.update(final=rr.url, status=rr.status_code, platform=fp(rr.text[:300000]))
                for dl in links(rr.text, rr.url):
                    if re.search(r"delinq", dl, re.I):
                        out["delinquent"].append(dl)
            d = get(f"https://{h}/DelinquentList")
            if not isinstance(d, Exception) and d.status_code == 200 and re.search(r"delinquentlist/polsub", d.text, re.I):
                out["issg_list"].append(h)
            out["hosts"][h] = info
        break
    out["delinquent"] = sorted(set(out["delinquent"]))[:20]
    return out


if __name__ == "__main__":
    d = directory()
    with cf.ThreadPoolExecutor(12) as ex:
        for o in ex.map(lambda kv: deep(*kv), sorted(d.items())):
            print("J " + json.dumps(o))
