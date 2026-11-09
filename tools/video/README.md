# EstateHawk demo video (Playwright)

One command records a narrated-caption walkthrough of the product with **fictional demo data** (no real owners on screen).

```bash
bash tools/video/run.sh                        # full video -> tools/video/out/estatehawk-demo.mp4
bash tools/video/run.sh --scenes deal,map      # only some scenes
bash tools/video/run.sh --split                # one mp4 per scene (for reels/shorts)
bash tools/video/run.sh --mobile               # phone-size video
node tools/video/record.js --list              # list scene ids
```

`run.sh` starts a private server on port 8199 with a fresh database, creates a demo admin ("Alex Morgan"), loads demo leads, records, converts to mp4 (ffmpeg) and stops the server. Needs Python deps from `requirements.txt`, Node with Playwright, and ffmpeg (optional; without it you get .webm).

## Adding a new feature to the video
Add one object to `scenes.js` (id, title, run). Helpers: `go`, `caption`, `click`, `type`, `hover`, `scroll`, `scrollTo`, `wait`, `card`, `topLeadId`, `page`. A missing selector is skipped with a log line, so an old scene never breaks the whole video. Keep the scene list in product order.

Current scenes: intro, home, deals, deal, offer, map, auctions, alerts, outreach, counties, reports, calculator, pricing, outro.

## Recording the live site
`EH_EMAIL=... EH_PASSWORD=... node tools/video/record.js --base https://getestatehawk.com` works, but the live site shows real owner names. Use the local demo for anything public.

## Voiceover shorts
1. Scenes for a short live in `tools/video/shorts/` (one scene per voice sentence). Record: `bash tools/video/run.sh --file shorts/tour.js --split --no-captions`
2. Voice: Google AI Studio > Generate speech (voice "Koda", custom style: warm young Pakistani founder, fluent English, light accent). Script: `tools/video/shorts/tour-voice.txt`. Separate sentences with " ... " so the pauses are clear.
3. Music: `python3 tools/video/music.py tools/video/out/music.wav 60` (generated, copyright-free) or any track you own.
4. Join: `python3 tools/video/voiceover.py VOICE.wav tools/video/out/tour.mp4 tools/video/out/estatehawk-t*.mp4 --music tools/video/out/music.wav`
   It splits the voice at its longest pauses (one part per clip), trims each clip to its part and mixes the music under the voice.
