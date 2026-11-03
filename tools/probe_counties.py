"""Check which Ohio counties publish a delinquent tax list on the ISSG platform.
Run: python tools/probe_counties.py  -> prints a table and writes probe_result.json"""
import json, re, concurrent.futures as cf
import requests

OHIO = """Adams Allen Ashland Ashtabula Athens Auglaize Belmont Brown Butler Carroll Champaign Clark Clermont Clinton
Columbiana Coshocton Crawford Cuyahoga Darke Defiance Delaware Erie Fairfield Fayette Franklin Fulton Gallia Geauga Greene
Guernsey Hamilton Hancock Hardin Harrison Henry Highland Hocking Holmes Huron Jackson Jefferson Knox Lake Lawrence Licking
Logan Lorain Lucas Madison Mahoning Marion Medina Meigs Mercer Miami Monroe Montgomery Morgan Morrow Muskingum Noble Ottawa
Paulding Perry Pickaway Pike Portage Preble Putnam Richland Ross Sandusky Scioto Seneca Shelby Stark Summit Trumbull
Tuscarawas Union Van_Wert Vinton Warren Washington Wayne Williams Wood Wyandot""".split()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def hosts(name):
    s = name.lower().replace("_", "")
    d = name.lower().replace("_", "-")
    out = [f"{s}-treasurer-public.issg.io", f"{d}-treasurer-public.issg.io", f"{s}-auditor-public.issg.io",
           f"treasurer.{s}countyohio.gov", f"treasurer.{s}county.gov", f"realestate.{s}countyohio.gov"]
    return list(dict.fromkeys(out))


def check(name):
    res = {"county": name.replace("_", " ") + " County", "host": None, "townships": 0, "tried": []}
    for h in hosts(name):
        try:
            r = requests.get(f"https://{h}/DelinquentList", headers={"User-Agent": UA}, timeout=20)
            res["tried"].append(f"{h}:{r.status_code}")
            if r.status_code == 200 and re.search(r"delinquentlist/polsub", r.text, re.I):
                res["host"] = h
                res["townships"] = len(set(re.findall(r"[Pp]ol[Ss]ub=([^&\"']+)", r.text)))
                return res
        except requests.RequestException as e:
            res["tried"].append(f"{h}:{type(e).__name__}")
    return res


if __name__ == "__main__":
    with cf.ThreadPoolExecutor(12) as ex:
        out = list(ex.map(check, OHIO))
    found = [o for o in out if o["host"]]
    for o in found:
        print(f"FOUND  {o['county']:22} {o['host']:45} townships={o['townships']}")
    print(f"\n{len(found)} of {len(out)} counties have an ISSG delinquent list")
    json.dump(out, open("probe_result.json", "w"), indent=1)
