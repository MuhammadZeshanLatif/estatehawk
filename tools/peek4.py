import re, html, requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
g = lambda u, **k: requests.get(u, headers=UA, timeout=60, **k)
t = g("https://go.mcohio.org/applications/treasurer/search/fdpopup.cfm?dtype=DQ").text
print("M", re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S))[:2500])
for h in re.findall(r"href=[\"']([^\"']+)", t)[:40]: print("ML", h)
for mode in ("", "&mode=owner"):
    x = g("https://propertyaccess.summitoh.net/Datalets/Datalet.aspx?sIndex=0&idx=1&UseSearch=no&pin=6800002&jur=077&taxyr=2025&LMparent=20" + mode).text
    b = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " | ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", x, flags=re.S))))
    i = b.find("Basic Information"); print("SU", mode, b[i:i+2500])
