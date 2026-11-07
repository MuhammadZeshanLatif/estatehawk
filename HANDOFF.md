# EstateHawk handoff (current state)

## 2026-11-08 deal page spacing cleanup (released and visually checked)

- User screenshot showed two large blank areas before a separate research row, plus an old embedded Deal calculator. Root cause: three independent detail columns ended at different heights, while research cards began in a full-width row beneath the tallest column.
- `web/views.js` now places tax-sale rules below property details, comparable sales below deal score, and flood zone below activity notes to balance the detail columns. `web/research.js` loads those cards into their slots and removes the old Deal calculator UI; its backend math remains available to other workflows. The free public calculator at `/deal-profit-calculator` remains the visible calculator. `web/styles.css` removes unused research/calculator grid rules.
- 25 Python tests, JS syntax and diff check passed. First production release `dee5622` removed the duplicate calculator; authenticated visual inspection of the exact user-shown deal found residual left-column space, so follow-up production commit `ba22b4d` reordered the cards. The signed-in Chrome deal tab was reloaded and visually checked after deployment: the former blank areas now contain tax-sale rules (left), comparable sales (middle), and flood zone (right), with no embedded calculator.

## 2026-11-08 free public calculator move (released)

- User disliked the dense deal page. Removed the embedded profit calculator card from `web/views.js` and its app CSS; Offer Draft now links to `/deal-profit-calculator`.
- `app/site.py` serves a public, no-login calculator page, adds header/footer navigation and sitemap entry. `web/deal-profit-page.js` reuses the pure math in `web/deal-profit.js`; `web/deal-profit-page.css` gives it a responsive two-column layout. Inputs are calculated only in the browser, without uploading values. `app/site_ui.py` fixes the mobile menu layout and missing hamburger icon revealed during visual QA.
- Public-route test, 25 Python tests, JS/Python syntax, browser math/reset/mobile-menu/overflow checks passed locally. Desktop and mobile screenshots were inspected. Dev commit `e9d6dba` and production-only cherry-pick `6b63a63` were pushed. Live `/deal-profit-calculator` returned HTTP 200 with the form; new public JS was served, and live app `views.js` no longer contained the embedded card but did contain the free calculator link. Authenticated deal-page visual check remains pending.

## 2026-11-08 deal profit calculator (released)

- Deal detail now has a collapsible Deal profit calculator directly below Offer Draft. It uses the offer as an editable purchase starting point and requires the investor to supply an expected resale value; it does not treat county value as ARV. Repairs, closing, holding, selling percentage, target profit, and an explicit buyer-pays-tax checkbox feed projected profit, return on costs, and maximum offer. Inputs are stored per property and organization in this browser only.
- `web/deal-profit.js` contains the pure calculation; `web/views.js` mounts it; `web/styles.css` styles it. JavaScript syntax, calculation cases, `git diff --check`, and 24 Python tests passed. Dev commit `d819a64` and production-only cherry-pick `e5072c4` were pushed. Production later served `/static/deal-profit.js` with HTTP 200 and the expected calculation code. Authenticated browser visual check remains pending.

## 2026-11-08 homepage interruption fix (local, not yet deployed)

- `web/chat-widget.js`: chat stays closed on page load; greeting appears when the visitor clicks the launcher. `web/chat-widget.css`: the closed launcher has a subtle glow, with reduced-motion support.
- `web/app.js`: the welcome tour no longer opens automatically or redirects first-time users to Deals. The optional **Take a tour** menu action remains available. First-time super-admin setup and email confirmation remain separate flows.
- JavaScript syntax and `git diff --check` passed. Dev commit `9861211` and production-only cherry-pick `b26d2f6` were pushed on 2026-11-08. The first public asset check still served the old chat JS/CSS, so Render completion and live visual behavior remain unverified.

Last updated: 2026-11-07. Read this file first. `E:\Projects\EstateHawk\docs\PROGRESS.md` and `PROJECT_CONTEXT.md` preserve the earlier history; some older “next steps” there were already completed and are not the current task list.

## SEO/blog/traffic work in progress (2026-11-07)

- EstateHawk-specific editorial workflow: `SEO-CONTENT-MASTER-PROMPT.md`, adapted from `E:\Projects\talentrank-app\SEO-CONTENT-MASTER-PROMPT-V2.md`. The new prompt is for US real estate/county-record topics and has no ad monetization or page-coding instructions.
- Blog CMS built locally in `app/content.py`, `app/site.py`, `app/main.py`, `app/db.py`, `web/views2.js`: Admin > Blog can write/save drafts, upload a cover image, preview privately, publish, unpublish by saving as draft, edit and delete. Published articles render at `/blog/{slug}` with canonical/description, BlogPosting and BreadcrumbList data; `/blog` lists them, sitemap includes only published posts. No article has been created or published yet.
- Admin > Traffic funnel groups anonymous first-party browser visitors by detected source and first entry type (blog/other), with landed → signup → email confirmed → paid stages and 7/30/90-day views. A first-party cookie and account link preserve first source through email verification; verified billing transition records paid even without checkout return. Browser blocking/cookie clearing and unknown referrers limit attribution. Existing historical visits cannot be backfilled. Privacy policy now describes this measurement.
- Release `ba95c15` was pushed to `dev` and `main` on 2026-11-07 and Render served the new `/blog` page afterward (HTTP 200, expected title). Live `/static/views2.js` contained Traffic funnel, `/privacy` contained the measurement notice, `/sitemap.xml` was reachable, and unauthenticated `/api/admin/blogs` and `/api/admin/funnel` both returned 401. Empty `/blog` was noindex and set the anonymous first-party visitor cookie. No post was published. Local validation: 20 Python tests passed, Python compile passed, JS syntax passed, `git diff --check` passed. The authenticated admin UI and first real draft/preview were not tested on production; do not claim they were.
- Next: sign in as super admin and check Admin > Blog and Admin > Traffic funnel visually. Create an accurate EstateHawk article draft using the saved prompt, preview it, and publish only with the user's content approval. Confirm its live URL, metadata, cover image and sitemap entry. Traffic data starts after rollout; do not invent or backfill older data.

## Marketing website session fix (2026-11-07)

- User reported that the public website showed Sign in / Start free trial despite an active portal session, and returning to the portal looked like another login. Root cause in code: `app/site.py` always rendered anonymous header CTAs. `app/main.py` now reads the existing signed session for marketing pages, gives signed-in HTML private/no-store caching, redirects signed-in `/login` and `/signup` to `/app#/deals` (or `/check-email` until verified), and redirects `www.getestatehawk.com` GETs to the canonical apex so a different host does not split browser cookies. `web/app.js` adds a same-origin Visit website item in the profile menu. The header shows the first name/photo and Open dashboard, or Confirm email for unverified users.
- Release `03abd56` pushed to `dev` and `main` on 2026-11-07. Render later served `/static/app.js` with Visit website and `/features` with the new signed-in header styling. `https://www.getestatehawk.com/features` returned 301 to the apex; anonymous `/login` still returned 200. A browser with an authenticated session was unavailable for a live visual test of the personalized header, but 24 local Python tests pass, including signed-in header, unverified header, login/signup redirects and private caching. Python compile, `node --check web/app.js` and `git diff --check` passed.

## Seller-intent source research correction (2026-11-07)

- The user wants a source of owner-initiated, genuinely for-sale leads, not an added manual qualification feature. An earlier implementation was committed as `8ed43f4` on `dev` but never sent to `main`; it was reverted by `afcf0ce` at the user's correction. Neither feature is live. Do not reintroduce it without an explicit request.
- Primary-source research: FSBO.com and Zillow FSBO show owner-posted listings; Zillow's listing-quality policy requires the FSBO poster to be the owner, but listing contact may not be a public phone, and both sites prohibit automated scraping for a competing product without permission. Property Leads says its investor leads originate from homeowner form submissions or inbound calls about a cash offer; its site documents exclusive delivery and a webhook route to the purchasing investor's CRM. **Its terms prohibit resale/rebrokering without each consumer's written consent and disclaim ownership/accuracy guarantees. Do not ingest and redistribute these leads to EstateHawk subscribers under a standard buyer account.** A bespoke written data licence or EstateHawk's own direct seller opt-ins would be required. An inquiry is evidence of interest, not a guaranteed sale or perfect identity proof.
- Existing county tax-delinquency records are useful as property distress signals, not confirmed seller-intent leads. Keep that distinction in product claims and any future source evaluation.

## Source of truth and deployment

- Working repository: `E:\Projects\EstateHawk\repo`. The sibling `estatehawk/` and `staging/` directories are older copies, not the deployment source. Do not edit or deploy from them.
- GitHub: `MuhammadZeshanLatif/estatehawk`. Branches `dev` and `main` both include the latest code release `c8259f3` plus documentation updates. Check the remote heads again before work. Render auto-deploys pushes to `main`. Production URL: `https://getestatehawk.com`. Render service: `srv-dbkqj3rbc2fs73a3qjp0`. Database: Neon PostgreSQL via `DATABASE_URL` (never copy its secret into documentation).
- Last release `c8259f3` removed the chatbot’s automatic plan promotion and added a top-right × to the plan dialog while keeping its bottom Close button. The production `app.js` and `chat-widget.js` assets were checked after deploy.
- Earlier releases added email confirmation before dashboard access, password confirmation/show controls, optional signup phone, super-admin user email/phone list and contact-message inbox, safe password reset links, a trial export upgrade dialog, lead navigation/filter/UI fixes, Gemini backup key, and the website assistant. See git history for individual commits.
- Code: FastAPI in `app/`; frontend in `web/` (no build step); tests in `tests/`. `app/main.py` is the API entry point, `app/auth.py` handles sessions, `app/db.py` handles SQLite/Postgres migration, `app/jobs.py` handles county sync, `app/chat.py` handles assistant answers, and `web/app.js`, `web/views.js`, `web/views2.js` contain the product UI.

## Daily sync: latest verified observation

- Hosted daily county sync is the GitHub Actions workflow `.github/workflows/daily-sync.yml`, scheduled for 03:17 UTC / 08:17 Pakistan time, with manual `workflow_dispatch` available. GitHub scheduled starts can be delayed. `python -m app.cli sync` runs counties, contact lookup and digest. A workflow `success` means the command exited successfully; `app/cli.py` can still return success if some counties failed, so inspect the run output or county `last_run` data when per-county certainty matters.
- At about 06:50 Pakistan time on 2026-11-07, there was **no run dated November 7 yet**. Latest observed run was November 6, GitHub Actions run `42205579691`, status `completed`, conclusion `success`, started 10:49 UTC and completed 11:46 UTC. Link: `https://github.com/MuhammadZeshanLatif/estatehawk/actions/runs/42205579691`.
- To check again: use GitHub Actions “Daily county sync” or the read-only GitHub API `https://api.github.com/repos/MuhammadZeshanLatif/estatehawk/actions/workflows/daily-sync.yml/runs?per_page=10`. Convert UTC timestamps to Asia/Karachi. For actual county-level results, inspect the job log or the authenticated Counties screen / `/api/counties` response. Do not claim every county synced from the green workflow badge alone.

## Current product decisions

- User-facing replies to Zeeshan should be in **Roman Urdu**. Product UI and the help assistant use English.
- The chatbot should answer only EstateHawk-related questions, directly and clearly. Do not append sales cards or push a paid plan unless the visitor specifically asks about plan, price, billing or limits. `app/chat.py` contains the prompt and offline fallback. The web widget is `web/chat-widget.js`.
- Never show a user's existing password to an admin. Passwords are hashed; admins can email a one-time reset link. Password signup/change/reset accepts a 15–128 character passphrase and rejects a small set of common weak patterns. Confirm-password and eye controls are present.
- Signup phone is optional. Contact-form and in-app plan questions are saved to `contact_messages`, visible to the super admin in Admin > Contact messages; email delivery remains in place.

## Safe next steps for another AI

1. Read `HANDOFF.md`, then `README.md`, relevant code, and recent git commits. Confirm branch and clean working tree before editing. Read older `E:\Projects\EstateHawk\docs\` notes as history, not as authoritative current status.
2. For a bug, reproduce the specific behavior, fix it in `repo`, run `python -m unittest discover -s tests -p 'test_*.py'`, `python -m compileall -q app`, `node --check` on touched JS, and `git diff --check`.
3. Commit and push `dev`. Before production, fetch/verify `main` and ensure a safe fast-forward. Push the approved release to `main`, then verify live assets or behavior. Do not equate a Git push with a completed Render deployment.
4. Do not place API keys, database URLs, cookies, customer passwords or live property/owner details in this handoff. Ask only for genuinely missing access or a consequential approval.
5. After each meaningful change or release, update this handoff and append a dated note to `E:\Projects\EstateHawk\docs\PROGRESS.md`: what changed, what was tested, what is live, and what remains.
