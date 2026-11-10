"""Screen Studio style camera: smooth zoom into each click / focus point, then back out.
python3 tools/video/zoom.py RAW.webm EVENTS.json OUT.mp4 [--size 1920x1080] [--zoom 1.8]

EVENTS.json (written by record.js): {"events":[{"t":seconds,"x":px,"y":px,"type":"click"|"focus","hold":seconds,"zoom":1.8}], "w":..,"h":..}
Zoom is gentle (max 1.4x) and slow; nearby events share one shot, so the camera pans between them instead of zooming in and out again.
Frames are upscaled to the output size, so the page fills the whole video."""
import argparse, json, subprocess
import numpy as np, cv2
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SR = 44100


def sfx_track(events, seconds, zoom_default):
    """mouse-click sound on every click, soft whoosh when the camera zooms in"""
    out = np.zeros(int(SR * (seconds + 1)))
    rng = np.random.default_rng(3)
    b, a = butter(2, [2500 / (SR / 2), 9000 / (SR / 2)], "band")
    click = lfilter(b, a, rng.normal(0, 1, int(0.012 * SR))) * np.exp(-np.arange(int(0.012 * SR)) / (0.0025 * SR))
    click2 = click[: int(0.008 * SR)] * 0.6
    L = int(0.55 * SR)
    bw, aw = butter(2, [300 / (SR / 2), 2500 / (SR / 2)], "band")
    whoosh = lfilter(bw, aw, rng.normal(0, 1, L)) * np.sin(np.linspace(0, np.pi, L)) ** 2
    whoosh *= 0.10 / (np.max(np.abs(whoosh)) + 1e-9)
    click *= 0.9 / (np.max(np.abs(click)) + 1e-9)
    click2 *= 0.9 / (np.max(np.abs(click)) + 1e-9)
    last = -99
    for e in sorted(events, key=lambda e: e["t"]):
        if e["t"] - last > MERGE_GAP:  # whoosh only when a new zoom shot starts
            w0 = int(max(0, e["t"] - 0.6) * SR)
            out[w0:w0 + L] += whoosh[: len(out[w0:w0 + L])]
        last = e["t"] + e.get("hold", 1.8)
        if e.get("type") == "click":
            c0 = int((e["t"] + 0.2) * SR)
            out[c0:c0 + len(click)] += click[: len(out[c0:c0 + len(click)])]
            c1 = c0 + int(0.07 * SR)
            out[c1:c1 + len(click2)] += click2[: len(out[c1:c1 + len(click2)])]
    return (np.clip(out, -1, 1) * 32767).astype(np.int16)


def ease(k):
    k = min(1, max(0, k))
    return k * k * (3 - 2 * k)


MAX_ZOOM = 1.4   # never closer than this: calm, professional framing
MERGE_GAP = 3.0  # events closer than this keep the camera in (it pans instead of zooming out and in again)
TAU = 0.45       # seconds; camera smoothing (higher = slower, softer moves)


def soft(z):
    """requested zoom (1.4..2.2 in scene files) -> gentle zoom 1.15..1.4"""
    return 1 + min(MAX_ZOOM - 1, (max(1.0, z) - 1) * 0.45)


def plan(events, default_zoom):
    """camera shots: one per group of nearby events; each event inside a group is a pan target"""
    shots = []
    for e in events:
        z = soft(e.get("zoom", default_zoom))
        s0, s1 = e["t"] - 0.5, e["t"] + e.get("hold", 1.8)
        if shots and s0 - shots[-1]["end"] < MERGE_GAP:
            shots[-1]["end"] = max(shots[-1]["end"], s1)
            shots[-1]["pts"].append((s0, e["x"], e["y"], z))
        else:
            shots.append({"start": s0, "end": s1, "pts": [(s0, e["x"], e["y"], z)]})
    return shots


def target(shots, t, W, H):
    for sh in shots:
        if sh["start"] <= t <= sh["end"]:
            p = [q for q in sh["pts"] if q[0] <= t][-1] if any(q[0] <= t for q in sh["pts"]) else sh["pts"][0]
            return p[3], p[1], p[2]
    return 1.0, W / 2, H / 2


class Camera:
    """critically damped follow: two cascaded smoothing stages give slow, eased starts and stops"""
    def __init__(self, W, H, fps):
        self.a = 1 - np.exp(-1 / (fps * TAU / 2))
        self.s1 = np.array([1.0, W / 2, H / 2]); self.s2 = self.s1.copy()

    def step(self, tgt):
        self.s1 += (np.array(tgt) - self.s1) * self.a
        self.s2 += (self.s1 - self.s2) * self.a
        return self.s2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw"); ap.add_argument("events"); ap.add_argument("out")
    ap.add_argument("--size", default="1920x1080"); ap.add_argument("--zoom", type=float, default=1.8)
    a = ap.parse_args()
    OW, OH = map(int, a.size.split("x"))
    ev = json.load(open(a.events))
    events = sorted([e for e in ev.get("events", []) if e.get("type") in ("click", "focus")], key=lambda e: e["t"])
    cap = cv2.VideoCapture(a.raw)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    if fps > 60 or fps < 10:
        fps = 25
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    sfx = a.out.rsplit(".", 1)[0] + ".sfx.wav"
    wavfile.write(sfx, SR, sfx_track(events, max(frames / fps, (events[-1]["t"] + 3) if events else 1), a.zoom))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(fps), "-i", "-",
                           "-i", sfx, "-map", "0:v", "-map", "1:a", "-shortest",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    shots = plan(events, a.zoom)
    cam = Camera(W, H, fps)
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        t = i / fps
        z, cx, cy = cam.step(target(shots, t + 0.35, W, H))
        cw, ch = W / z, H / z
        x0 = min(max(cx - cw / 2, 0), W - cw)
        y0 = min(max(cy - ch / 2, 0), H - ch)
        M = np.float32([[OW / cw, 0, -x0 * OW / cw], [0, OH / ch, -y0 * OH / ch]])
        ff.stdin.write(cv2.warpAffine(f, M, (OW, OH), flags=cv2.INTER_CUBIC).tobytes())
        i += 1
    ff.stdin.close()
    ff.wait()
    print("zoomed:", a.out, i, "frames")


if __name__ == "__main__":
    main()
