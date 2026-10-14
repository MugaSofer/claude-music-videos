"""Beats and vocal phrases for a Suno take.

usage (with MV1's venv, which has beat_this + demucs):
  E:/music-video/btenv/Scripts/python -B analyse.py E:/Claude/music-video-2-work/05/takeA.wav OUT.json
Writes beats, downbeats, and vocal phrases (start/end of each sung stretch).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

src, out = sys.argv[1], sys.argv[2]
work = Path(src).with_suffix('')

# 1. beats
from beat_this.inference import File2Beats  # noqa: E402
f2b = File2Beats(checkpoint_path='final0', device='cpu', dbn=False)
beats, downbeats = f2b(src)
print('beats', len(beats), 'downbeats', len(downbeats))

# 2. vocal stem (demucs htdemucs, two stems)
stem_dir = work.parent / 'stems'
subprocess.run([sys.executable, '-B', '-m', 'demucs', '--two-stems=vocals', '-n', 'htdemucs', '-d', 'cpu',
                '-j', '2', '-o', str(stem_dir), src], check=True)
voc_path = stem_dir / 'htdemucs' / work.name / 'vocals.wav'
v, sr = sf.read(str(voc_path))
if v.ndim > 1:
    v = v.mean(1)

# 3. vocal activity: RMS in 50 ms hops, threshold relative to the loud parts, merge short gaps
hop = int(0.05 * sr)
rms = np.sqrt(np.convolve(v ** 2, np.ones(hop) / hop, mode='same'))[::hop]
db = 20 * np.log10(rms + 1e-9)
thr = np.percentile(db, 90) - 22
act = db > thr
phrases, start = [], None
for i, a in enumerate(act):
    t = i * 0.05
    if a and start is None:
        start = t
    if not a and start is not None:
        phrases.append([start, t])
        start = None
if start is not None:
    phrases.append([start, len(act) * 0.05])
merged = []
for p in phrases:
    if merged and p[0] - merged[-1][1] < 0.35:
        merged[-1][1] = p[1]
    else:
        merged.append(p)
merged = [p for p in merged if p[1] - p[0] > 0.4]
print('phrases', len(merged))
for p in merged:
    print(f'  {p[0]:7.2f} - {p[1]:7.2f}')
json.dump(dict(beats=list(map(float, beats)), downbeats=list(map(float, downbeats)), phrases=merged,
               vocals=str(voc_path)), open(out, 'w'), indent=1)
