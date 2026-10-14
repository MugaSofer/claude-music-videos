"""score.json -> E:\\Claude\\music-video-2-work\\13\\murmuration.wav.

Pianos A (left) and B (right) with piece 2's modal piano, so the phasing is heard as a stereo
shimmer; an additive bowed cello (saw partials, a body formant, delayed vibrato, a swelling bow,
bow noise); marsh air.
"""
import json
import sys
import time

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, "../02-player-piano")
from piano import SR, note, room  # noqa: E402

T0 = time.time()
OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\13\murmuration.wav"
S = json.load(open("score.json"))
TOTAL = S["total"] + 3
N = int(TOTAL * SR)
hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)
L = np.zeros(N)
R = np.zeros(N)


def add(x, t0, pan, g=1.0):
    i = int(t0 * SR)
    j = min(i + len(x), N)
    L[i:j] += x[:j - i] * np.cos(pan * np.pi / 2) * g
    R[i:j] += x[:j - i] * np.sin(pan * np.pi / 2) * g


cache = {}
for e in S["events"]:
    if e["kind"] in ("pianoA", "pianoB"):
        key = (e["m"], e["v"], e["d"])
        if key not in cache:
            cache[key] = note(e["m"], e["v"], max(e["d"], 0.6), metal=0.3)
        add(cache[key], e["t"], 0.3 if e["kind"] == "pianoA" else 0.7, 0.9)
print(f"{time.time() - T0:5.1f}s pianos", flush=True)


def cello(m, dur, seed):
    rng = np.random.default_rng(seed)
    n = int((dur + 0.6) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.5) / 1.0, 0, 1)
    ph = 2 * np.pi * np.cumsum(hz(m) * vib) / SR
    y = sum(np.sin(k * ph) / k ** 1.1 for k in range(1, 14))
    y = sosfilt(butter(2, [180, 1600], "band", fs=SR, output="sos"), y) + 0.3 * sosfilt(butter(2, 300, "low", fs=SR, output="sos"), y)
    bow = sosfilt(butter(2, [1500, 5000], "band", fs=SR, output="sos"), rng.standard_normal(n)) * 0.02
    u = np.clip(t / dur, 0, 1)
    env = np.clip(t / 0.6, 0, 1) * (0.55 + 0.45 * np.sin(np.pi * u)) * np.clip((dur + 0.5 - t) / 0.5, 0, 1)
    return (y + bow) * env


for k, e in enumerate(S["events"]):
    if e["kind"] == "cello":
        add(cello(e["m"], e["d"], k), e["t"], 0.5, 0.45)
print(f"{time.time() - T0:5.1f}s cello", flush=True)

mix = np.stack([L, R], 1)
pk = np.abs(mix).max()
rng = np.random.default_rng(3)
air = sosfilt(butter(2, [200, 1200], "band", fs=SR, output="sos"), rng.standard_normal((N, 2)), axis=0)
tt = np.arange(N) / SR
air *= (0.6 + 0.4 * np.sin(2 * np.pi * tt / 9.0))[:, None] * 0.015
y = room(mix / pk * 0.8 + air, seconds=3.0, mix=0.3)
y = y / np.abs(y).max() * 0.89
wavfile.write(OUT, SR, (y * 32767).astype(np.int16))
print(f"{time.time() - T0:5.1f}s wrote {len(y) / SR:.1f}s", flush=True)
