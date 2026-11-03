"""Scraper for county treasurer/auditor sites built on the ISSG platform (many Ohio counties).

Flow:
  1. GET /DelinquentList                 -> township (Polsub) names
  2. GET /DelinquentList/Polsub?Polsub=X -> find the ExportCsv link
  3. GET the CSV                         -> Property Number, Owner Name, School District, Location Address, Amount, View Property
  4. (enrich) GET the "View Property" page -> values, owner contact/mailing address, charges, map coordinates
"""
import csv, io, re, time
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


class Blocked(RuntimeError):
    """The site refused the request (403 and the like). Retrying will not help."""


class IssgClient:
    def __init__(self, host, delay=0.6, timeout=40):
        self.base = host if host.startswith("http") else f"https://{host}"
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        self.delay = delay
        self.timeout = timeout

    def get(self, path, **params):
        url = urljoin(self.base + "/", path.lstrip("/"))
        for attempt in range(3):
            try:
                r = self.s.get(url, params=params or None, timeout=self.timeout)
                if r.status_code == 200:
                    time.sleep(self.delay)
                    return r
                last = f"HTTP {r.status_code}"
                if r.status_code in (401, 403, 404):  # the site refuses this page: do not retry
                    raise Blocked(f"GET {url} failed: {last}")
            except requests.ConnectionError:
                last = "could not connect (site down, wrong address, or no internet)"
            except requests.Timeout:
                last = "the site took too long to answer"
            except requests.RequestException as e:
                last = type(e).__name__
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"GET {url} failed: {last}")

    # ---- list pages -------------------------------------------------------
    def polsubs(self):
        """Return [(name, count, href)] of townships/cities in the delinquent list.
        Sites differ in case: ?Polsub=, ?PolSub=, ?polsub= (and may add TaxYear)."""
        soup = BeautifulSoup(self.get("/DelinquentList").text, "html.parser")
        out, seen = [], set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/delinquentlist/polsub" not in href.lower():
                continue
            qs = {k.lower(): v for k, v in parse_qs(urlparse(href).query).items()}
            name = (qs.get("polsub") or [None])[0]
            if not name or name in seen:
                continue
            seen.add(name)
            m = re.search(r"(\d[\d,]*)\s*$", a.get_text(" ", strip=True))
            out.append((name, int(m.group(1).replace(",", "")) if m else None, urljoin(self.base + "/", href)))
        return out

    def export_csv_url(self, polsub=None, href=None):
        if href:
            soup = BeautifulSoup(self.get(href).text, "html.parser")
        else:
            params = {"Polsub": polsub} if polsub else {}
            soup = BeautifulSoup(self.get("/DelinquentList/Polsub", **params).text, "html.parser")
        for a in soup.find_all("a", href=True):
            if "ExportCsv" in a["href"]:
                return urljoin(self.base + "/", a["href"])
        q = {"Polsub": polsub} if polsub else {}
        return f"{self.base}/DelinquentList/ExportCsv?{urlencode(q)}"

    def tax_year_from(self, url):
        qs = {k.lower(): v for k, v in parse_qs(urlparse(url).query).items()}
        y = (qs.get("taxyear") or [None])[0]
        return int(y) if y and y.isdigit() else None

    def fetch_rows(self, polsub=None, href=None):
        url = self.export_csv_url(polsub, href)
        text = self.get(url).text
        return parse_csv(text), self.tax_year_from(url)

    def all_rows(self, progress=None):
        """Every delinquent parcel in the county (de-duplicated by parcel number)."""
        rows, year = {}, None
        subs = self.polsubs()
        if not subs:  # some sites list the whole county on one page
            r, year = self.fetch_rows(None)
            return r, year
        for i, (name, _cnt, href) in enumerate(subs):
            r, y = self.fetch_rows(name, href)
            year = year or y
            for row in r:
                rows.setdefault(row["parcel_number"], row)
            if progress:
                progress(i + 1, len(subs), name)
        return list(rows.values()), year

    # ---- property page ----------------------------------------------------
    def property(self, url):
        info = parse_property(self.get(url).text)
        u = urlparse(url)
        qs = {k.lower(): v[0] for k, v in parse_qs(u.query).items()}
        pid = qs.get("property_id")
        # Auditor-style sites (/RealEstate/...) also have an aerial parcel picture and a dwelling page
        if pid and "/realestate/" in u.path.lower():
            info["photo_url"] = f"{u.scheme}://{u.netloc}/api/RealEstateMap?Property_ID={pid}"
            if (info.get("land_use") or "")[:1] == "5" and (info.get("improvement_value") or 0) > 0:
                try:
                    year = qs.get("tax_year") or qs.get("taxyear") or ""
                    d = self.get(f"{u.scheme}://{u.netloc}/RealEstate/Dwelling", Property_ID=pid, TaxYear=year, RowNumber=0)
                    info.update(parse_dwelling(d.text))
                except Exception:
                    pass
        return info


def _num(s):
    if s is None:
        return None
    s = s.replace("$", "").replace(",", "").strip()
    if s in ("", "--", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def split_location(loc):
    """'123 MAIN ST\\nCAMBRIDGE OH 43725' -> street, city, state, zip"""
    lines = [l.strip() for l in re.split(r"[\r\n]+", loc or "") if l.strip()]
    street = lines[0] if lines else ""
    city = state = zp = ""
    if len(lines) > 1:
        m = re.match(r"(.*?)\s+([A-Z]{2})\s+(\d{5})(?:-\d{4})?$", lines[-1])
        if m:
            city, state, zp = m.group(1).strip(), m.group(2), m.group(3)
        else:
            city = lines[-1]
    return street, city, state, zp


def parse_csv(text):
    rows = []
    rd = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    for r in rd:
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        pn = r.get("Property Number") or r.get("Parcel Number")
        if not pn:
            continue
        street, city, state, zp = split_location(r.get("Location Address", ""))
        rows.append({
            "parcel_number": pn,
            "owner_name": re.sub(r"\s{2,}", " & ", r.get("Owner Name", "")).strip(),
            "school_district": r.get("School District", ""),
            "street": street, "city": city, "state": state or "OH", "zip": zp,
            "amount_owed": _num(r.get("Amount")),
            "property_url": r.get("View Property", ""),
        })
    return rows


def _labelled(soup, label):
    """ISSG pages put a label div followed by a value div."""
    for el in soup.find_all(["div", "th", "td", "span"]):
        if el.get_text(" ", strip=True).rstrip(":").lower() == label.lower() and not el.find(["div", "table"]):
            sib = el.find_next_sibling()
            if sib is not None:
                return sib.get_text("\n", strip=True).replace("\xa0", " ").strip()
    return None


def _table_row(table, row_label, col):
    heads = [th.get_text(" ", strip=True) for th in table.select("thead th")]
    for tr in table.select("tbody tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        if cells[0].get_text(" ", strip=True).split("\n")[0].strip().lower().startswith(row_label.lower()):
            vals = [c.get_text(" ", strip=True) for c in cells[1:]]
            if col in heads and heads.index(col) < len(vals):
                return vals[heads.index(col)], cells[0].get_text(" ", strip=True)
    return None, None


def _int(s):
    n = _num(re.sub(r"[^0-9.,-]", "", s or "") or None)
    return int(n) if n is not None else None


def parse_dwelling(html):
    """Dwelling card: <div aria-label="Bedrooms">3</div> ..."""
    soup = BeautifulSoup(html, "html.parser")
    val = lambda k: (soup.find(attrs={"aria-label": k}).get_text(" ", strip=True) if soup.find(attrs={"aria-label": k}) else None)
    out = {"style": val("Style"), "condition": val("Condition"), "beds": _int(val("Bedrooms")), "baths_full": _int(val("Full Baths")),
           "baths_half": _int(val("Half Baths")), "year_built": _int(val("Year Built")), "living_area": _int(val("Living Area")),
           "stories": _num(val("Stories"))}
    return {k: v for k, v in out.items() if v not in (None, "", 0) or k in ("baths_half",)}


def parse_property(html):
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    hdr = lambda key: (soup.find(attrs={"aria-labelledby": key}) or None)
    for key, name in (("HeaderLegalDescription", "legal_desc"), ("HeaderAcres", "acres"), ("HeaderLocation", "location")):
        el = hdr(key)
        if el:
            out[name] = el.get_text("\n", strip=True)
    if out.get("acres"):
        out["acres"] = _num(out["acres"])
    cy = soup.find(attrs={"aria-labelledby": "PropertyCertifiedDelinquentYear"})
    if cy:
        y = re.search(r"(19|20)\d\d", cy.get_text())
        if y:
            out["cert_year"] = int(y.group(0))
    if out.get("location"):
        _st, city, state, zp = split_location(out["location"])
        if city:
            out["loc_city"], out["loc_zip"] = city, zp
    m = soup.find("a", href=re.compile(r"google\.com/maps/place/(-?\d+\.\d+),(-?\d+\.\d+)"))
    if m:
        lat, lng = re.search(r"place/(-?\d+\.\d+),(-?\d+\.\d+)", m["href"]).groups()
        out["lat"], out["lng"] = float(lat), float(lng)
    contact = _labelled(soup, "Contact")
    if contact:
        lines = [l.strip() for l in contact.split("\n") if l.strip()]
        out["mail_address"] = ", ".join(lines[1:]) if len(lines) > 1 else contact
        mm = re.search(r"\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*$", lines[-1]) if lines else None
        if mm:
            out["mail_state"], out["mail_zip"] = mm.group(1), mm.group(2)
    on = _labelled(soup, "Owner Name")
    if on:
        out["owner_full_name"] = on
    lu = _labelled(soup, "Land Use")
    if lu:
        out["land_use"] = lu
    for t in soup.find_all("table"):
        heads = [th.get_text(" ", strip=True) for th in t.select("thead th")]
        if "Appraised" in heads:
            for row, key in (("Land", "land_value"), ("Improvement", "improvement_value"), ("Total", "appraised_total")):
                v, _ = _table_row(t, row, "Appraised")
                if v is not None and key not in out:
                    out[key] = _num(v)
            _, lab = _table_row(t, "Owner Occupancy", "Appraised")
            if lab:
                out["owner_occupied"] = 1 if "(Y)" in lab.replace(" ", "") else 0
        if "Prior" in heads and "Total" in heads:
            tot_row = None
            for tr in t.select("tbody tr"):
                c = [x.get_text(" ", strip=True) for x in tr.find_all(["th", "td"])]
                if not c:
                    continue
                if c[0].lower().startswith("total") and tot_row is None:
                    tot_row = c
                if c[0].lower().startswith("tax") and "annual_tax" not in out:
                    vals = dict(zip(heads, c[1:]))
                    first, second = _num(vals.get("First")), _num(vals.get("Second"))
                    if first is not None or second is not None:
                        out["annual_tax"] = (first or 0) + (second or 0)
                if c[0].lower().startswith("due") and "total_due" not in out:
                    vals = dict(zip(heads, c[1:]))
                    out["total_due"] = _num(vals.get("Total"))
            if tot_row:
                vals = dict(zip(heads, tot_row[1:]))
                out["prior_due"] = _num(vals.get("Prior"))
    return out
