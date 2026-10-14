"""events.json + the wave field -> E:\\Claude\\music-video-2-work\\08\\tidal.wav.

Bells: struck-bell partial series (hum, prime, tierce, quint, nominal, ...) with detuned pairs for
the shimmer. Halyard ticks: a noise snap plus a small metallic ring. Lighthouse: a big low bell.
Sea wash: noise shaped by the water height at the quay wall and by the tide.
"""
import json
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, "../02-player-piano")
from piano import SR, room  # noqa: E402
from sea import HARBOUR, height, tide  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\08\tidal.wav"
E = json.load(open("events.json"))
TOTAL = E["total"] + 8
N = int(TOTAL * SR)
hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)

# ratio, amplitude, decay (s) at the prime; a small ship's bell, brassy
PARTIALS = [(0.5, 0.35, 3.2), (1.0, 1.0, 2.4), (1.19, 0.45, 1.6), (1.5, 0.3, 1.2), (2.0, 0.55, 1.0),
            (2.51, 0.25, 0.6), (2.66, 0.2, 0.5), (3.01, 0.15, 0.35), (4.1, 0.08, 0.2)]


def bell(m, vel, big=1.0, seed=0):
    rng = np.random.default_rng(seed + m)
    f0 = hz(m)
    dur = 4.0 * big + 1.0
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for r, a, dec in PARTIALS:
        f = f0 * r
        if f > 16000:
            continue
        d = dec * big * (1.6 if m < 55 else 1.0)
        for det in (-0.6, 0.6):            # a pair of slightly split modes: the shimmer
            y += a * 0.5 * np.exp(-t / d) * np.sin(2 * np.pi * f * (1 + det / 1000) * t + rng.uniform(0, 6.28))
    k = int(0.004 * SR)
    y[:k] += rng.standard_normal(k) * np.exp(-np.arange(k) / (0.0008 * SR)) * 0.3      # clapper strike
    return y * vel


def tick(vel, seed):
    rng = np.random.default_rng(seed)
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    snap = sosfilt(butter(2, [1800, 5200], "band", fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-t / 0.012)
    ring = np.sin(2 * np.pi * 910 * t) * np.exp(-t / 0.09) + 0.5 * np.sin(2 * np.pi * 2470 * t) * np.exp(-t / 0.05)
    return (1.2 * snap + 0.25 * ring) * vel


L = np.zeros(N)
R = np.zeros(N)


def add(x, t0, pan):
    i = int(t0 * SR)
    j = min(i + len(x), N)
    L[i:j] += x[:j - i] * np.cos(pan * np.pi / 2)
    R[i:j] += x[:j - i] * np.sin(pan * np.pi / 2)


cache = {}
for k, e in enumerate(E["events"]):
    pan = 0.12 + 0.76 * e["x"] / HARBOUR
    if e["kind"] == "bell":
        key = (e["midi"], e["vel"])
        if key not in cache:
            cache[key] = bell(e["midi"], e["vel"])
        add(cache[key] * 0.5, e["t"], pan)
    elif e["kind"] == "tick":
        add(tick(e["vel"], k) * 0.22, e["t"], pan)
    elif e["kind"] == "light":
        add(bell(e["midi"], e["vel"], big=2.5) * 0.55, e["t"], 0.2)

# sea wash: waves slapping the quay wall (right) plus a broad surf bed
t = np.arange(N) / SR
ctrl_t = np.arange(0, TOTAL, 0.02)
quay = np.array([max(0.0, height(HARBOUR - 3, c)) for c in ctrl_t])
tid = np.array([tide(c) for c in ctrl_t])
quay_env = np.interp(t, ctrl_t, quay / (quay.max() + 1e-9))
tide_env = np.interp(t, ctrl_t, tid)
rng = np.random.default_rng(2)
noise = rng.standard_normal((N, 2))
wash = sosfilt(butter(2, [250, 2400], "band", fs=SR, output="sos"), noise, axis=0)
bed = sosfilt(butter(2, 500, "low", fs=SR, output="sos"), rng.standard_normal((N, 2)), axis=0)
sea = wash * (quay_env ** 2 * tide_env)[:, None] * np.array([0.35, 1.0]) * 0.06
sea += bed * (0.3 + 0.7 * tide_env)[:, None] * 0.05

mix = np.stack([L, R], 1)
mix = mix / (np.abs(mix).max() + 1e-9) * 0.8 + sea
y = room(mix, seconds=3.2, mix=0.3)
fade = np.clip((TOTAL - 1 - np.arange(len(y)) / SR) / 4, 0, 1)
y = y * fade[:, None]
y = y / np.abs(y).max() * 0.89
wavfile.write(OUT, SR, (y * 32767).astype(np.int16))
print(f"{len(y) / SR:.1f}s, {len(cache)} distinct bells")
