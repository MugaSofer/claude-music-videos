"""Signal v3: score.json -> signal_v3.wav (mastered).

The Morse voices (unchanged in rhythm): the lighthouse a warm horn (left), the boat a clear bell voice
(right; synth, as Muga prefers), GOODNIGHT both. Around them, the composed arrangement from compose.py:
piano-2 synth piano for bass, comping and the sea's answers, a soft sub under the bass, a pad following
the bar chords, synthesized shaker / kick / rim, and the sea.
"""
import json
import sys
import time

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfilt

from compose import CH, ROOTS, UNIT  # noqa: E402  (before the path inserts: piece 2 also has a compose.py)

sys.path.insert(0, "../02-player-piano")
from piano import SR, render, room  # noqa: E402
sys.path.insert(0, "../..")
from master import master  # noqa: E402

T0 = time.time()
OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\11\signal_v3.wav"
S = json.load(open("score.json"))
TOTAL = S["total"] + 3
N = int(TOTAL * SR)
hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)
rng = np.random.default_rng(11)
t = np.arange(N) / SR


def adsr(n, a, r):
    e = np.ones(n)
    ka, kr = min(int(a * SR), n), min(int(r * SR), n)
    e[:ka] = np.linspace(0, 1, ka)
    if kr:
        e[-kr:] *= np.linspace(1, 0, kr)
    return e


def horn(m, dur):
    n = int((dur + 0.08) * SR)
    tt = np.arange(n) / SR
    f = hz(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.2 * tt) * np.clip(tt / 0.25, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = sum(np.sin(k * ph) / k ** 1.3 for k in range(1, 7))
    y = sosfilt(butter(2, 1100, "low", fs=SR, output="sos"), saw * 0.6 + 0.25 * np.sin(ph / 2))
    return y * adsr(n, 0.015, 0.06)


def bell(m, dur):
    n = int((dur + 0.8) * SR)
    tt = np.arange(n) / SR
    k = int((dur + 0.04) * SR)
    hold = np.zeros(n)
    hold[:k] = adsr(k, 0.004, 0.04)
    tail = np.exp(-np.maximum(tt - dur, 0) / 0.3) * (tt >= dur)
    f = hz(m)
    y = (np.sin(2 * np.pi * f * tt) + 0.18 * np.sin(4 * np.pi * f * tt)) * (hold + 0.35 * tail)
    y += 0.3 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt / 0.15) + 0.1 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt / 0.05)
    return y * 0.7


L = np.zeros(N)
R = np.zeros(N)


def add(x, t0, pan, g=1.0, buf=None):
    i = int(t0 * SR)
    j = min(i + len(x), N)
    if j <= i:
        return
    if buf is not None:
        buf[i:j] += x[:j - i] * g
        return
    L[i:j] += x[:j - i] * np.cos(pan * np.pi / 2) * g
    R[i:j] += x[:j - i] * np.sin(pan * np.pi / 2) * g


for e in S["events"]:
    if e["sender"] in ("light", "both"):
        add(horn(e["midi"], e["dur"]), e["t"], 0.3, 0.42)
    if e["sender"] == "boat":
        add(bell(e["midi"], e["dur"]), e["t"], 0.7, 0.45)
    if e["sender"] == "both":
        add(bell(e["midi"] + 12, e["dur"]), e["t"], 0.7, 0.4)
voices = np.stack([L, R], 1).copy()
print(f"{time.time() - T0:5.1f}s voices", flush=True)

# the piano: bass (low), comping, the sea's answers; one render each so they can be balanced
A = S["acc"]
def piano_part(names, gain):
    ev = sorted((a["t"], a["midi"], a["vel"], a["dur"]) for a in A if a["voice"] in names)
    if not ev:
        return np.zeros((N, 2))
    x = render(ev, TOTAL, metal=0.25)[:N]
    x = np.pad(x, ((0, N - len(x)), (0, 0))) if x.ndim == 2 else np.pad(np.stack([x, x], 1), ((0, N - len(x)), (0, 0)))
    return x / (np.abs(x).max() + 1e-9) * gain
bass = piano_part({"bass"}, 0.55)
comp = piano_part({"comp"}, 0.38)
answer = piano_part({"answer"}, 0.6)
print(f"{time.time() - T0:5.1f}s piano", flush=True)

sub = np.zeros(N)                                    # a soft sine an octave under the bass, for weight
for a in A:
    if a["voice"] == "bass":
        n = int((a["dur"] + 0.1) * SR)
        tt = np.arange(n) / SR
        add(np.sin(2 * np.pi * hz(a["midi"] - 12) * tt) * adsr(n, 0.02, 0.15) * np.exp(-tt / 2.5) * a["vel"], a["t"], 0, 1, sub)
sub = sub / (np.abs(sub).max() + 1e-9) * 0.22

drums = np.zeros(N)
for a in A:
    v = a["vel"]
    if a["voice"] == "shaker":
        n = int(0.09 * SR)
        x = sosfilt(butter(2, [5000, 11000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
        x *= np.exp(-np.arange(n) / (0.018 * SR)) * np.clip(np.arange(n) / (0.006 * SR), 0, 1)
        add(x * v * 0.5, a["t"] + rng.uniform(-0.004, 0.006), 0, 1, drums)
    elif a["voice"] == "kick":
        n = int(0.4 * SR)
        tt = np.arange(n) / SR
        f = 48 + 70 * np.exp(-tt / 0.035)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.16)
        add(x * v * 0.9, a["t"], 0, 1, drums)
    elif a["voice"] == "rim":
        n = int(0.12 * SR)
        tt = np.arange(n) / SR
        x = (np.sin(2 * np.pi * 1700 * tt) * 0.6 + sosfilt(butter(2, [1500, 4000], "bandpass", fs=SR, output="sos"),
                                                            rng.standard_normal(n)) * 0.5) * np.exp(-tt / 0.025)
        add(x * v * 0.5, a["t"], 0, 1, drums)
drums = drums / (np.abs(drums).max() + 1e-9) * 0.3

pad = np.zeros(N)                                    # detuned saws on each bar's chord, cross-faded
bars = S["bars"]
for i, b in enumerate(bars):
    a0 = b["u"] * UNIT
    b1 = bars[i + 1]["u"] * UNIT if i + 1 < len(bars) else S["total"]
    i0, i1 = int(a0 * SR), min(N, int((b1 + 0.6) * SR))
    tt = t[i0:i1] - a0
    env = np.clip(tt / 0.5, 0, 1) * np.clip((b1 + 0.6 - a0 - tt) / 0.6, 0, 1) * (0.5 + 0.5 * min(b["lvl"], 4) / 4)
    seg = np.zeros(i1 - i0)
    for m in CH[b["chord"]]:
        for det in (-0.1, 0.1):
            seg += 2 * ((tt * hz(m) * 2 ** (det / 12)) % 1.0) - 1
    pad[i0:i1] += seg * env
pad = sosfilt(butter(2, 1000, "low", fs=SR, output="sos"), pad)
pad = pad / (np.abs(pad).max() + 1e-9) * 0.12

sea = sosfilt(butter(2, 700, "low", fs=SR, output="sos"), rng.standard_normal((N, 2)), axis=0)
sea = sea * (0.6 + 0.4 * np.sin(2 * np.pi * t / 7.3)[:, None] * np.sin(2 * np.pi * t / 11.1 + 1)[:, None]) * 0.035

voices = voices / (np.abs(voices).max() + 1e-9) * 0.75
mix = voices + bass + comp + answer + sub[:, None] + pad[:, None] + drums[:, None] + sea
y = room(mix, seconds=2.4, mix=0.22)[:N]
DB = {0: -7.0, 1: -5.0, 2: -3.0, 3: -1.5, 4: 0.0, 5: 0.5}       # the arc: a lone call, building, a hush, goodnight
arc = np.zeros(N)
for i, b in enumerate(bars):
    i0 = int(b["u"] * UNIT * SR)
    i1 = int(bars[i + 1]["u"] * UNIT * SR) if i + 1 < len(bars) else N
    arc[i0:i1] = DB[b["lvl"]] - (4.0 if b.get("coda") else 0)
arc = uniform_filter1d(arc, SR)                                   # smooth over a second
y = y * (10 ** (arc / 20))[:, None]
y = master(y, target=-14.0)
wavfile.write(OUT, SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
print(f"{time.time() - T0:5.1f}s wrote {len(y) / SR:.1f}s", flush=True)
for a in range(0, int(TOTAL), 10):
    s = y[a * SR:(a + 10) * SR]
    print(f"{a:3d}s {20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9):6.1f} dB")
