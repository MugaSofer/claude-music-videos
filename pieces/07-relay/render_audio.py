"""score.json -> E:\\Claude\\music-video-2-work\\07\\relay.wav.

Instruments: piano (piece 2), Karplus-Strong pluck (new, for Grok), organ and music box
(piece 3; the music box in a long reverb is Gemini's ghost), plus a low D drone.
"""
import json
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, "../02-player-piano")
sys.path.insert(0, "../03-tune-travelled")
from piano import SR, note, room  # noqa: E402
sys.path.insert(0, "../..")
import salamander  # noqa: E402
from instruments import music_box, organ  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\07\relay_v3_raw.wav"
S = json.load(open("score.json"))
TOTAL = S["total"] + 4
N = int(TOTAL * SR)
EV = S["events"]
hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)


def pluck(m, vel, dur, seed=0):
    """Karplus-Strong string with a little body resonance: bright attack, warm decay."""
    rng = np.random.default_rng(seed + m)
    f = hz(m)
    p = int(SR / f)
    n = int((max(dur, 0.6) + 1.2) * SR)
    buf = rng.uniform(-1, 1, p)
    buf = np.convolve(buf, [0.5, 0.5], "same")          # pluck position softening
    out = np.empty(n)
    idx = 0
    decay = 0.996 - 0.0006 * max(0, m - 60) / 12
    for i in range(n):
        out[i] = buf[idx]
        nxt = (idx + 1) % p
        buf[idx] = decay * 0.5 * (buf[idx] + buf[nxt])
        idx = nxt
    body = np.convolve(out, np.exp(-np.arange(200) / 30.0) * np.sin(np.arange(200) * 2 * np.pi * 180 / SR), "same")
    y = out + 0.25 * body / (np.abs(body).max() + 1e-9)
    env = np.ones(n)
    r = int(0.15 * SR)
    k = int((dur + 0.3) * SR)
    if k < n:
        env[k:] = 0
        env[max(0, k - r):k] *= np.linspace(1, 0, min(r, k))
    return y * env * vel * 0.6


stems = {k: np.zeros(N) for k in ("piano", "pluck", "organ", "ghost", "drone")}
cache = {}
for e in EV:
    i = int(e["t"] * SR)
    if e["voice"] == "piano":
        key = ("p", e["midi"], e["vel"], e["dur"])
        if key not in cache:
            cache[key] = note(e["midi"], e["vel"], min(e["dur"] * 1.2 + 0.3, 4.5), metal=0.35)   # v3: back to the synth piano (Muga prefers it)
        x = cache[key]
    elif e["voice"] == "pluck":
        key = ("k", e["midi"], e["vel"], e["dur"])
        if key not in cache:
            cache[key] = pluck(e["midi"], e["vel"], e["dur"])
        x = cache[key]
    else:
        continue
    j = min(i + len(x), N)
    stems[e["voice"]][i:j] += x[:j - i]

org = [(e["t"], hz(e["midi"]), e["dur"] * 0.98, e["vel"]) for e in EV if e["voice"] == "organ"]
stems["organ"] = organ(org, TOTAL, fifth_below=False)[:N] * 0.9
gh = [(e["t"], hz(e["midi"]), e["dur"], e["vel"]) for e in EV if e["voice"] == "ghost"]
stems["ghost"] = music_box(gh, TOTAL)[:N]

# drone: low D (and A) from the seed's second pass to the end, swelling in the round
t = np.arange(N) / SR
secs = dict(S["sections"])
d0 = 8.0
env = np.clip((t - d0) / 6, 0, 1) * (0.55 + 0.45 * np.clip((t - secs["round"]) / 10, 0, 1))
env *= np.clip((S["total"] + 2 - t) / 5, 0, 1)
stems["drone"] = env * (np.sin(2 * np.pi * 73.42 * t) + 0.4 * np.sin(2 * np.pi * 110.0 * t)
                        + 0.15 * np.sin(2 * np.pi * 146.83 * t)) * 0.12

PAN = {"piano": 0.45, "pluck": 0.3, "organ": 0.65, "ghost": 0.55, "drone": 0.5}
GAIN = {"piano": 1.0, "pluck": 0.9, "organ": 0.55, "ghost": 0.45, "drone": 1.0}
mix = np.zeros((N, 2))
for k, x in stems.items():
    x = x * GAIN[k] / (np.abs(x).max() + 1e-9) if np.abs(x).max() > 0 else x
    st = np.stack([x * np.cos(PAN[k] * np.pi / 2), x * np.sin(PAN[k] * np.pi / 2)], 1)
    if k == "ghost":
        st = room(st, seconds=5.0, mix=0.75)[:N]       # far away, mostly reverb
    mix += st
y = room(mix, seconds=2.4, mix=0.22)
y = y / np.abs(y).max() * 0.89
wavfile.write(OUT, SR, (y * 32767).astype(np.int16))
print(f"{len(y) / SR:.1f}s")
