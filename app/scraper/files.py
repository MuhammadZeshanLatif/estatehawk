"""Counties that do not run ISSG but publish their delinquent list as a downloadable file (Excel / CSV).

A county uses this when its `host` is "file:<key>", e.g. "file:hamilton".
Each source returns rows in the same shape as the ISSG scraper:
  parcel_number, owner_name, school_district, street, city, state, zip, amount_owed, property_url
plus optional extras (mail_address, mail_zip, land_use, appraised_total, land_value, improvement_value).
"""
import datetime as dt
import io
import re
import time
from urllib.parse import urljoin

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def _num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.\-]", "", str(v))
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _s(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""


def _split_addr(text):
    """'6112 BENNEVILLE ST CINCINNATI OH 45230' -> (street, city, zip). City is best effort."""
    t = _s(text)
    m = re.match(r"(.*?)[ ,]+([A-Z][A-Z .'-]*?)[ ,]+OH[ ,]+(\d{5})", t)
    if not m:
        return t, "", ""
    street, city, z = m.group(1).strip(), m.group(2).strip(), m.group(3)
    # street suffixes run into the city name ("VINE ST W ALLIANCE"): split on the last street word
    sm = re.match(r"(.*\b(?:ST|AVE|RD|DR|LN|CT|BLVD|PL|WAY|PIKE|HWY|CIR|TER|PKWY|TRL|RUN|SQ)\b(?:\s+[NSEW])?)\s+(.*)$", f"{street} {city}")
    if sm and not re.search(r"\b(?:ST|AVE|RD|DR|LN|CT|BLVD)\b", city):
        street, city = sm.group(1), sm.group(2)
    return street, city, z


def _row(parcel, owner, amount, street="", city="", zip_="", district="", url=None, **extra):
    r = {"parcel_number": _s(parcel), "owner_name": _s(owner), "school_district": _s(district),
         "street": _s(street), "city": _s(city), "state": "OH", "zip": _s(zip_)[:5], "amount_owed": _num(amount),
         "property_url": url}
    r.update({k: v for k, v in extra.items() if v not in (None, "")})
    return r


def _xlsx_rows(content):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    return list(ws.iter_rows(values_only=True))


def _header_index(rows, must):
    """Find the header row (the first row containing every name in `must`) -> (row_index, {name: col})."""
    for i, row in enumerate(rows[:20]):
        names = [_s(c).lower() for c in row]
        if all(m in names for m in must):
            return i, {n: j for j, n in enumerate(names) if n}
    raise RuntimeError(f"Could not find the columns {must} in the file (format changed?)")


# ---- sources -----------------------------------------------------------------
def hamilton(c):
    rows = _xlsx_rows(c.get("https://www.hamiltoncountyauditor.org/download/Delinquent/unpaid.xlsx").content)
    h, col = _header_index(rows, ["parcel_number", "owner_name_1", "unpaid_amount"])
    year = dt.date.today().year - 1
    out = []
    for r in rows[h + 1:]:
        pn = _s(r[col["parcel_number"]])
        amt = _num(r[col["unpaid_amount"]])
        if not pn or not amt or amt < 1:
            continue
        owner = " ".join(x for x in (_s(r[col["owner_name_1"]]), _s(r[col.get("owner_name_2", -1)] if "owner_name_2" in col else "")) if x)
        mail_city = _s(r[col["owner_address_2"]]) if "owner_address_2" in col else ""
        mz = re.search(r"(\d{5})", mail_city)
        out.append(_row(pn, owner, amt, district=_s(r[col["tax_district"]]) if "tax_district" in col else "",
                        url=f"https://wedge3.hcauditor.org/view/re/{pn}/{year}/summary",
                        mail_address=f"{_s(r[col['owner_address_1']])}, {mail_city}".strip(", "),
                        mail_state="OH" if ",OH" in mail_city.replace(" ", "") else None,
                        mail_zip=mz.group(1) if mz else None, land_use=_s(r[col["property_class"]]) if "property_class" in col else None))
    return out, year


def stark(c):
    page = c.get("https://www.starkcountyohio.gov/government/offices/treasurer/departments/delinquent_tax_and_foreclosures/index.php")
    links = re.findall(r"href=[\"']([^\"']*Delq_Taxpayer_List[^\"']*\.xlsx)[\"']", page.text, re.I)
    if not links:
        raise RuntimeError("Stark delinquent list link not found on the treasurer page")
    url = urljoin("https://www.starkcountyohio.gov/", links[0].replace(" ", "%20"))
    rows = _xlsx_rows(c.get(url).content)
    h, col = _header_index(rows, ["parcel_id", "current_owner", "total_delq"])
    out = []
    for r in rows[h + 1:]:
        pn = _s(r[col["parcel_id"]])
        if not pn:
            continue
        street, city, z = _split_addr(r[col["situs_address"]]) if "situs_address" in col else ("", "", "")
        cert = r[col["cert_delq_date"]] if "cert_delq_date" in col else None
        out.append(_row(pn, r[col["current_owner"]], r[col["total_delq"]], street, city, z,
                        land_use=_s(r[col["use_code"]]) if "use_code" in col else None,
                        land_value=_num(r[col["mkt_land_val"]]) if "mkt_land_val" in col else None,
                        improvement_value=_num(r[col["mkt_bldg_val"]]) if "mkt_bldg_val" in col else None,
                        appraised_total=_num(r[col["mkt_total_val"]]) if "mkt_total_val" in col else None,
                        cert_year=cert.year if isinstance(cert, dt.datetime) else None))
    return out, None


def allen(c):
    page = c.get("https://allencountyohauditor.com/delinquent-lists-and-auditor-sales/")
    links = re.findall(r"href=[\"']([^\"']*Delq[^\"']*\.xlsx)[\"']", page.text, re.I)
    if not links:
        raise RuntimeError("Allen delinquent list link not found")
    rows = _xlsx_rows(c.get(urljoin(page.url, links[0])).content)
    h, col = _header_index(rows, ["parcel", "owner", "amount"])
    out = []
    for r in rows[h + 1:]:
        pn = _s(r[col["parcel"]])
        if pn:
            out.append(_row(pn, r[col["owner"]], r[col["amount"]], district=_s(r[col["tax district"]]) if "tax district" in col else ""))
    return out, None


SOURCES = {"hamilton": hamilton, "stark": stark, "allen": allen}


# ---- property pages ------------------------------------------------------------
def parse_wedge(html):
    """DEVNET wEdge property summary (Hamilton and other wEdge counties)."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    toks = [t.strip() for t in re.split(r"<[^>]+>", body)]
    toks = [re.sub(r"\s+", " ", t) for t in toks if t and t.strip() and not t.strip().startswith("(")]
    val = {}
    for i, t in enumerate(toks[:-1]):
        if t not in val:
            val[t] = toks[i + 1]
    out = {}
    if val.get("Address"):
        out["street"] = val["Address"].upper()
    own = val.get("Owner Name and Address")
    if own:
        out["owner_full_name"] = own
    mail = val.get("Tax Bill Mail Address") or own
    if mail:
        m = re.search(r"(\d+\s.*?)\s([A-Z .]+)\s(OH|[A-Z]{2})\s(\d{5})", mail)
        if m:
            out["mail_address"], out["mail_state"], out["mail_zip"] = f"{m.group(1)}, {m.group(2)}", m.group(3), m.group(4)
    num = lambda k: _num(val.get(k))
    out.update({"land_value": num("Market Land Value"), "improvement_value": num("Market Improvement Value"),
                "appraised_total": num("Market Total Value"), "annual_tax": num("Total Tax"), "acres": num("Acreage"),
                "year_built": int(num("Year Built")) if num("Year Built") else None,
                "beds": int(num("# Bedrooms")) if num("# Bedrooms") else None,
                "baths_full": int(num("# Full Bathrooms")) if num("# Full Bathrooms") else None,
                "baths_half": int(num("# Half Bathrooms")) if num("# Half Bathrooms") else None,
                "legal_desc": val.get("Property Description"), "land_use": val.get("Auditor Land Use")})
    occ = val.get("Owner Occupancy Credit")
    if occ:
        out["owner_occupied"] = 1 if occ.lower().startswith("y") else 0
    sd = val.get("School District")
    if sd:
        out["school_district"] = sd
    return {k: v for k, v in out.items() if v not in (None, "")}


class FileClient:
    def __init__(self, host, delay=0.5, timeout=120):
        self.key = host.split(":", 1)[1] if ":" in host else host
        if self.key not in SOURCES:
            raise RuntimeError(f"Unknown file source '{self.key}'")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        self.delay, self.timeout = delay, timeout

    def get(self, url):
        last = None
        for attempt in range(3):
            try:
                r = self.s.get(url, timeout=self.timeout)
                if r.status_code == 200:
                    return r
                last = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                last = type(e).__name__
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"GET {url} failed: {last}")

    def all_rows(self, progress=None):
        rows, year = SOURCES[self.key](self)
        seen = {}
        for r in rows:
            seen.setdefault(r["parcel_number"], r)
        if progress:
            progress(1, 1, self.key)
        return list(seen.values()), year

    def property(self, url):
        r = self.get(url)
        time.sleep(self.delay)
        if "hcauditor.org" in url or "wedge" in url:
            return parse_wedge(r.text)
        return {}
