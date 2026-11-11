"""Assemble a story ad from AI clips, the Playwright product recording, end cards, voice and music.
python3 build.py SPEC.json

SPEC: {"out": "ad.mp4", "voice": "voice.wav", "music": "music.wav", "length": 66.5,
       "shots": [{"at": 0, "to": 10.4, "src": "clip.mp4", "in": 0},                   # one full-frame shot
                 {"at": 30.5, "to": 36.5, "src": "product.mp4", "in": 2.85, "out": 11.07},  # squeezed to fit (speed up)
                 {"at": 10, "to": 14, "left": "a.mp4", "right": "b.mp4", "overlay": "labels.png"},  # split screen
                 {"at": 58.4, "to": 66.5, "image": "card.png"}]}
A clip shorter than its slot plays a bit slower (max 1.35x longer), then holds its last frame.
Clip sound stays in quietly (room tone), the voice sits on top, music is ducked under the voice."""
import json, os, subprocess, sys, tempfile

W, H, FPS = 1920, 1080, 30


def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).decode())


def has_audio(f):
    return bool(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", f]).strip())


def fit(src, t_in, t_out, D):
    """video filter + audio filter that turn src[t_in:t_out] into exactly D seconds"""
    L = t_out - t_in
    k = D / L
    if k > 1.35:  # slow down a little, then hold the last frame
        k2 = 1.35
        hold = D - L * k2
    else:
        k2, hold = k, 0
    v = f"trim={t_in}:{t_out},setpts=(PTS-STARTPTS)*{k2:.5f},fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if hold > 0:
        v += f",tpad=stop_mode=clone:stop_duration={hold:.3f}"
    v += f",trim=0:{D:.3f},setpts=PTS-STARTPTS,setsar=1"
    # audio: keep it unstretched (room tone), pad or cut to D
    a = f"atrim={t_in}:{min(t_out, t_in + D)},asetpts=PTS-STARTPTS,apad=whole_dur={D:.3f},atrim=0:{D:.3f}"
    return v, a


def segment(s, tmp, i):
    D = s["to"] - s["at"]
    out = os.path.join(tmp, f"s{i:02d}.mp4")
    if "image" in s:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", f"{D:.3f}", "-i", s["image"], "-f", "lavfi", "-t", f"{D:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
               "-vf", f"scale={W}:{H},fps={FPS},setsar=1,zoompan=z='1+0.00025*on':d=1:s={W}x{H}:fps={FPS}", "-map", "0:v", "-map", "1:a"]
    elif "left" in s:
        parts, filt = [], []
        for j, side in enumerate(("left", "right")):
            f = s[side]; t_in = s.get("in", 0); t_out = s.get("out", dur(f))
            v, a = fit(f, t_in, t_out, D)
            filt.append(f"[{j}:v]{v},crop={W // 2}:{H}:{W // 4}:0[{side}]")
            parts += ["-i", f]
        filt.append(f"[left][right]hstack=inputs=2[st];[st][2:v]overlay=0:0[v]")
        filt.append(f"[0:a]atrim=0:{D:.3f},asetpts=PTS-STARTPTS,apad=whole_dur={D:.3f}[a0];[1:a]atrim=0:{D:.3f},asetpts=PTS-STARTPTS,apad=whole_dur={D:.3f}[a1];[a0][a1]amix=inputs=2:normalize=0[a]")
        cmd = ["ffmpeg", "-y", "-loglevel", "error"] + parts + ["-i", s["overlay"], "-filter_complex", ";".join(filt), "-map", "[v]", "-map", "[a]"]
    else:
        f = s["src"]; t_in = s.get("in", 0); t_out = s.get("out", dur(f))
        v, a = fit(f, t_in, t_out, D)
        if has_audio(f):
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", f, "-filter_complex", f"[0:v]{v}[v];[0:a]{a},aresample=48000,aformat=channel_layouts=stereo[a]", "-map", "[v]", "-map", "[a]"]
        else:
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", f, "-f", "lavfi", "-t", f"{D:.3f}", "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex", f"[0:v]{v}[v]", "-map", "[v]", "-map", "1:a"]
    cmd += ["-t", f"{D:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-ar", "48000", "-ac", "2", out]
    subprocess.run(cmd, check=True)
    return out


def main():
    spec = json.load(open(sys.argv[1]))
    tmp = tempfile.mkdtemp(prefix="story-")
    segs = [segment(s, tmp, i) for i, s in enumerate(spec["shots"])]
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in segs))
    joined = os.path.join(tmp, "joined.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined], check=True)
    T = spec.get("length") or dur(joined)
    room = spec.get("room", 0.22)
    fade = f"fade=t=in:st=0:d=0.6,fade=t=out:st={T - 1.0:.2f}:d=1.0"
    fc = (f"[0:v]{fade}[v];"
          f"[0:a]volume={room}[room];"
          f"[1:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(spec.get('voice_at', 0) * 1000)}|{int(spec.get('voice_at', 0) * 1000)},volume=1.0,asplit=2[vo][key];"
          f"[2:a]aresample=48000,aformat=channel_layouts=stereo,volume={spec.get('music_vol', 0.30)}[mu];"
          f"[mu][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[mud];"
          f"[room][vo][mud]amix=inputs=3:normalize=0,afade=t=out:st={T - 1.2:.2f}:d=1.2,loudnorm=I=-15:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined, "-i", spec["voice"], "-stream_loop", "-1", "-i", spec["music"],
                    "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{T:.3f}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", spec["out"]], check=True)
    print("ad:", spec["out"], f"{T:.1f}s")


if __name__ == "__main__":
    main()
