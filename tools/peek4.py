import requests, io, zipfile
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
r = requests.get("https://go.mcohio.org/applications/treasurer/search/data/Delq/Delq_20261031.zip", headers=UA, timeout=120)
print("F", r.status_code, len(r.content))
z = zipfile.ZipFile(io.BytesIO(r.content))
for n in z.namelist():
    d = z.read(n); print("Z", n, len(d))
    lines = d.decode("latin1").splitlines()
    print("ZN", len(lines))
    for l in lines[:4]: print("ZD", repr(l[:1200]))
