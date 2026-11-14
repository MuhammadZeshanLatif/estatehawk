# EstateHawk: full project and marketing handoff (2026-11-14)

Read this first, then `HANDOFF.md` (product, code, deploy) and `CLAUDE.md`.
Reply to Zeeshan in **Roman Urdu**, short bullets, no icons, no em-dashes. All marketing content is **English for US investors in Ohio and Texas** (not Pakistan).

## 1. What EstateHawk is
- SaaS at getestatehawk.com: tax-delinquent property leads from official county records, Ohio and Texas, updated daily. Shows owner, years behind, amount owed, tax history, deal score, map, same-day alerts, owner contact lookup, deal profit calculator, offer draft. 14-day free trial.
- Repo: `MuhammadZeshanLatif/estatehawk`. Local path on his PC: `E:\Projects\EstateHawk\repo`. FastAPI `app/`, frontend `web/` (no build), tests `tests/`, Chrome extension in `extension/`. Render deploys `main`; work goes to `dev`, he merges.
- Commits: author `Muhammad Zeeshan Latif <zeeshanlatif.tech@gmail.com>` (use `--author`), committer stays Claude.
- Daily county sync: GitHub Actions `.github/workflows/daily-sync.yml`.
- SEO: `SEO-AUDIT-2026-11-09.md`, `SEO-BLOG-KEYWORDS-2026-11-09.md`, `SEO-CONTENT-MASTER-PROMPT.md`. Search Console is verified. Blog CMS is in Admin > Blog.
- Footer now has LinkedIn + Facebook icons and Organization `sameAs`. To add a channel, edit `SOCIAL` in `app/site.py` (commit 39c5d10 on dev, needs merge to main).

## 2. Video tooling (Playwright)
- `tools/video/` records product walkthroughs: `bash tools/video/run.sh`. Feature scene library `tools/video/library.js` (one scene per feature). See `tools/video/README.md`. Rule: every user-visible feature gets a scene.
- Short ads: `tools/video/shorts/` (ad.js, tour.js, pitch-urdu.js, story-ad.js = product part of story ads, banner hidden).
- Product footage used in story ads: `tools/video/out/story/estatehawk-demo.mp4` (marks: 2.85 stats, 11.07 lead detail, 20.41 map, ~25.5 alerts, card after 28.57). Music: `tools/video/out/music.wav`.

## 3. Story ads (cinematic, AI clips + voice + product footage)
Pipeline (`tools/video/shorts/story/`):
1. Clips: Google Flow (labs.google/fx/tools/flow, PRO account zeeshanlatif.tech), project `flow.google.com/project/24e39a32-4faf-43a9-931b-39012e1ac99d`. Settings: Video, 16:9, Omni 1.1 Flash, 720p, 8 s, x1 = 12 credits. Credits reset Nov 20 (almost none left now). Every prompt ends with: `Cinematic, shot on 35mm, shallow depth of field, soft film grain, photorealistic, 16:9. No on-screen text, no captions, no logos, no readable writing. No dialogue, no speech.` Download 720p (download icon, then 720p).
2. Voice: Google AI Studio > Generate speech, voice Charon (narrator), Aoede (female), Algenib (old man), Orus (deadpan). Run with ctrl+Enter, then download.
3. Files land in his Downloads (`C:\Users\Zeeshan\Downloads`); clips folders `E:\Projects\EstateHawk\clips`, `clips3`.
4. `node cards.js OUTDIR` renders end cards; `python3 voice_times.py VOICE.wav` gives sentence start times; write a spec JSON; `python3 build.py SPEC.json` assembles (clip slots, split screen, product footage, card, ducked music, loudnorm).
5. Deliver full + `-720.mp4` (under 10 MB) + 9:16 Short (blurred background, logo/URL overlay) into `E:\Projects\EstateHawk\video`.
Scripts and plans: `story-ad.md` (Dan, split), `story-ad-2.md` (mailbox, veteran, county), `story-ad-3.md` (9 ads), `story-ad-4.md` (2 new ads, NOT built yet).

Built (in `E:\Projects\EstateHawk\video`): dan, split, mailbox, veteran, county, trucker, fatherson, partner, calls, weekend, years, driving, vlog, firstdeal (14 ads, each with -720 copy). 9:16 Shorts of all 14 were made in the cloud session but only the Dan short was sent; regenerate from the full files if needed. YouTube banner `estatehawk-youtube-banner.png` and cover `estatehawk-cover.png` (1584x396) were made the same way (green brand, logo from `web/icon.svg`).

**Pending, do this first:** build `story-ad-4.md` ads ("The night before the auction" ~55 s, "2 AM" ~25 s). The 7 Flow clips and 2 voice wavs (Nov 14) are already in Downloads; end cards `card-auction.png` and `card-2am.png` are in `cards.js`. Build, then schedule.

## 4. Posting schedule (7:30 PM PKT daily)
LinkedIn (his personal profile, captions tag @EstateHawk, UTM `utm_source=linkedin&utm_medium=social&utm_campaign=story_<name>`) and EstateHawk Facebook page as Reels (UTM `utm_source=facebook&utm_medium=page`), all already scheduled:
- Nov 11 split, Nov 12 Dan (posted), Nov 13 mailbox, 14 veteran, 15 county, 16 trucker, 17 fatherson, 18 partner, 19 calls, 20 weekend, 21 years, 22 driving, 23 vlog, 24 firstdeal.
- Next free slots: Nov 25 onward (auction, 2 AM).
- Uploading in Chrome only works for files attached in chat (file_upload refuses other paths). Meta composer: patch `HTMLInputElement.prototype.click` to expose the file input, then `file_upload`; schedule via Share step > Schedule > date picker > hour/minute. LinkedIn: Video button, Next, caption, type `@EstateHawk` and pick the company, clock icon, date `MM/DD/YYYY`, time `7:30 PM`, Confirm, Schedule.
- His personal FB profile cannot be scheduled; posts there are manual.

## 5. Accounts and channels
- LinkedIn company page: linkedin.com/company/getestatehawk. Facebook page: facebook.com/profile.php?id=61595889045774 (0 followers so far).
- BiggerPockets: profile biggerpockets.com/users/zeeshanl filled (Technology, founder bio, Wholesale+Flip, LinkedIn link). Intro post in New Member Introductions was pending moderation. Forum rules forbid self-promotion and AI-written posts; he writes replies himself.
- YouTube: EstateHawk channel NOT created yet (@EstateHawk is taken by someone else; use @getestatehawk). He must click Create himself. Then add description, links, banner, upload Shorts.
- Instagram: not created; he creates it, then link to the FB page.
- Never create accounts, enter passwords/OTP/card numbers, or click paid upgrades (Flow, Neon, BiggerPockets Pro). Render stays Free.

## 6. Outreach
- LinkedIn: 15 to 20 Ohio/Texas wholesalers a day, message includes getestatehawk.com and "follow EstateHawk". InMail credits nearly used; prefer invites with a note (max 300 chars). Nov 11 batch sent (10 InMails, 5 invites).
- Facebook DMs hit a limit after 2.
- Backlink list reviewed (ghulamaliseo.com/backlinks): start with AlternativeTo, SaaSHub, G2, Capterra, GoodFirms, TrustRadius, SourceForge, Product Hunt, then launch directories. He creates the accounts.
