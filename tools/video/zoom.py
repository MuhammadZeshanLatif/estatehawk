"""Screen Studio style camera: smooth zoom into each click / focus point, then back out.
python3 tools/video/zoom.py RAW.webm EVENTS.json OUT.mp4 [--size 1920x1080] [--zoom 1.8]

EVENTS.json (written by record.js): {"events":[{"t":seconds,"x":px,"y":px,"type":"click"|"focus","hold":seconds,"zoom":1.8}], "w":..,"h":..}
The camera eases in over 0.6 s, holds on the point (following the cursor a little), and eases out over 0.7 s.
Frames are upscaled to the output size, so the page fills the whole video."""
import argparse, json, subprocess
import numpy as np, cv2


def ease(k):
    k = min(1, max(0, k))
    return k * k * (3 - 2 * k)


def camera(events, t, W, H, default_zoom):
    """zoom and centre at time t"""
    z, cx, cy = 1.0, W / 2, H / 2
    for e in events:
        zin, hold, zout = 0.6, e.get("hold", 1.8), 0.7
        s = e["t"] - 0.35
        if s <= t <= s + zin + hold + zout:
            if t < s + zin:
                k = ease((t - s) / zin)
            elif t < s + zin + hold:
                k = 1
            else:
                k = 1 - ease((t - s - zin - hold) / zout)
            ez = e.get("zoom", default_zoom)
            nz = 1 + (ez - 1) * k
            if nz > z:
                z = nz
                cx = W / 2 + (e["x"] - W / 2) * k
                cy = H / 2 + (e["y"] - H / 2) * k
    return z, cx, cy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw"); ap.add_argument("events"); ap.add_argument("out")
    ap.add_argument("--size", default="1920x1080"); ap.add_argument("--zoom", type=float, default=1.8)
    a = ap.parse_args()
    OW, OH = map(int, a.size.split("x"))
    ev = json.load(open(a.events))
    events = sorted(ev.get("events", []), key=lambda e: e["t"])
    cap = cv2.VideoCapture(a.raw)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    if fps > 60 or fps < 10:
        fps = 25
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        t = i / fps
        z, cx, cy = camera(events, t, W, H, a.zoom)
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
