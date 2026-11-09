"""Join scene clips with a voiceover and background music.
python3 tools/video/voiceover.py VOICE_AUDIO OUT.mp4 CLIP1 CLIP2 ... [--music music.wav] [--skip 1.0]

The voice is split at its longest pauses into as many parts as there are clips (one sentence per scene).
Each clip is trimmed (or its last frame held) to its part's length, then everything is joined and
the music is mixed under the voice (quieter while he speaks)."""
import argparse, re, subprocess, tempfile, os


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True)


def dur(f):
    return float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f).stdout)


def pauses(voice):
    err = subprocess.run(["ffmpeg", "-i", voice, "-af", "silencedetect=noise=-35dB:d=0.25", "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return [(s, e) for s, e in zip(st, en)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice"); ap.add_argument("out"); ap.add_argument("clips", nargs="+")
    ap.add_argument("--music"); ap.add_argument("--skip", type=float, default=1.0, help="seconds cut from the start of each clip (page loading)")
    ap.add_argument("--marks", help="scene boundaries in seconds of the voice, comma separated (overrides pause detection)")
    ap.add_argument("--lead", type=float, default=0.6, help="silence before the voice starts")
    a = ap.parse_args()
    total = dur(a.voice)
    ps = [p for p in pauses(a.voice) if 0.5 < p[0] < total - 0.5]
    cuts = sorted(sorted(ps, key=lambda p: p[1] - p[0], reverse=True)[:len(a.clips) - 1])
    marks = [0.0] + ([float(x) for x in a.marks.split(",")] if a.marks else [(s + e) / 2 for s, e in cuts]) + [total]
    lens = [marks[i + 1] - marks[i] for i in range(len(a.clips))]
    lens[0] += a.lead
    lens[-1] += 1.5  # let the end card breathe
    print("scene lengths:", [round(x, 1) for x in lens])
    tmp = tempfile.mkdtemp()
    parts = []
    for i, (c, L) in enumerate(zip(a.clips, lens)):
        p = os.path.join(tmp, f"{i}.mp4")
        have = dur(c) - a.skip
        vf = "fps=30,scale=1920:1080,setsar=1" + (f",tpad=stop_mode=clone:stop_duration={L - have + 0.1:.2f}" if have < L else "")
        run("ffmpeg", "-y", "-ss", str(a.skip), "-i", c, "-t", f"{L:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", p)
        parts.append(p)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    joined = os.path.join(tmp, "joined.mp4")
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined)
    T = dur(joined)
    ms = int(a.lead * 1000)
    if a.music:
        fc = (f"[1:a]adelay={ms}|{ms},apad,atrim=0:{T:.2f},aformat=channel_layouts=stereo,volume=1.6[v];"
              f"[2:a]atrim=0:{T:.2f},afade=t=out:st={T - 2.5:.2f}:d=2.5,volume=0.32[m];"
              f"[m][v]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];"
              f"[md][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
        run("ffmpeg", "-y", "-i", joined, "-i", a.voice, "-i", a.music, "-filter_complex", fc.replace("[m][v]sidechain", "[m][vs]sidechain").replace("volume=1.6[v];", "volume=1.6,asplit[v][vs];"),
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out)
    else:
        run("ffmpeg", "-y", "-i", joined, "-i", a.voice, "-filter_complex", f"[1:a]adelay={ms}|{ms},apad,atrim=0:{T:.2f}[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out)
    print("ready:", a.out, round(dur(a.out), 1), "s")


if __name__ == "__main__":
    main()
