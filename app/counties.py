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
    {"name": "Fayette County", "state": "OH", "host": "", "lat": 39.56, "lng": -83.46, "verified": False},
]
