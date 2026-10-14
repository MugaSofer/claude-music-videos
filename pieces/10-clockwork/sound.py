"""events.json -> E:\\Claude\\music-video-2-work\\10\\clockwork.wav.

Bells (gear A), steel tongues (B, D), wood bars (C), glass (E), escapement tick/tock,
and a winding ratchet at the start. As the spring runs down, strikes soften and sag in pitch.
"""
import json
import sys
import time

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, "../02-player-piano")
from piano import SR, room  # noqa: E402

T0 = time.time()
OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\10\clockwork.wav"
E = json.load(open("events.json"))
TOTAL = E["total"] + 3
N = int(TOTAL * SR)
hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)
PAN = {"A": 0.25, "B": 0.4, "C": 0.55, "D": 0.68, "E": 0.8}
# instrument: list of (partial ratio, amplitude, decay seconds)
TIMBRE = {
    "bell": [(0.5, 0.3, 3.0), (1.0, 1.0, 2.2), (1.19, 0.4, 1.4), (1.5, 0.25, 1.0), (2.0, 0.45, 0.8), (2.66, 0.2, 0.4)],
    "tongue": [(1.0, 1.0, 1.3), (5.9, 0.35, 0.12), (13.1, 0.12, 0.04)],
    "wood": [(1.0, 1.0, 0.35), (3.93, 0.45, 0.08), (9.2, 0.15, 0.03)],
    "glass": [(1.0, 1.0, 2.4), (2.32, 0.3, 0.9), (4.1, 0.08, 0.3)],
}


def struck(inst, m, vel, seed):
    r = np.random.default_rng(seed)
    parts = TIMBRE[inst]
    dur = max(d for _, _, d in parts) * 4 + 0.1
    t = np.arange(int(dur * SR)) / SR
    f0 = hz(m)
    y = np.zeros_like(t)
    for ratio, a, dec in parts:
        f = f0 * ratio
        if f < 17000:
            y += a * np.exp(-t / dec) * np.sin(2 * np.pi * f * t + r.uniform(0, 6.28))
    k = int(0.002 * SR)
    y[:k] += r.standard_normal(k) * 0.15 * np.linspace(1, 0, k)       # the pin's contact click
    return y * vel


def click(freq, seed, amp=1.0):
    r = np.random.default_rng(seed)
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    nz = sosfilt(butter(2, [freq * 0.7, freq * 1.4], "band", fs=SR, output="sos"), r.standard_normal(n))
    return (nz * np.exp(-t / 0.004) + 0.4 * np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.012)) * amp


L = np.zeros(N)
R = np.zeros(N)


def add(x, t0, pan, g=1.0):
    i = int(t0 * SR)
    j = min(i + len(x), N)
    if j <= i:
        return
    L[i:j] += x[:j - i] * np.cos(pan * np.pi / 2) * g
    R[i:j] += x[:j - i] * np.sin(pan * np.pi / 2) * g


cache = {}
for k, e in enumerate(E["events"]):
    if e["kind"] == "esc":
        f = 3600 if not e["tock"] else 2300
        add(click(f, k, e["vel"]), e["t"], 0.5, 0.35)
    elif e["kind"] == "pin":
        sag = 0.35 * (1 - e["speed"])                     # a slower strike rings a hair flat
        key = (e["inst"], e["midi"], round(e["vel"], 2), round(sag, 2))
        if key not in cache:
            cache[key] = struck(e["inst"], e["midi"] - sag, e["vel"], len(cache))
        g = {"bell": 0.55, "tongue": 0.4, "wood": 0.5, "glass": 0.28}[e["inst"]]
        add(cache[key], e["t"], PAN[e["gear"]], g)
print(f"{time.time() - T0:5.1f}s strikes done ({len(cache)} voices)", flush=True)

# winding the spring: ratchet clicks at a steady rate while the key turns (0.5 to 7 s)
tt = 0.5
k = 0
while tt < 7.0:
    add(click(1500, 5000 + k, 0.7), tt, 0.45, 0.3)
    tt += 0.11 if (k % 8) < 6 else 0.3                   # turn, turn, ... regrip
    k += 1

mix = np.stack([L, R], 1)
y = room(mix, seconds=1.6, mix=0.18)
y = y / np.abs(y).max() * 0.89
wavfile.write(OUT, SR, (y * 32767).astype(np.int16))
print(f"{time.time() - T0:5.1f}s wrote {len(y) / SR:.1f}s", flush=True)
