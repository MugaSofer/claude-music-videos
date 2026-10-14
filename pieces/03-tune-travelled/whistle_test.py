"""Render the shepherd's tune with the real whistle and the old synth; report per-note pitch error."""
import json
import time

import numpy as np
from scipy.io import wavfile

import instruments as I
import realwhistle as R

t_ = time.time()
S = R.segments()
print(len(S), 'held notes:', sorted(round(s['f']) for s in S), f'{time.time() - t_:.1f}s', flush=True)
tl = json.load(open('timeline.json'))
ns = [(n['t'] - 3.0 + 0.5, n['f'], n['d'], 1.0) for n in tl['notes'] if n['scene'] == 'shepherd']
T = ns[-1][0] + ns[-1][2] + 1.5
x = R.whistle(ns, T)
print(f'whistle {time.time() - t_:.1f}s', flush=True)
y = I.whistle(ns, T) * 0.8
x *= np.sqrt(np.mean(y ** 2) / np.mean(x ** 2))
f, a, c = R._track(x)
errs = []
for t0, fr, du, v in ns:
    i0, i1 = int((t0 + 0.12) * SR_ if (SR_ := 48000) else 0) // R.HOP, int((t0 + du - 0.05) * 48000) // R.HOP
    if i1 > i0:
        errs.append(1200 * np.log2(np.median(f[i0:i1]) / fr))
print('pitch error per note (cents):', np.round(errs).astype(int))
for nm, z in (('real', x), ('synth', y)):
    wavfile.write(f'E:/Claude/music-video-2-work/03/whistle_{nm}_test.wav', 48000,
                  (np.clip(z / np.abs(z).max() * 0.8, -1, 1) * 32767).astype(np.int16))
