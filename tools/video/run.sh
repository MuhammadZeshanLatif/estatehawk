#!/usr/bin/env bash
# One command to make the EstateHawk demo video with FICTIONAL demo data (no real owners on screen).
#   bash tools/video/run.sh                       full video, 1920x1080
#   bash tools/video/run.sh --scenes deal,map     only some scenes (see: node tools/video/record.js --list)
#   bash tools/video/run.sh --split               one file per scene
#   bash tools/video/run.sh --mobile              phone-size video
# Any flag is passed to record.js. Output: tools/video/out/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${EH_VIDEO_WORK:-$ROOT/tools/video/out/.server}"
PORT="${EH_VIDEO_PORT:-8199}"
mkdir -p "$WORK"
rm -f "$WORK/demo.db" "$WORK/demo.db-shm" "$WORK/demo.db-wal"

export EH_EMAIL="video@estatehawk.test" EH_PASSWORD="Video-Demo-Pass-2026" EH_BASE="http://127.0.0.1:$PORT"
cd "$ROOT"
[ -f "$WORK/server.pid" ] && kill "$(cat "$WORK/server.pid")" 2>/dev/null || true
SECRET_KEY=video-demo ESTATEHAWK_DB="$WORK/demo.db" ESTATEHAWK_NO_SCHEDULER=1 GEMINI_API_KEY= RENTCAST_API_KEY= \
  python3 -m uvicorn app.main:app --port "$PORT" > "$WORK/server.log" 2>&1 &
echo $! > "$WORK/server.pid"
trap 'kill "$(cat "$WORK/server.pid")" 2>/dev/null || true' EXIT

# stand-in map tiles (the cloud workspace cannot reach server.arcgisonline.com)
TPORT=$((PORT + 1000))
python3 "$ROOT/tools/video/tiles.py" "$TPORT" > "$WORK/tiles.log" 2>&1 &
echo $! > "$WORK/tiles.pid"
export EH_TILES="http://127.0.0.1:$TPORT"
trap 'kill "$(cat "$WORK/server.pid")" "$(cat "$WORK/tiles.pid")" 2>/dev/null || true' EXIT

for i in $(seq 1 40); do curl -sf "$EH_BASE/healthz" >/dev/null && break; sleep 0.5; done
# admin account + fictional demo leads
curl -sf -c "$WORK/c.txt" -H 'Content-Type: application/json' "$EH_BASE/api/auth/setup" \
  -d "{\"email\":\"$EH_EMAIL\",\"password\":\"$EH_PASSWORD\",\"confirm_password\":\"$EH_PASSWORD\",\"name\":\"Alex Morgan\"}" >/dev/null
curl -sf -b "$WORK/c.txt" -X POST "$EH_BASE/api/demo/seed" >/dev/null

NODE_PATH="${NODE_PATH:-$(npm root -g)}" node "$ROOT/tools/video/record.js" "$@"
