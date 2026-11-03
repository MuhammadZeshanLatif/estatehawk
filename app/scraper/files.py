"""Counties that do not run ISSG but publish their delinquent list as a downloadable file (Excel / CSV).

A county uses this when its `host` is "file:<key>", e.g. "file:hamilton".
Each source returns rows in the same shape as the ISSG scraper:
  parcel_number, owner_name, school_district, street, city, state, zip, amount_owed, property_url
plus optional extras (mail_address, mail_zip, land_use, appraised_total, land_value, improvement_value).
"""
import datetime as dt
import html as htmllib
import io
import re
import time
from urllib.parse import urljoin, urlencode, urlparse

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
    sm = re.match(r"(.*\b(?:ST|AVE|RD|DR|LN|CT|BLVD|PL|WAY|PIKE|HWY|CIR|TER|PKWY|TRL|RUN|SQ)\b(?:\s+(?:NE|NW|SE|SW|[NSEW]))?)\s+(.*)$", f"{street} {city}")
    if sm and sm.group(2):
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


def summit(c):
    """Summit County: the published delinquent notice on akronlegalnews.com, one page per taxing district."""
    idx = c.get("https://akronlegalnews.com/notices/delinquent_taxes")
    pages = sorted(set(re.findall(r"/notices/delinquent_taxes_detail/(\d+)", idx.text)))
    if not pages:
        raise RuntimeError("Summit notice index has no district pages")
    year = None
    m = re.search(r"Published in newspapers on \w+, (\w+ \d+)\w*, (\d{4})", idx.text)
    out = []
    for i, pid in enumerate(pages):
        t = htmllib.unescape(re.sub(r"<[^>]+>", " ", c.get(f"https://akronlegalnews.com/notices/delinquent_taxes_detail/{pid}").text))
        hm = re.search(r"Published in newspapers on \w+, \w+ \d+\w*, (\d{4})", t)
        year = year or (int(hm.group(1)) if hm else None)
        for e in re.split(r"\s*\u2022\s*", re.sub(r"\s+", " ", t)):
            em = re.match(r".*?\b(\d{7})\s+(\*\s+)?([\d,]+\.\d{1,2})\s+(.+)$", e)
            if not em:
                continue
            pn, contract, amt, rest = em.group(1), em.group(2), em.group(3), em.group(4).strip()
            rest = re.split(r"\s(?:Notice is hereby|KRISTEN|The Akron Legal News)", rest)[0][:300]
            out.append(_row(pn, rest, amt,
                            url=f"https://propertyaccess.summitoh.net/Datalets/Datalet.aspx?sIndex=0&idx=1&UseSearch=no&pin={pn}&jur=077&taxyr={(year or dt.date.today().year) }&LMparent=20",
                            legal_desc=rest))
        time.sleep(0.3)
    return out, (year - 1 if year else None)


def montgomery(c):
    """Montgomery County (Dayton): the treasurer's monthly delinquent file (zip with one CSV, every field we need)."""
    import csv, zipfile
    base = "https://go.mcohio.org/applications/treasurer/search/"
    links = re.findall(r"data\\Delq\\(Delq_\d{8}\.zip)", c.get(base + "fdpopup.cfm?dtype=DQ").text)
    if not links:
        raise RuntimeError("Montgomery delinquent file link not found")
    z = zipfile.ZipFile(io.BytesIO(c.get(base + "data/Delq/" + sorted(links)[-1]).content))
    text = z.read(z.namelist()[0]).decode("latin1")
    rd = csv.reader(io.StringIO(text))
    head = [h.strip().upper() for h in next(rd)]
    ix = {h: i for i, h in enumerate(head)}
    g = lambda row, k: row[ix[k]].strip() if k in ix and ix[k] < len(row) else ""
    out = []
    for row in rd:
        if g(row, "CLS") in ("U", "E") or not g(row, "PARCELID"):
            continue
        amt = _num(g(row, "NETDELQ"))
        if not amt or amt < 1:
            continue
        loc = g(row, "PARCELLOCATION")
        mail1, mail3 = g(row, "PADDR1"), g(row, "PADDR3") or g(row, "PADDR2")
        mz = re.search(r"\b(\d{5})", mail3)
        city = ""
        if loc and mail1 and loc.split()[:2] == mail1.split()[:2]:  # owner lives there: the mailing city is the property city
            cm = re.match(r"([A-Z .]+?)\s+OH\b", mail3)
            city = cm.group(1).strip() if cm else ""
        yb = _num(g(row, "YRBLT"))
        cy = _num(g(row, "CERTDLQYR"))
        out.append(_row(g(row, "PARCELID"), " & ".join(x for x in (g(row, "OWNERNAME1"), g(row, "OWNERNAME2")) if x), amt,
                        loc, city, "", district=g(row, "TXDST"),
                        mail_address=", ".join(x for x in (mail1, mail3) if x), mail_zip=mz.group(1) if mz else None,
                        land_use=g(row, "LUC"), land_value=_num(g(row, "ASMTLAND")), improvement_value=_num(g(row, "ASMTBLDG")),
                        appraised_total=_num(g(row, "ASMTTOTAL")), year_built=int(yb) if yb and yb > 1700 else None,
                        cert_year=int(cy) if cy and cy > 1900 else None, acres=_num(g(row, "ACRES")) or None,
                        legal_desc=" ".join(x for x in (g(row, "LEGAL1"), g(row, "LEGAL2"), g(row, "LEGAL3")) if x)))
    # each taxing district is one city/township: borrow the most common known city for the rest
    from collections import Counter
    best = {}
    for r in out:
        if r["city"]:
            best.setdefault(r["school_district"], Counter())[r["city"]] += 1
    for r in out:
        if not r["city"] and r["school_district"] in best:
            r["city"] = best[r["school_district"]].most_common(1)[0][0]
    return out, None


def franklin(c):
    """Franklin County (Columbus): the auditor's monthly Tax Accounting export. Delinquent = unpaid prior-year balance."""
    import csv, zipfile
    root = "https://apps.franklincountyauditor.com"
    folders = []
    for y in (dt.date.today().year, dt.date.today().year - 1):
        t = c.get(f"{root}/Outside_User_Files/{y}/").text
        folders += re.findall(r"href=\"(/Outside_User_Files/\d{4}/[^\"]*Tax%20Accounting/)\"", t, re.I)
        if folders:
            break
    if not folders:
        raise RuntimeError("Franklin Tax Accounting folder not found")
    z = zipfile.ZipFile(io.BytesIO(c.get(root + sorted(folders)[-1] + "Tab-Delimited.zip").content))

    def table(name):
        with z.open(name) as f:
            rd = csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace"), delimiter="\t")
            head = next(rd)
            ix = {h.strip(): i for i, h in enumerate(head)}
            for row in rd:
                yield ix, row

    due = {}
    for ix, row in table("TaxDetail.txt"):
        prior = _num(row[ix["TotPrior"]]) or 0
        total = _num(row[ix["TotTotal"]]) or 0
        if prior > 1 and total > 1:
            due[row[ix["Parcel Id"]].strip('"')] = total
    vals = {}
    for ix, row in table("Value.txt"):
        pid = row[ix["Parcel Id"]].strip('"')
        if pid in due and row[ix["ValueType"]].strip('"') == "BASE":
            vals[pid] = (_num(row[ix["MarketLand"]]), _num(row[ix["MarketImpr"]]))
    out = []
    for ix, row in table("Parcel.txt"):
        g = lambda k: row[ix[k]].strip().strip('"') if k in ix and ix[k] < len(row) else ""
        pid = g("PARCEL ID")
        if pid not in due:
            continue
        site = g("SiteAddress")
        street, city, z5 = _split_addr(site.replace(",", " ")) if site else ("", "", "")
        if not z5:
            street = site.split(",")[0]
        land, impr = vals.get(pid, (None, None))
        cdq = _num(g("CDQ"))
        out.append(_row(pid, " & ".join(x for x in (g("OwnerName1"), g("OwnerName2")) if x), due[pid], street,
                        city or g("City").replace(" CITY", "").title().upper(), z5 or g("ZipCode"), district=g("SchoolDistrictDesc"),
                        url=None, mail_address=", ".join(x for x in (g("TaxpayerAddress1") or g("OwnerAddress1"), g("TaxpayerAddress2") or g("OwnerAddress2")) if x),
                        land_use=f"{g('LUC')} - {g('LUCDesc')}".strip(" -"), land_value=land, improvement_value=impr,
                        appraised_total=(land or 0) + (impr or 0) if land is not None else None,
                        cert_year=int(cdq) if cdq and cdq > 1900 else None, acres=_num(g("Acres")) or None,
                        legal_desc=" ".join(x for x in (g("Legal1"), g("Legal2"), g("Legal3")) if x)))
    return out, None


SOURCES = {"franklin": franklin, "montgomery": montgomery, "hamilton": hamilton, "stark": stark, "allen": allen, "summit": summit}


# ---- property pages ------------------------------------------------------------
def parse_wedge(html):
    """DEVNET wEdge property summary (Hamilton and other wEdge counties)."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    toks = [t.strip() for t in re.split(r"<[^>]+>", body)]
    toks = [re.sub(r"\s+", " ", htmllib.unescape(t)).strip() for t in toks if t and t.strip() and not t.strip().startswith("(")]
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


def parse_iasworld(html):
    """Tyler iasWorld Public Access datalet (Summit and other iasWorld counties)."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    toks = [re.sub(r"\s+", " ", htmllib.unescape(t)).strip() for t in re.split(r"<[^>]+>", body)]
    toks = [t for t in toks if t]
    val = {}
    for i, t in enumerate(toks[:-1]):
        val.setdefault(t, toks[i + 1])
    out = {}
    sa = val.get("Site Address")
    if sa and re.match(r"\d", sa):
        parts = [p.strip() for p in sa.split(",")]
        out["street"] = parts[0].upper()
        cz = re.match(r"([A-Z .]+?)\s+(\d{5})", parts[-1] or "")
        if cz:
            out["loc_city"], out["loc_zip"] = cz.group(1).strip(), cz.group(2)
    if "Owner 2" in toks:
        k = toks.index("Owner 2")
        owners = []
        for t in toks[k + 1:k + 4]:
            if re.search(r"Homestead|Land Summary|Owner Occupancy", t):
                break
            owners.append(t)
        if owners:
            out["owner_name"] = " & ".join(owners[:2])
            out["owner_full_name"] = out["owner_name"]
    num = lambda k: _num(val.get(k))
    out.update({"land_use": val.get("Land Use Code"), "year_built": int(num("Year Built")) if num("Year Built") else None,
                "beds": int(num("Bedrooms")) if num("Bedrooms") else None,
                "baths_full": int(num("Full Baths")) if num("Full Baths") else None,
                "baths_half": int(num("Half Baths")) if num("Half Baths") else None,
                "living_area": int(num("Square Feet")) if num("Square Feet") else None,
                "stories": num("Stories"), "style": val.get("Style"), "condition": val.get("CDU")})
    occ = val.get("Owner Occupancy Credit")
    if occ in ("YES", "NO"):
        out["owner_occupied"] = 1 if occ == "YES" else 0
    if val.get("Taxing District"):
        out["school_district"] = val["Taxing District"]
    return {k: v for k, v in out.items() if v not in (None, "", "-")}


_BUNDLES = {}


def _aia_bundle(hostname):
    """Some county/vendor servers send their certificate without the intermediate one. Browsers fetch it from
    the certificate's AIA 'CA Issuers' link; we do the same and keep full verification on."""
    if hostname in _BUNDLES:
        return _BUNDLES[hostname]
    import socket, ssl, tempfile, certifi
    from cryptography import x509
    from cryptography.x509.oid import AuthorityInformationAccessOID
    from cryptography.hazmat.primitives.serialization import Encoding
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE  # only to read the certificate; requests verifies below
    with socket.create_connection((hostname, 443), timeout=20) as sk, ctx.wrap_socket(sk, server_hostname=hostname) as ss:
        leaf = x509.load_der_x509_certificate(ss.getpeercert(True))
    aia = leaf.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
    url = next(d.access_location.value for d in aia if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS)
    raw = requests.get(url, timeout=30).content
    try:
        inter = x509.load_der_x509_certificate(raw)
    except ValueError:
        inter = x509.load_pem_x509_certificate(raw)
    f = tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False)
    f.write(open(certifi.where(), "rb").read() + b"\n" + inter.public_bytes(Encoding.PEM))
    f.close()
    _BUNDLES[hostname] = f.name
    return f.name


def lgbs(c, state, county):
    """Linebarger (LGBS) tax-sale listings: Texas counties (and Philadelphia). Properties headed to or struck off at a
    tax foreclosure sale. No owner names in this feed; the county appraisal district has them."""
    import json
    out, url = [], "https://taxsales.lgbs.com/api/property_sales/?" + urlencode({"state": state, "county": county, "limit": 500})
    while url:
        j = c.get(url).json()
        for x in j.get("results", []):
            if (x.get("state") or "").upper() != state.upper() or (x.get("county") or "").upper() != county.upper():
                continue  # the API ignores unknown filters: never mix counties
            geo = (x.get("geometry") or {}).get("coordinates") or [None, None]
            sale = x.get("sale_date_only") or x.get("sale_date") or ""
            note = ", ".join(v for v in (f"Tax sale: {x.get('sale_type') or ''}".strip(": "), x.get("status") or "",
                                             f"sale date {sale[:10]}" if sale else "", f"cause {x['cause_nbr']}" if x.get("cause_nbr") else "") if v)
            out.append(_row(x.get("account_nbr") or x.get("uid"), "", x.get("minimum_bid"),
                            " ".join(v for v in (x.get("prop_address_one"), x.get("prop_address_two")) if v),
                            x.get("prop_city"), x.get("prop_zipcode"), url=None,
                            appraised_total=_num(x.get("value")), legal_desc=note,
                            lat=geo[1], lng=geo[0]))
            out[-1]["state"] = (x.get("prop_state") or state)[:2]
        url = j.get("next")
        time.sleep(1.5)
        if url and url.startswith("http://"):
            url = "https://" + url[7:]
    return out, None


SOURCES["lgbs"] = lgbs


class FileClient:
    def __init__(self, host, delay=0.5, timeout=120):
        parts = host.split(":")
        # "file:hamilton" -> hamilton(); "lgbs:TX:HARDIN COUNTY" -> lgbs("TX", "HARDIN COUNTY")
        self.key, self.args = (parts[1], parts[2:]) if parts[0] == "file" else (parts[0], parts[1:])
        if self.key not in SOURCES:
            raise RuntimeError(f"Unknown file source '{self.key}'")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        self.delay, self.timeout = delay, timeout

    def get(self, url):
        last = None
        for attempt in range(3):
            try:
                try:
                    r = self.s.get(url, timeout=self.timeout)
                except requests.exceptions.SSLError:
                    r = self.s.get(url, timeout=self.timeout, verify=_aia_bundle(urlparse(url).hostname))
                if r.status_code == 200:
                    return r
                last = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                last = type(e).__name__
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"GET {url} failed: {last}")

    def all_rows(self, progress=None):
        rows, year = SOURCES[self.key](self, *self.args)
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
        if "Datalet" in url:
            return parse_iasworld(r.text)
        return {}
