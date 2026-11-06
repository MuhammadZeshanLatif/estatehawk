# EstateHawk app

Finds tax-delinquent properties in Ohio counties every night, scores them as deals, and helps you contact owners.

## Chalana (Windows)
1. Python 3.10+ install karein (python.org, "Add python.exe to PATH" tick karein).
2. Is folder mein `start.bat` par double-click karein. Pehli dafa 1-2 minute lagte hain.
3. Browser mein http://localhost:8000 khulega. Setup wizard: naam, counties, phir "Download real county data" ya "demo data".
4. Roz subah 08:00 (Pakistan time) har county ka data khud update hota hai. Ohio ki sites US raat ~10 baje update hoti hain = Pakistan subah ~7-8 baje.
5. `setup_autostart.bat` ek dafa chalayein: Windows on hote hi app khud (minimized) chal jayegi. Computer 8 baje band tha to jab bhi app chale, sync khud poori ho jati hai.
6. Jab chahein naya data: Deals par refresh button, ya Counties > Sync all / har county ke menu mein "Sync now". Waqt badalna: Settings > Profile > Nightly county sync time.

## Gemini API key (optional)
Settings > Integrations > Gemini AI mein primary aur backup keys dalein (ya `.env` file mein `GEMINI_API_KEY=` aur `GEMINI_API_KEY_BACKUP=`). Primary fail ho to backup khud try hoti hai. Independent quota ke liye doosri key alag Google project se banayein. Dono fail hon to offer letter/email built-in template se banta hai; "Why this score" AI explanation us waqt unavailable hoti hai.

## Screens (design/chatgpt ke mutabiq)
Deals, Deal detail (tax history, why this score, offer draft, notes), Map, Alerts (rules + channels + daily digest), Counties (sync status, 30-day trend), Outreach (kanban, follow-ups, reply rate, batch letters), Reports (KPIs, charts, funnel, CSV/PDF), Settings (profile, scoring weights with live preview, integrations), Onboarding wizard, mobile layout.

## Data kahan se aata hai
Ohio ki ISSG counties (Guernsey, Logan, Geauga, Tuscarawas; Erie unverified):
`/DelinquentList` > har township ka `ExportCsv` > har parcel ka `/Account/Index` page (value, owner mailing address, owner-occupancy, prior/annual tax, map coordinates).
Naya county: Counties > Add county > website dalein > Test connection.

## Code
- `app/scraper/issg.py` county site reader, `app/jobs.py` nightly sync + diff + alerts, `app/scoring.py` deal score, `app/ai.py` Gemini, `app/notify.py` email/Slack/SMS/WhatsApp, `app/main.py` API.
- `web/` front-end (no build step). `tests/mock_issg.py` fake county site for testing.
- Database: `data/estatehawk.db` (SQLite). Backup = copy this file.

## Limits (honest)
- Value = county appraisal; equity ignores mortgages (not public in treasurer data). Rent = rough estimate.
- Owner phone/email are not in county records (skip tracing is "coming soon"). Letters go to the tax-bill mailing address.
- Photos: satellite view (Esri) + Google Street View link, not listing photos.
