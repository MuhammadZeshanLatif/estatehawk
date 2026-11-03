"""Download list files and print their shape: sheet names, header row, first rows (or first text of a PDF / HTML)."""
import io, re, sys
import requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
for u in open(sys.argv[1]).read().split():
    try:
        r = requests.get(u, headers=UA, timeout=120)
    except requests.RequestException as e:
        print("F", u, "ERR", type(e).__name__); continue
    ct = r.headers.get("content-type", "")
    print("F", u, r.status_code, ct, len(r.content))
    b = r.content
    try:
        if b[:2] == b"PK":
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True)
            for ws in wb.worksheets[:3]:
                print("   SHEET", ws.title, ws.max_row, ws.max_column)
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    print("   R", [c for c in row][:20])
                    if i >= 6: break
        elif b[:4] == b"%PDF":
            import pdfplumber
            with pdfplumber.open(io.BytesIO(b)) as pdf:
                print("   PAGES", len(pdf.pages))
                for line in (pdf.pages[0].extract_text() or "").splitlines()[:25]:
                    print("   T", line[:160])
                if len(pdf.pages) > 1:
                    for line in (pdf.pages[1].extract_text() or "").splitlines()[:8]:
                        print("   T2", line[:160])
        else:
            txt = r.text
            body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", txt, flags=re.S | re.I)
            tables = re.findall(r"<tr.*?</tr>", body, re.S | re.I)
            print("   TR", len(tables))
            for t in tables[:8]:
                print("   R", re.sub(r"<[^>]+>|\s+", " ", t).strip()[:200])
            for h, tx in re.findall(r"href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", txt, re.S | re.I):
                if re.search(r"\.(pdf|xlsx?|csv|zip|txt)|delinq|download", h + tx, re.I):
                    print("   L", h[:160], "|", re.sub(r"<[^>]+>|\s+", " ", tx).strip()[:60])
    except Exception as e:
        print("   PARSE-ERR", e)
