"""Fetch pages and print the file / delinquent links on them (for finding where a county keeps its list)."""
import re, sys
from urllib.parse import urljoin
import requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
for u in open(sys.argv[1]).read().split():
    try:
        r = requests.get(u, headers=UA, timeout=25)
    except requests.RequestException as e:
        print("P", u, "ERR", type(e).__name__); continue
    t = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I)
    print("P", u, r.status_code, len(r.text), (t.group(1).strip()[:80] if t else ""))
    seen = set()
    for h, txt in re.findall(r"href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", r.text, re.S | re.I):
        full = urljoin(r.url, h)
        txt = re.sub(r"<[^>]+>|\s+", " ", txt).strip()[:70]
        if full in seen:
            continue
        if re.search(r"\.(pdf|xlsx?|csv|zip|txt)(\?|$)|delinq|export|download", full + " " + txt, re.I):
            seen.add(full); print("   L", full[:200], "|", txt)
    if "FORM" in sys.argv:
        for f in re.findall(r"<form[^>]*>", r.text, re.I)[:3]:
            print("   F", f[:200])
