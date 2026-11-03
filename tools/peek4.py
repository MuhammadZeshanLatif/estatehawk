import requests, io, re, html, zipfile
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
g = lambda u, **k: requests.get(u, headers=UA, timeout=300, **k)
def links(u, pat=r"."):
    r = g(u); print("P", u, r.status_code, len(r.text)); out = []
    for h, t in re.findall(r"href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", r.text, re.S | re.I):
        t = re.sub(r"<[^>]+>|\s+", " ", t).strip()
        if re.search(pat, h + " " + t, re.I):
            print("   L", h[:160], "|", html.unescape(t)[:70]); out.append(h)
    sz = re.findall(r"(\d+/\d+/\d+\s+\d+:\d+ [AP]M)\s+(\d+)\s+<A HREF=\"([^\"]+)\"", r.text, re.I)
    for d, s, h in sz: print("   S", d, s, h)
    return out
links("https://apps.franklincountyauditor.com/Outside_User_Files/2026/2026-10-15%20Tax%20Accounting/")
links("https://www.cuyahogacounty.gov/fiscal-officer/departments/real-property/delinquent-publication", r"delinq|download|csv|xlsx|zip|pdf|txt")
