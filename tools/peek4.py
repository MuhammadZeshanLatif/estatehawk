import requests, json, re, ssl, socket, certifi, tempfile
from cryptography import x509
from cryptography.x509.oid import AuthorityInformationAccessOID
from cryptography.hazmat.primitives.serialization import Encoding
# server sends no intermediate: fetch it from the certificate's AIA "CA Issuers" URL (what browsers do), keep verification on
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
with socket.create_connection(("taxsales.lgbs.com", 443)) as sk, ctx.wrap_socket(sk, server_hostname="taxsales.lgbs.com") as ss:
    leaf = x509.load_der_x509_certificate(ss.getpeercert(True))
aia = leaf.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
url = [d.access_location.value for d in aia if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS][0]
raw = requests.get(url, timeout=30).content
try: inter = x509.load_der_x509_certificate(raw)
except Exception: inter = x509.load_pem_x509_certificate(raw)
bundle = tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False)
bundle.write(open(certifi.where(), "rb").read() + b"\n" + inter.public_bytes(Encoding.PEM)); bundle.close()
print("CERT intermediate from", url)
VERIFY = bundle.name
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "Accept": "application/json, text/html"}
g = lambda u, **k: requests.get(u, headers=UA, timeout=60, verify=VERIFY, **k)
from collections import Counter
r = g("https://taxsales.lgbs.com/api/property_sales/?limit=3").json()
print("COUNT", r.get("count")); print("KEYS", list(r.keys()))
for x in r.get("results", [])[:2]: print("ROW", json.dumps(x)[:2500])
c = g("https://taxsales.lgbs.com/api/sale_counties/?limit=500").json()
items = c.get("results", c) if isinstance(c, dict) else c
print("SC", (c.get("count") if isinstance(c, dict) else len(c)), json.dumps(items[:3])[:800])
states = Counter()
for it in items: states[(it.get("state") or it.get("state_abbr") or "?")] += 1
print("STATES", states.most_common())
