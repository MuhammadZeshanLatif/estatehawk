"""Line a single-take recording up with a voiceover, sentence by sentence.
python3 tools/video/fit.py TAKE.mp4 VOICE.wav OUT.mp4 --t 0,7.2,9.0,... [--music music.wav] [--lead 0.5] [--tail 2.5]

TAKE.mp4 + TAKE.events.json come from record.js (scene calls v.mark(i) where sentence i starts).
--t lists when each sentence starts in the voice. Part i of the video (mark i to mark i+1) is sped up or
slowed down (max 1.25x slower, then the last frame is held) to last exactly as long as sentence i.
Click and zoom sounds are rebuilt at their new times; music is ducked under the voice."""
import argparse, json, os, subprocess, tempfile, sys
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(__file__))
from zoom import sfx_track, SR
from voiceover import dur, run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("take"); ap.add_argument("voice"); ap.add_argument("out")
    ap.add_argument("--t", required=True); ap.add_argument("--music")
    ap.add_argument("--lead", type=float, default=0.5, help="video before the voice starts")
    ap.add_argument("--tail", type=float, default=2.5, help="video after the voice ends")
    a = ap.parse_args()
    ev = json.load(open(a.take.rsplit(".", 1)[0] + ".events.json"))["events"]
    marks = sorted([e for e in ev if e.get("type") == "mark"], key=lambda e: int(e["name"]))
    T = [float(x) for x in a.t.split(",")]
    assert len(marks) == len(T), f"{len(marks)} marks in the take, {len(T)} sentence times"
    take_len, voice_len = dur(a.take), dur(a.voice)
    src = [m["t"] for m in marks] + [take_len]
    dst = [a.lead + x for x in T] + [a.lead + voice_len + a.tail]
    dst[0] = 0.0
    src[0] = max(0.0, src[0] - a.lead)  # a little video before the first sentence
    tmp = tempfile.mkdtemp()
    parts, segs = [], []
    for i in range(len(T)):
        A, L = src[i + 1] - src[i], dst[i + 1] - dst[i]
        f = min(L / A, 1.25) if A > 0 else 1
        hold = max(0.0, L - A * f)
        p = os.path.join(tmp, f"{i}.mp4")
        vf = f"setpts={f:.4f}*(PTS-STARTPTS),fps=30" + (f",tpad=stop_mode=clone:stop_duration={hold + 0.05:.2f}" if hold > 0 else "")
        run("ffmpeg", "-y", "-ss", f"{src[i]:.3f}", "-t", f"{A:.3f}", "-i", a.take, "-vf", vf, "-t", f"{L:.3f}", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", p)
        parts.append(p)
        segs.append((src[i], src[i + 1], dst[i], f))
        print(f"part {i}: {A:5.1f}s -> {L:5.1f}s ({'faster' if f < 1 else 'slower'} x{1 / f:.2f}{', hold %.1fs' % hold if hold > 0 else ''})")
    lst = os.path.join(tmp, "l.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    vid = os.path.join(tmp, "v.mp4")
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid)
    total = dur(vid)

    def remap(t):
        for s0, s1, d0, f in segs:
            if s0 <= t < s1:
                return d0 + (t - s0) * f
        return None
    clicks = []
    for e in ev:
        if e.get("type") in ("click", "focus"):
            nt = remap(e["t"])
            if nt is not None:
                clicks.append({**e, "t": nt})
    sfx = os.path.join(tmp, "sfx.wav")
    wavfile.write(sfx, SR, sfx_track(clicks, total, 1.8))
    ms = int(a.lead * 1000)
    inputs = ["-i", vid, "-i", a.voice, "-i", sfx]
    fc = f"[1:a]adelay={ms}|{ms},apad,atrim=0:{total:.2f},aformat=channel_layouts=stereo,volume=1.7,asplit[v][vs];[2:a]aformat=channel_layouts=stereo,volume=0.8[sx];"
    if a.music:
        inputs += ["-i", a.music]
        fc += (f"[3:a]aloop=loop=-1:size=2e9,atrim=0:{total:.2f},afade=t=in:d=1.5,afade=t=out:st={total - 3:.2f}:d=3,volume=0.30[m];"
               f"[m][vs]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=450[md];[md][v][sx]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95[a]")
    else:
        fc += "[v][sx]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]"
    run("ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out)
    print("ready:", a.out, round(dur(a.out), 1), "s")


if __name__ == "__main__":
    main()
