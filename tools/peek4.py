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
for u in ["https://taxsales.lgbs.com/api/", "https://taxsales.lgbs.com/api/faq/?search=TX", "https://taxsales.lgbs.com/"]:
    r = g(u); print("P", u, r.status_code, r.headers.get("content-type"), len(r.text)); print("B", r.text[:1500].replace("\n", " "))
home = g("https://taxsales.lgbs.com/").text
for s in re.findall(r"src=[\"']([^\"']+\.js[^\"']*)", home)[:8]:
    js = g(s if s.startswith("http") else "https://taxsales.lgbs.com" + s).text
    eps = sorted(set(re.findall(r"[\"'`](/api/[a-zA-Z0-9_/\-]+)", js)))
    print("JS", s, len(js), eps[:60])
