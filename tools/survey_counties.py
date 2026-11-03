"""Survey every Ohio county auditor site: which software it runs and where its delinquent tax list lives.
Run on GitHub Actions (needs open internet). Writes survey_result.json"""
import json, re, string, concurrent.futures as cf
from urllib.parse import urljoin
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
SIGS = {"issg": r"issg", "beacon": r"beacon\.schneidercorp|schneidercorp", "devnet": r"devnetwedge|wedge\b|devnet",
        "tyler": r"iasworld|tylertech|tyler technologies|publicaccess", "aumentum": r"aumentum|thomson reuters",
        "avenu": r"avenu", "gis_arcgis": r"arcgis", "qpublic": r"qpublic", "taxsys": r"taxsys|grant street",
        "appraisal": r"appraisal research|arc-?gis", "pdf_list": r"delinquen[^\"'<>]{0,80}\.pdf"}


def get(url, **kw):
    try:
        r = requests.get(url, headers=UA, timeout=25, allow_redirects=True, **kw)
        return r
    except requests.RequestException as e:
        return e


def directory():
    out = {}
    for ch in string.ascii_uppercase:
        r = get(f"https://caao.org/auditors-directory/char/{ch}/")
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        html = r.text
        for m in re.finditer(r"([A-Z][A-Za-z ]+?) County(.{0,3000}?)(?=[A-Z][A-Za-z ]+? County|$)", html, re.S):
            pass
        # county detail pages
        for slug in set(re.findall(r"/auditors-directory/name/([a-z\-]+-county)/", html)):
            out[slug] = None
    for slug in list(out):
        r = get(f"https://caao.org/auditors-directory/name/{slug}/")
        if isinstance(r, Exception):
            continue
        links = [u for u in re.findall(r"href=[\"'](https?://[^\"']+|www\.[^\"']+)", r.text)
                 if "caao.org" not in u and not re.search(r"facebook|twitter|google|linkedin|instagram|youtube|wp-|gravatar|w\.org", u)]
        out[slug] = links
    return out


def survey(slug, links):
    name = slug.replace("-county", "").replace("-", " ").title() + " County"
    res = {"county": name, "sites": []}
    for u in (links or [])[:3]:
        if not u.startswith("http"):
            u = "http://" + u
        r = get(u)
        if isinstance(r, Exception):
            res["sites"].append({"url": u, "error": type(r).__name__})
            continue
        html = r.text[:400000]
        low = html.lower()
        sig = [k for k, p in SIGS.items() if re.search(p, low)]
        delinq = sorted({urljoin(r.url, h) for h in re.findall(r"href=[\"']([^\"']+)[\"']", html) if re.search(r"delinq", h, re.I)})[:15]
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        res["sites"].append({"url": u, "final": r.url, "status": r.status_code, "title": (title.group(1).strip()[:100] if title else ""),
                             "platform": sig, "delinquent_links": delinq})
    return res


if __name__ == "__main__":
    d = directory()
    print(len(d), "counties in directory")
    with cf.ThreadPoolExecutor(12) as ex:
        out = list(ex.map(lambda kv: survey(*kv), sorted(d.items())))
    json.dump({"directory": d, "survey": out}, open("survey_result.json", "w"), indent=1)
    for o in out:
        s = o["sites"][0] if o["sites"] else {}
        print(f"{o['county']:22} {s.get('final', s.get('url', '-'))[:60]:60} {','.join(s.get('platform', []))[:40]:40} dl={len(s.get('delinquent_links', []))}")
