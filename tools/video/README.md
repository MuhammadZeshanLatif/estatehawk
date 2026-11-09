# EstateHawk videos (Playwright)

Everything needed to make product videos without reading the app again.
Fictional demo data only ("Alex Morgan", made-up owners), so videos are safe to post.

## Files
- `library.js`: **one scene per feature** (60 scenes: website, leads, deal page, map, alerts, auctions, counties, outreach, reports, settings, plans, admin). Every scene reaches its page by clicking, so any list of scenes plays as one continuous take.
- `scenes.js`: older 14-scene overview with captions.
- `shorts/`: finished short videos (scene lists written for one voiceover).
- `record.js`: Playwright engine (cursor with click ripple, captions, title cards, timing, recording).
- `zoom.py`: Screen Studio style camera: zooms into every click and `focus()`, then back out. Output 1080p.
- `music.py`: generated background music (no copyright).
- `voiceover.py`: joins clips with a voice file and music (voice split per clip, music ducked under voice).
- `run.sh`: starts a private server with demo data, runs record.js, stops the server.

## Make a video
```bash
bash tools/video/run.sh --file library.js --list                           # all feature scenes
bash tools/video/run.sh --file library.js --scenes home,open-dashboard,deals,deal-open,deal-tax,map,outro-card
bash tools/video/run.sh --file library.js --scenes deal-calculator --split   # one mp4 per scene
bash tools/video/run.sh --file library.js --scenes ... --no-captions        # for voiceover videos
bash tools/video/run.sh --file library.js --scenes ... --mobile             # phone size
```
Output: `tools/video/out/`. Without `--split`, the chosen scenes play in one take in the given order.

## Voiceover
1. Write the script (one sentence per scene).
2. Google AI Studio > Generate speech: voice "Koda", Style: "A warm, friendly young Pakistani founder speaking fluent English with a light, natural Pakistani accent. Conversational and human...". Download the WAV and put it in `E:\Projects\EstateHawk` (the cloud workspace cannot reach Google's API).
3. `python3 tools/video/music.py tools/video/out/music.wav 60`
4. `python3 tools/video/voiceover.py VOICE.wav OUT.mp4 CLIP1.mp4 CLIP2.mp4 ... --music tools/video/out/music.wav` (`--marks` for exact sentence boundaries).

## Adding a feature
Add a scene to `library.js` (id, title, caption, run). Helpers: `nav(route)` clicks the sidebar, `click(sel, hold, zoom)`, `focus(sel, seconds, zoom)`, `type`, `scroll`, `scrollTo`, `card`, `wait`. A missing selector is skipped with a log line, never breaks the video.

## Known limit
Map tiles and satellite photos come from `server.arcgisonline.com`, which the cloud workspace blocks. Add that domain in claude.ai Settings > Capabilities to see them in videos.
