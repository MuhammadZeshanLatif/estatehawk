import re, sys, requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
for u in sys.argv[1:]:
    t = requests.get(u, headers=UA, timeout=30).text
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", body))
    print("H", u); print("X", txt[:3500])
    for m in re.finditer(r".{0,200}(Address|Situs|Location).{0,200}", body, re.I):
        print("A", re.sub(r"\s+", " ", m.group(0))[:400])
