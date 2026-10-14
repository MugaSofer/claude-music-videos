"""Build sections.json for a take from its analysis (beats) plus hand-read section times.

usage: python make_sections.py ANALYSIS.json OUT.json
Section times come from the vocal-phrase map (see PROGRESS.md). Take A's are below.
"""
import json
import sys

A = json.load(open(sys.argv[1]))
TAKE_A = [
    dict(kind='verse', t0=11.5, t1=36.2, vignettes=['baker', 'bus', 'nurse', 'fox']),
    dict(kind='chorus', t0=37.0, t1=58.5),
    dict(kind='verse', t0=63.8, t1=88.5, vignettes=['lorry', 'dad', 'lines', 'tower']),
    dict(kind='chorus', t0=89.3, t1=114.5),
    dict(kind='bridge', t0=116.0, t1=131.8, vignettes=['baker', 'lines', 'tower']),
    dict(kind='final', t0=133.1, t1=158.2),
    dict(kind='outro', t0=161.3, t1=163.7),
]
TAKE_B = [      # chosen: steady 83.3 bpm (beat-interval CV 1.8%), 2:50
    dict(kind='verse', t0=11.45, t1=35.45, vignettes=['baker', 'bus', 'nurse', 'fox']),
    dict(kind='chorus', t0=36.8, t1=58.1),
    dict(kind='verse', t0=62.95, t1=87.05, vignettes=['lorry', 'dad', 'lines', 'tower']),
    dict(kind='chorus', t0=88.4, t1=105.5),
    dict(kind='bridge', t0=106.8, t1=126.45, vignettes=['baker', 'lines', 'tower']),
    dict(kind='final', t0=131.25, t1=158.6),
    dict(kind='outro', t0=159.7, t1=167.25),
]
take = sys.argv[3] if len(sys.argv) > 3 else 'A'
json.dump(dict(beats=A['beats'], downbeats=A['downbeats'], sections=TAKE_B if take == 'B' else TAKE_A,
               total=170.0 if take == 'B' else 179.6), open(sys.argv[2], 'w'), indent=1)
print('ok')
