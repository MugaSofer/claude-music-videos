"""score.json -> E:\\Claude\\music-video-2-work\\11\\signal.wav.

Lighthouse: a warm horn/organ voice (filtered saw, vibrato, a soft fifth below), panned left.
Boat: a clear sine with a small bell tail, panned right. GOODNIGHT: both together, an octave apart.
Under them: a detuned pad holding each message's chord, and the sea.
"""
import json
import sys
import time

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, "../02-player-piano")
from piano import SR, room  # noqa: E402
sys.path.insert(0, "../..")
import salamander  # noqa: E402

T0 = time.time()
OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\11\signal_v2_raw.wav"
S = json.load(open("score.json"))
TOTAL = S["total"] + 3
N = int(TOTAL * SR)
hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)


def adsr(n, a, r):
    e = np.ones(n)
    ka, kr = min(int(a * SR), n), min(int(r * SR), n)
    e[:ka] = np.linspace(0, 1, ka)
    if kr:
        e[-kr:] *= np.linspace(1, 0, kr)
    return e


def horn(m, dur):
    n = int((dur + 0.08) * SR)
    t = np.arange(n) / SR
    f = hz(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.25, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = sum(np.sin(k * ph) / k ** 1.3 for k in range(1, 7))
    fifth = 0.25 * np.sin(ph * 2 / 3)
    y = sosfilt(butter(2, 950, "low", fs=SR, output="sos"), saw * 0.6 + fifth)
    return y * adsr(n, 0.018, 0.07)


def boatvoice(m, dur):
    n = int((dur + 0.7) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    hold = np.zeros(n)
    k = int((dur + 0.05) * SR)
    hold[:k] = adsr(k, 0.006, 0.04)
    tail = np.exp(-np.maximum(t - dur, 0) / 0.25) * (t >= dur)
    y = np.sin(2 * np.pi * f * t) * (hold + 0.35 * tail) + 0.25 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.12)
    return y * 0.8


L = np.zeros(N)
R = np.zeros(N)


def add(x, t0, pan, g=1.0):
    i = int(t0 * SR)
    j = min(i + len(x), N)
    L[i:j] += x[:j - i] * np.cos(pan * np.pi / 2) * g
    R[i:j] += x[:j - i] * np.sin(pan * np.pi / 2) * g


for e in S["events"]:
    if e["sender"] in ("light", "both"):
        add(horn(e["midi"], e["dur"]), e["t"], 0.28, 0.5)
    if e["sender"] == "boat":
        add(salamander.note(e["midi"], 0.55, max(e["dur"], 0.25)).mean(1) * 1.6, e["t"], 0.72, 0.42)
    if e["sender"] == "both":
        add(salamander.note(e["midi"] + 12, 0.6, max(e["dur"], 0.25)).mean(1) * 1.6, e["t"], 0.72, 0.36)
print(f"{time.time() - T0:5.1f}s voices", flush=True)

# pad: detuned saws, low-passed, one chord per message, cross-faded through the breaths
pad = np.zeros(N)
t = np.arange(N) / SR
msgs = S["messages"]
for i, m in enumerate(msgs):
    a = m["t0"] - 1.5
    b = msgs[i + 1]["t0"] - 1.0 if i + 1 < len(msgs) else S["total"]
    i0, i1 = max(0, int(a * SR)), min(N, int((b + 2.5) * SR))
    tt = t[i0:i1] - a
    env = np.clip(tt / 2.0, 0, 1) * np.clip((b + 2.5 - a - tt) / 2.5, 0, 1)
    seg = np.zeros(i1 - i0)
    for note in m["chord"]:
        for det in (-0.12, 0.12):
            f = hz(note) * 2 ** (det / 12)
            seg += 2 * ((tt * f) % 1.0) - 1
    pad[i0:i1] += seg * env
pad = sosfilt(butter(2, 900, "low", fs=SR, output="sos"), pad)
pad = pad / (np.abs(pad).max() + 1e-9) * 0.16
print(f"{time.time() - T0:5.1f}s pad", flush=True)

# the sea: slow swell of low-passed noise
rng = np.random.default_rng(1)
sea = sosfilt(butter(2, 700, "low", fs=SR, output="sos"), rng.standard_normal((N, 2)), axis=0)
swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 7.3)[:, None] * np.sin(2 * np.pi * t / 11.1 + 1)[:, None]
sea = sea * swell * 0.05

mix = np.stack([L, R], 1)
mix = mix / (np.abs(mix).max() + 1e-9) * 0.7 + pad[:, None] + sea
y = room(mix, seconds=2.8, mix=0.3)
y = y / np.abs(y).max() * 0.89
wavfile.write(OUT, SR, (y * 32767).astype(np.int16))
print(f"{time.time() - T0:5.1f}s wrote {len(y) / SR:.1f}s", flush=True)
