import requests, io, re, html
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
g = lambda u, **k: requests.get(u, headers=UA, timeout=300, **k)
def links(u, pat=r"."):
    try:
        r = g(u)
    except Exception as e:
        print("P", u, "ERR", e); return
    print("P", u, r.status_code, len(r.text))
    for h, t in re.findall(r"href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", r.text, re.S | re.I):
        t = re.sub(r"<[^>]+>|\s+", " ", t).strip()
        if re.search(pat, h + " " + t, re.I):
            print("   L", h[:160], "|", html.unescape(t)[:70])
links("https://apps.franklincountyauditor.com/Outside_User_Files/")
links("https://apps.franklincountyauditor.com/Outside_User_Files/2026/")
links("https://treasurer.franklincountyohio.gov/Delinquent-Taxes", r"delinq|list|download|xlsx|csv|pdf")
links("https://fiscalofficer.cuyahogacounty.gov/en-US/real-property-tax-data.aspx", r"delinq|download|csv|xlsx|zip|pdf")
links("https://www.cuyahogacounty.gov/fiscal-officer/departments/real-property/tax-data", r"delinq|download|csv|xlsx|zip|pdf")
links("https://data-cuyahoga.opendata.arcgis.com/search?q=delinquent")
links("https://co.lucas.oh.us/2296/Delinquent-Tax-List", r"delinq|xlsx|csv|pdf")
links("https://www.lucascountytreasurer.org/", r"delinq|xlsx|csv|pdf|list")
import py7zr
r = g("https://webapps.lakecountyohio.gov/PRDownload/Lake_RealCurrentData.7z")
print("Z", r.status_code, len(r.content))
with py7zr.SevenZipFile(io.BytesIO(r.content)) as z:
    names = z.getnames(); print("ZN", names[:30])
    data = z.readall()
    for n, b in list(data.items())[:12]:
        raw = b.read(800)
        print("ZF", n, repr(raw[:800].decode("latin1")))
