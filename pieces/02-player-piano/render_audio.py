"""events.json -> piano audio (E:\Claude\music-video-2-work\02\canon.wav)."""
import json
import sys

import numpy as np
from scipy.io import wavfile

from piano import render, room, SR

OUT = sys.argv[1] if len(sys.argv) > 1 else r'E:\Claude\music-video-2-work\02\canon.wav'
E = json.load(open('events.json'))
ev = [(e['t'], e['m'], e['v'], e['d']) for e in E['events']]
x = room(render(ev, E['info']['total'] + 4, metal=0.45), seconds=2.2, mix=0.2)
peak = np.abs(x).max()
x = x / peak * 0.89
wavfile.write(OUT, SR, (x * 32767).astype(np.int16))
print(f'{len(x) / SR:.1f}s, normalised from peak {peak:.2f}')
