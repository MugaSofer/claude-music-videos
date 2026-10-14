"""score.json -> E:\\Claude\\music-video-2-work\\09\\typewriter.wav.

Typewriter parts (key / space / shift / punctuation / margin bell / carriage-return ratchet),
a 2-op FM electric piano holding each line's chord, and a weather ambience per line.
"""
import json
import sys
import time
T0 = time.time()
log = lambda m: print(f"{time.time() - T0:6.1f}s {m}", flush=True)

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, "../02-player-piano")
from piano import SR, room  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\09\typewriter.wav"
S = json.load(open("score.json"))
TOTAL = S["total"] + 3
N = int(TOTAL * SR)
hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)
BP = lambda lo, hi: butter(2, [lo, hi], "band", fs=SR, output="sos")
LP = lambda f: butter(2, f, "low", fs=SR, output="sos")
HP = lambda f: butter(2, f, "high", fs=SR, output="sos")


def env(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def strike(seed, low=180.0, low_amp=0.5, click=1.0, ping=0.25):
    """One typebar hitting the platen: click + body thunk + a little metal ping."""
    r = np.random.default_rng(seed)
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    c = sosfilt(HP(2500), r.standard_normal(n)) * env(n, 0.004) * click
    lo = low * r.uniform(0.92, 1.08)
    body = np.sin(2 * np.pi * lo * t) * env(n, 0.03) * low_amp
    pf = r.uniform(3200, 4200)
    p = np.sin(2 * np.pi * pf * t) * env(n, 0.025) * ping
    return (c + body + p) * r.uniform(0.8, 1.0)


def ding(m):
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    f = hz(m)
    y = (np.sin(2 * np.pi * f * t) * env(n, 1.1) + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * env(n, 0.45)
         + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * env(n, 0.15))
    return y * 0.5


def ratchet(seed):
    """Carriage return: accelerating ratchet clicks, then the carriage stop clunk."""
    r = np.random.default_rng(seed)
    n = int(0.75 * SR)
    y = np.zeros(n)
    tt = 0.0
    gap = 0.045
    while tt < 0.55:
        i = int(tt * SR)
        k = int(0.006 * SR)
        y[i:i + k] += sosfilt(BP(1800, 6000), r.standard_normal(k)) * env(k, 0.0015) * 0.5
        tt += gap
        gap = max(gap * 0.9, 0.012)
    i = int(0.58 * SR)
    k = int(0.15 * SR)
    t = np.arange(k) / SR
    y[i:i + k] += (np.sin(2 * np.pi * 120 * t) * env(k, 0.04) + 0.6 * sosfilt(HP(900), r.standard_normal(k)) * env(k, 0.01))
    return y


def epiano(m, dur, vel, bright=1.0):
    """2-op FM electric piano: bell-ish attack settling into a warm tone."""
    n = int((dur + 2.5) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    idx = (1.6 * np.exp(-t / 0.35) + 0.35) * bright
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t)) * np.exp(-t / (3.5 + 0.02 * (72 - m)))
    rel = int(dur * SR)
    if rel < n:
        y[rel:] *= np.exp(-np.arange(n - rel) / (0.6 * SR))
    a = int(0.01 * SR)
    y[:a] *= np.linspace(0, 1, a)
    return y * vel


L = np.zeros(N)
R = np.zeros(N)


def add(x, t0, pan=0.5, g=1.0):
    i = int(t0 * SR)
    j = min(i + len(x), N)
    L[i:j] += x[:j - i] * np.cos(pan * np.pi / 2) * g
    R[i:j] += x[:j - i] * np.sin(pan * np.pi / 2) * g


# ---- typewriter (the carriage moves, so keys pan with the column: the typebar hits at the carriage point)
for k, e in enumerate(S["events"]):
    pan = 0.3 + 0.4 * min(e.get("col", 0), 64) / 64
    if e["kind"] == "key":
        add(strike(k), e["t"], pan, 0.5)
    elif e["kind"] == "punct":
        add(strike(k, low=220, ping=0.4), e["t"], pan, 0.45)
    elif e["kind"] == "space":
        add(strike(k, low=95, low_amp=1.2, click=0.35, ping=0.05), e["t"], pan, 0.55)   # the soft kick
    elif e["kind"] == "shift":
        add(strike(k, low=600, low_amp=0.4, click=1.3, ping=0.1), e["t"] - 0.03, pan, 0.4)   # a rim click
        add(strike(k + 999), e["t"], pan, 0.5)
    elif e["kind"] == "ding":
        add(ding(e["midi"]), e["t"], 0.72, 0.35)
    elif e["kind"] == "return":
        add(ratchet(k), e["t"], 0.5, 0.4)

log("typewriter done")
# ---- electric piano: one chord per line, entering softly after "Dear you,"
pad = np.zeros((N, 2))
for L_ in S["lines"]:
    dur = L_["t1"] - L_["t0"]
    bright = 1.35 if L_["weather"] == "sun" else 0.8 if L_["weather"] == "fog" else 1.0
    for j, m in enumerate(L_["chord"]):
        x = epiano(m, dur, 0.16 if j else 0.22, bright)
        i = int(L_["t0"] * SR)
        k2 = min(i + len(x), N)
        pan = 0.35 + 0.3 * j / 4
        pad[i:k2, 0] += x[:k2 - i] * np.cos(pan * np.pi / 2)
        pad[i:k2, 1] += x[:k2 - i] * np.sin(pan * np.pi / 2)

log("pad done")
# ---- weather ambiences, faded across each line
rng = np.random.default_rng(4)
amb = np.zeros((N, 2))
tt = np.arange(N) / SR
for L_ in S["lines"]:
    w = L_["weather"]
    i0, i1 = int(L_["t0"] * SR), min(int((L_["t1"] + 1.5) * SR), N)
    n = i1 - i0
    fade = np.minimum(1, np.minimum(np.arange(n) / (1.5 * SR), (n - np.arange(n)) / (1.5 * SR)))
    seg = np.zeros((n, 2))
    if w == "rain":
        seg += sosfilt(BP(800, 6000), rng.standard_normal((n, 2)), axis=0) * 0.05
        for _ in range(140):                                  # droplets
            p = rng.integers(0, n - 2000)
            k = int(0.03 * SR)
            f = rng.uniform(1500, 3500)
            seg[p:p + k, rng.integers(0, 2)] += np.sin(2 * np.pi * f * np.arange(k) / SR * (1 + np.arange(k) / k * 0.4)) * env(k, 0.008) * 0.15
    elif w == "wind":
        sweep = 0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / SR / 4.3)
        base = sosfilt(BP(300, 1400), rng.standard_normal((n, 2)), axis=0)
        seg += base * (0.03 + 0.07 * sweep)[:, None]
    elif w == "fog":
        seg += np.sin(2 * np.pi * 73.4 * tt[i0:i1])[:, None] * 0.05 + sosfilt(LP(400), rng.standard_normal((n, 2)), axis=0) * 0.04
    elif w == "snow":
        for _ in range(30):
            p = rng.integers(0, n - SR)
            m = rng.choice([84, 86, 88, 91, 93])
            x = ding(m)[:SR] * 0.18
            seg[p:p + len(x), rng.integers(0, 2)] += x
    elif w == "stars":
        for _ in range(22):
            p = rng.integers(0, n - SR)
            m = rng.choice([88, 91, 93, 96, 100])
            x = ding(m)[:SR] * 0.14
            seg[p:p + len(x), rng.integers(0, 2)] += x
    elif w == "sun":
        seg += sosfilt(BP(2000, 7000), rng.standard_normal((n, 2)), axis=0) * 0.008   # a warm air hiss
    amb[i0:i1] += seg * fade[:, None]

log("ambience done")
mix = np.stack([L, R], 1)
mix = mix / (np.abs(mix).max() + 1e-9) * 0.75 + pad / (np.abs(pad).max() + 1e-9) * 0.42 + amb
y = room(mix, seconds=1.8, mix=0.2)
log("room done")
y = y / np.abs(y).max() * 0.89
wavfile.write(OUT, SR, (y * 32767).astype(np.int16))
print(f"{len(y) / SR:.1f}s")
