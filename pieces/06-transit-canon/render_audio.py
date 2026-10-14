"""events.json -> E:\\Claude\\music-video-2-work\\06\\transit.wav. Piano from piece 2, panned by map x."""
import json
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, "../02-player-piano")
from piano import SR, note, room  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\06\transit.wav"
E = json.load(open("events.json"))
total = E["info"]["total"] + 5
L = np.zeros(int(total * SR))
R = np.zeros_like(L)
cache = {}
for e in E["events"]:
    key = (e["m"], e["v"], e["d"])
    if key not in cache:
        cache[key] = note(e["m"], e["v"], e["d"], metal=0.6)
    x = cache[key]
    i = int(e["t"] * SR)
    j = min(i + len(x), len(L))
    pan = 0.15 + 0.7 * e["x"] / 32
    L[i:j] += x[:j - i] * np.cos(pan * np.pi / 2)
    R[i:j] += x[:j - i] * np.sin(pan * np.pi / 2)
y = room(np.stack([L, R], 1), seconds=3.0, mix=0.28)
y = y / np.abs(y).max() * 0.89
wavfile.write(OUT, SR, (y * 32767).astype(np.int16))
print(f"{len(y) / SR:.1f}s, {len(cache)} distinct notes")
