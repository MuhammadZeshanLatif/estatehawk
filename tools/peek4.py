import requests, json, re
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "Accept": "application/json, text/html"}
g = lambda u, **k: requests.get(u, headers=UA, timeout=60, **k)
for u in ["https://taxsales.lgbs.com/api/", "https://taxsales.lgbs.com/api/faq/?search=TX", "https://taxsales.lgbs.com/"]:
    r = g(u); print("P", u, r.status_code, r.headers.get("content-type"), len(r.text)); print("B", r.text[:1500].replace("\n", " "))
home = g("https://taxsales.lgbs.com/").text
for s in re.findall(r"src=[\"']([^\"']+\.js[^\"']*)", home)[:8]:
    js = g(s if s.startswith("http") else "https://taxsales.lgbs.com" + s).text
    eps = sorted(set(re.findall(r"[\"'`](/api/[a-zA-Z0-9_/\-]+)", js)))
    print("JS", s, len(js), eps[:60])
