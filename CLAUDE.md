# EstateHawk notes for AI assistants

- Read `HANDOFF.md` first (current state, release steps, safety rules).
- Videos: `tools/video/README.md`. Feature scene library: `tools/video/library.js` (one scene per feature, click-driven, chainable).
  Make a video: `bash tools/video/run.sh --file library.js --scenes a,b,c`. Do not rewrite the recorder or re-read the app for a new video.
  When a user-visible feature is added or changed, add or update its scene in `library.js` in the same change.
