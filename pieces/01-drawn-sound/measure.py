"""Fast loudness estimate per section: render every Nth frame, measure column-signal RMS.

The level is relative, not the final dBFS (no high-pass, no gain), but the balance
between sections matches the real decode closely enough to mix with.
"""
import sys

import numpy as np

from film import Film, B, FPS, TOTAL_BARS
from optical import columns_to_samples

SECTIONS = [(1, 8, 'intro'), (8, 16, 'dawn'), (16, 18, 'town'), (18, 32, 'morning'), (32, 35, 'storm in'),
            (35, 44, 'storm'), (44, 46, 'clearing'), (46, 52, 'climax'), (52, 55, 'dusk'), (55, 62, 'night'),
            (62, 65, 'coda'), (65, 68, 'text')]
STEP = int(sys.argv[1]) if len(sys.argv) > 1 else 8
only = sys.argv[2:] or None

film = Film(only)
acc = {name: [] for *_, name in SECTIONS}
bounds = [(int(B(a) * FPS), int(B(b) * FPS), n) for a, b, n in SECTIONS]
for fr in range(int(B(TOTAL_BARS) * FPS)):
    if fr % STEP:
        film.render_phases_only(fr)
        continue
    s = columns_to_samples(film.render(fr))
    s = s - s.mean()
    for a, b, n in bounds:
        if a <= fr < b:
            acc[n].append((s ** 2).mean())
ref = None
for *_, n in SECTIONS:
    v = 10 * np.log10(np.mean(acc[n]) + 1e-15)
    ref = v if ref is None and n == 'morning' else ref
print('relative to morning:')
for *_, n in SECTIONS:
    v = 10 * np.log10(np.mean(acc[n]) + 1e-15)
    print(f'  {n:10s} {v - ref:+6.1f} dB   (abs {v:6.1f})')
