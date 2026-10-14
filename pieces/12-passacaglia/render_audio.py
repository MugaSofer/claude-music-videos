"""events.json -> E:\\Claude\\music-video-2-work\\12\\passacaglia.wav, with piece 2's modal piano."""
import json
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, "../02-player-piano")
from piano import SR, render, room  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Claude\music-video-2-work\12\passacaglia.wav"
E = json.load(open("events.json"))
ev = [(e["t"], e["m"], e["v"], e["d"]) for e in E["events"]]
x = room(render(ev, E["total"] + 4, metal=0.35), seconds=2.6, mix=0.24)
x = x / np.abs(x).max() * 0.89
wavfile.write(OUT, SR, (x * 32767).astype(np.int16))
print(f"{len(x) / SR:.1f}s")
