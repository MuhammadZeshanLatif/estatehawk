"""Known Ohio counties that publish their delinquent tax list on the ISSG platform.

Each ISSG site exposes the same URLs:
  /DelinquentList                      -> list of townships/cities (Polsub) with counts
  /DelinquentList/Polsub?Polsub=NAME    -> one township, with an "Export CSV" link
  /DelinquentList/ExportCsv?Polsub=NAME&TaxYear=YYYY
  /Account/Index?Property_ID=...&Tax_Year=...   -> property detail (values, owner contact, charges, map link)
"""

KNOWN_ISSG = [
    {"name": "Guernsey County", "state": "OH", "host": "treasurer.guernseycounty.gov", "lat": 40.05, "lng": -81.49, "verified": True},
    {"name": "Logan County", "state": "OH", "host": "realestate.logancountyohio.gov", "lat": 40.39, "lng": -83.77, "verified": True},
    {"name": "Geauga County", "state": "OH", "host": "realestate.geauga.oh.gov", "lat": 41.50, "lng": -81.17, "verified": True},
    {"name": "Tuscarawas County", "state": "OH", "host": "treasurer.co.tuscarawas.oh.us", "lat": 40.44, "lng": -81.47, "verified": True},
    {"name": "Erie County", "state": "OH", "host": "erie-treasurer-public.issg.io", "lat": 41.43, "lng": -82.70, "verified": False},
    {"name": "Fayette County", "state": "OH", "host": "fayette-treasurer-public.issg.io", "lat": 39.56, "lng": -83.46, "verified": True},
    # found by tools/probe_counties.py (Nov 2026)
    {"name": "Brown County", "state": "OH", "host": "brown-treasurer-public.issg.io", "lat": 38.93, "lng": -83.87, "verified": True},
    {"name": "Champaign County", "state": "OH", "host": "champaign-treasurer-public.issg.io", "lat": 40.14, "lng": -83.77, "verified": True},
    {"name": "Coshocton County", "state": "OH", "host": "coshocton-treasurer-public.issg.io", "lat": 40.30, "lng": -81.93, "verified": True},
    {"name": "Greene County", "state": "OH", "host": "greene-treasurer-public.issg.io", "lat": 39.69, "lng": -83.89, "verified": True},
    {"name": "Holmes County", "state": "OH", "host": "holmes-auditor-public.issg.io", "lat": 40.56, "lng": -81.93, "verified": True},
    {"name": "Lorain County", "state": "OH", "host": "lorain-auditor-public.issg.io", "lat": 41.30, "lng": -82.15, "verified": True},
    {"name": "Morgan County", "state": "OH", "host": "morgan-treasurer-public.issg.io", "lat": 39.62, "lng": -81.85, "verified": True},
    {"name": "Ottawa County", "state": "OH", "host": "ottawa-auditor-public.issg.io", "lat": 41.54, "lng": -83.10, "verified": True},
    {"name": "Seneca County", "state": "OH", "host": "seneca-auditor-public.issg.io", "lat": 41.12, "lng": -83.13, "verified": True},
    {"name": "Huron County", "state": "OH", "host": "www.huroncountytreasurer.org", "lat": 41.15, "lng": -82.60, "verified": True},
    # counties that publish a downloadable list file instead of ISSG (app/scraper/files.py)
    {"name": "Hamilton County", "state": "OH", "host": "file:hamilton", "lat": 39.17, "lng": -84.54, "verified": True},
    {"name": "Stark County", "state": "OH", "host": "file:stark", "lat": 40.81, "lng": -81.37, "verified": True},
    {"name": "Franklin County", "state": "OH", "host": "file:franklin", "lat": 39.97, "lng": -83.00, "verified": True},
    {"name": "Montgomery County", "state": "OH", "host": "file:montgomery", "lat": 39.75, "lng": -84.29, "verified": True},
    {"name": "Summit County", "state": "OH", "host": "file:summit", "lat": 41.13, "lng": -81.53, "verified": True},
    {"name": "Allen County", "state": "OH", "host": "file:allen", "lat": 40.77, "lng": -84.11, "verified": True},
    {"name": "Wayne County", "state": "OH", "host": "wayne-treasurer-public.issg.io", "lat": 40.83, "lng": -81.89, "verified": True},
]
