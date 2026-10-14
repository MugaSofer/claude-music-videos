"""Render the shepherd's whistle in two versions (original octave, and an octave up from 3 whistlers); count clicks."""
import json

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d

import instruments as I
import realwhistle as R

tl = json.load(open('timeline.json'))
ns = [(n['t'] - 3.0 + 0.5, n['f'], n['d'], 1.0) for n in tl['notes'] if n['scene'] == 'shepherd']
T = ns[-1][0] + ns[-1][2] + 1.5
ref = I.whistle(ns, T) * 0.8
for name, srcs, octv in (('low', R.LOW, 0), ('high', R.HIGH, 1)):
    R.SRCS = srcs
    S = R.segments()
    x = R.whistle(ns, T, octave=octv)
    x *= np.sqrt(np.mean(ref ** 2) / np.mean(x ** 2))
    d = np.abs(np.diff(x)) / (np.sqrt(uniform_filter1d(x ** 2, 960))[1:] + 1e-4)
    f, a, c = R._track(x)
    errs = []
    for t0, fr, du, v in ns:
        i0, i1 = int((t0 + 0.12) * 48000) // R.HOP, int((t0 + du - 0.05) * 48000) // R.HOP
        if i1 > i0:
            errs.append(1200 * np.log2(np.median(f[i0:i1]) / (fr * 2 ** octv)))
    print(name, len(S), 'held notes', f'{min(s["f"] for s in S):.0f}-{max(s["f"] for s in S):.0f} Hz',
          'longest', f'{max(len(s["x"]) for s in S) / 48000:.2f}s', '| click-like jumps:', int((d > 0.6).sum()),
          '| worst pitch error', f'{np.max(np.abs(errs)):.0f} cents')
    wavfile.write(f'E:/Claude/music-video-2-work/03/whistle_{name}_test.wav', 48000,
                  (np.clip(x / np.abs(x).max() * 0.8, -1, 1) * 32767).astype(np.int16))
