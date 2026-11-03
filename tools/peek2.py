"""Print delinquent-related links, JS snippets and text for county pages."""
import re, sys, html
from urllib.parse import urljoin
import requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
for u in open(sys.argv[1]).read().split():
    try:
        r = requests.get(u, headers=UA, timeout=30)
    except requests.RequestException as e:
        print("P", u, "ERR", type(e).__name__); continue
    t = r.text
    print("P", u, r.status_code, len(t))
    for h, tx in re.findall(r"href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", t, re.S | re.I):
        tx = re.sub(r"<[^>]+>|\s+", " ", tx).strip()
        if re.search(r"delinq|forfeit|\.(pdf|xlsx?|csv|zip|txt)\b|download|unpaid|tax.?list", h + " " + tx, re.I) and not re.search(r"facebook|twitter|linkedin|reddit", h):
            print("   L", urljoin(r.url, h)[:180], "|", html.unescape(tx)[:60])
    for m in re.finditer(r"function fdpopup.{0,600}", t, re.S):
        print("   JS", re.sub(r"\s+", " ", m.group(0))[:600])
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)))
    if "TEXT" in sys.argv:
        print("   X", txt[:1500])
    for m in list(re.finditer(r".{0,120}delinquent.{0,160}", txt, re.I))[:4]:
        print("   D", m.group(0))
