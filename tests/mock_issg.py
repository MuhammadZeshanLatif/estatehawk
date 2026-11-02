"""A tiny fake ISSG county site for testing the scraper end to end (fictional data).
Run: python tests/mock_issg.py 8799   then add a county with host http://localhost:8799"""
import os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(__file__)
PROP = open(os.path.join(HERE, "fixtures", "property.html")).read()
DAY = int(os.environ.get("MOCK_DAY", "1"))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8799


def rows(polsub):
    base = [("01-0000999.000", "DOE JOHN   JANE", "412 MAPLE ST", "CAMBRIDGE OH 43725", "4438.50"),
            ("01-0000777.000", "ROE RICHARD", "18 OAK AVE", "CAMBRIDGE OH 43725", "1210.00")]
    other = [("02-0000123.000", "SMITH MARY", "CABIN HILL RD", "NEW CONCORD OH 43762", "73.33")]
    if DAY >= 2:
        other.append(("02-0000555.000", "NEWMAN NED", "77 RIVER RD", "NEW CONCORD OH 43762", "2900.00"))
        base = base[:1]  # ROE paid off
    data = base if polsub == "CAMBRIDGE TWP" else other
    out = ["Property Number,Owner Name,School District,Location Address,Amount,View Property"]
    for pn, own, st, city, amt in data:
        out.append(f'{pn},{own},CAMBRIDGE CSD,"{st}  \n{city}",{amt},http://localhost:{PORT}/Account/Index?Property_ID={pn}&Tax_Year=2025')
    return "\r\n".join(out) + "\r\n"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ct="text/html"):
        b = body.encode()
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/DelinquentList":
            return self.send('<a href="/DelinquentList/Polsub?TaxYear=2025&PolSub=CAMBRIDGE%20TWP">CAMBRIDGE TWP 2</a> <a href="/DelinquentList/Polsub?TaxYear=2025&PolSub=ADAMS%20TWP">ADAMS TWP 1</a>')
        if u.path == "/DelinquentList/Polsub":
            p = (q.get("Polsub") or q.get("PolSub") or [""])[0]
            return self.send(f'<a href="/DelinquentList/ExportCsv?Polsub={p.replace(" ", "+")}&TaxYear=2025">CSV</a>')
        if u.path == "/DelinquentList/ExportCsv":
            return self.send(rows(q.get("Polsub", [""])[0]), "text/csv")
        if u.path == "/Account/Index":
            return self.send(PROP)
        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
