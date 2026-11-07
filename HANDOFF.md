# EstateHawk handoff (current state)

Last updated: 2026-11-07. Read this file first. `E:\Projects\EstateHawk\docs\PROGRESS.md` and `PROJECT_CONTEXT.md` preserve the earlier history; some older “next steps” there were already completed and are not the current task list.

## SEO/blog/traffic work in progress (2026-11-07)

- EstateHawk-specific editorial workflow: `SEO-CONTENT-MASTER-PROMPT.md`, adapted from `E:\Projects\talentrank-app\SEO-CONTENT-MASTER-PROMPT-V2.md`. The new prompt is for US real estate/county-record topics and has no ad monetization or page-coding instructions.
- Blog CMS built locally in `app/content.py`, `app/site.py`, `app/main.py`, `app/db.py`, `web/views2.js`: Admin > Blog can write/save drafts, upload a cover image, preview privately, publish, unpublish by saving as draft, edit and delete. Published articles render at `/blog/{slug}` with canonical/description, BlogPosting and BreadcrumbList data; `/blog` lists them, sitemap includes only published posts. No article has been created or published yet.
- Admin > Traffic funnel groups anonymous first-party browser visitors by detected source and first entry type (blog/other), with landed → signup → email confirmed → paid stages and 7/30/90-day views. A first-party cookie and account link preserve first source through email verification; verified billing transition records paid even without checkout return. Browser blocking/cookie clearing and unknown referrers limit attribution. Existing historical visits cannot be backfilled. Privacy policy now describes this measurement.
- Release `ba95c15` was pushed to `dev` and `main` on 2026-11-07 and Render served the new `/blog` page afterward (HTTP 200, expected title). Live `/static/views2.js` contained Traffic funnel, `/privacy` contained the measurement notice, `/sitemap.xml` was reachable, and unauthenticated `/api/admin/blogs` and `/api/admin/funnel` both returned 401. Empty `/blog` was noindex and set the anonymous first-party visitor cookie. No post was published. Local validation: 20 Python tests passed, Python compile passed, JS syntax passed, `git diff --check` passed. The authenticated admin UI and first real draft/preview were not tested on production; do not claim they were.
- Next: sign in as super admin and check Admin > Blog and Admin > Traffic funnel visually. Create an accurate EstateHawk article draft using the saved prompt, preview it, and publish only with the user's content approval. Confirm its live URL, metadata, cover image and sitemap entry. Traffic data starts after rollout; do not invent or backfill older data.

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
