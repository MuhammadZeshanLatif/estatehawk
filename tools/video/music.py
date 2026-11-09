"""Light, hopeful background music for EstateHawk videos (generated, no copyright issues).
python3 tools/video/music.py OUT.wav [seconds]
Soft electric-piano chords (C - G - Am - F), a gentle pad and a quiet pulse, with fade in and out."""
import sys
import numpy as np
from scipy.io import wavfile

SR = 44100
BPM = 92
BEAT = 60 / BPM
CHORDS = [[60, 64, 67, 72], [55, 62, 67, 71], [57, 60, 64, 69], [53, 60, 65, 69]]  # C, G, Am, F (MIDI)
BASS = [36, 43, 45, 41]


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def epiano(f, dur):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 300))
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 4) + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 6)
    return tone * env


def pad(f, dur):
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return sum(np.sin(2 * np.pi * f * d * t) for d in (0.997, 1.0, 1.003)) / 3 * env


def make(seconds):
    n = int(SR * (seconds + 2))
    out = np.zeros(n)
    bar = 4 * BEAT
    i = 0
    while i * bar < seconds + 1:
        c, b = CHORDS[i % 4], BASS[i % 4]
        s = int(i * bar * SR)
        for k, beat in enumerate((0, 1.5, 2, 3)):  # light syncopated piano pattern
            st = s + int(beat * BEAT * SR)
            for m in (c if k == 0 else c[1:]):
                w = epiano(hz(m), 2.5) * (0.10 if k == 0 else 0.06)
                out[st:st + len(w)] += w[:max(0, n - st)]
        p = sum(pad(hz(m - 12), bar + 0.6) for m in c[:3]) * 0.05
        out[s:s + len(p)] += p[:max(0, n - s)]
        bw = epiano(hz(b), bar) * 0.12
        out[s:s + len(bw)] += bw[:max(0, n - s)]
        for beat in range(4):  # soft shaker pulse
            st = s + int((beat + 0.5) * BEAT * SR)
            L = int(0.05 * SR)
            if st + L < n:
                out[st:st + L] += np.random.default_rng(i * 4 + beat).normal(0, 1, L) * np.exp(-np.arange(L) / (0.012 * SR)) * 0.012
        i += 1
    out = out[:int(SR * seconds)]
    # simple room: a few decaying echoes
    for d, g in ((0.031, 0.25), (0.047, 0.18), (0.083, 0.12), (0.12, 0.08)):
        k = int(d * SR)
        out[k:] += out[:-k] * g
    fade = int(SR * 1.5)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade * 2:] *= np.linspace(1, 0, fade * 2)
    out /= np.max(np.abs(out)) + 1e-9
    st = (np.stack([out, np.roll(out, int(0.012 * SR))], 1) * 0.8 * 32767).astype(np.int16)
    return st


if __name__ == "__main__":
    wavfile.write(sys.argv[1], SR, make(float(sys.argv[2]) if len(sys.argv) > 2 else 60))
