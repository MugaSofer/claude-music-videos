"""Tempo canon for four voices at speeds 3:4:5:6, converging at 70% of the piece.

One subject (a melody in D dorian, pentatonic-leaning so canonic collisions stay
mostly consonant) is played by every voice, each at its own speed. Entry times are
calculated so that all four voices reach subject beat CONV at the same instant T_CONV.
Writes events.json: every note with its voice, so the visuals can build the city from it.
"""
import json

import numpy as np

TOTAL = 150.0                    # seconds: the slowest voice spans the whole piece
T_CONV = 105.0                   # the convergence instant
RATIOS = [3, 4, 5, 6]
ROOTS = [38, 50, 62, 74]         # D2, D3, D4, D5
VELS = [0.56, 0.62, 0.62, 0.6]
MODE = [0, 2, 3, 5, 7, 9, 10]    # dorian


def deg_to_semi(d):
    o, i = divmod(d, 7)
    return 12 * o + MODE[i]


# ---------------------------------------------------------------- the subject
# motifs: (degrees, durations in beats). None = rest.
a = ([0, 2, 4, 3, 1, 4], [1, .5, .5, 1, .5, 1.5])
b = ([4, 3, 2, 0, -1, 0], [.5, .5, .5, .5, 1, 2])
c = ([0, 1, 2, 4, 2, 1, 0, -1, 0, 2, 4, 5, 4, 2, 1, 2], [.25] * 16)
d = ([0, 4, 7, 6, 4], [.5, .5, 2, 1, 1])
rest = lambda n: ([None], [n])


def tr(m, k):
    return ([None if x is None else x + k for x in m[0]], m[1])


def inv(m, axis=4):
    return ([None if x is None else 2 * axis - x for x in m[0]], m[1])


def dim(m, f=0.5):
    return (m[0], [x * f for x in m[1]])


def aug(m, f=2):
    return (m[0], [x * f for x in m[1]])


SECTIONS = [
    # A: statement (0-60 beats)
    [a, b, a, tr(b, 2), rest(1), a, tr(a, 2), b, rest(1), d, tr(b, -1), rest(2),
     a, b, tr(a, 3), tr(b, 3), rest(2)],
    # B: runs arrive (to ~130)
    [c, a, c, tr(b, 2), tr(c, 2), tr(a, 4), inv(b), rest(1), tr(c, -2), a, tr(c, 3), d,
     inv(a), b, tr(c, 1), tr(c, 4), tr(d, 2), rest(1)],
    # C: rising sequence, diminution: pressure builds (to ~210)
    [dim(a), dim(b), tr(dim(a), 1), tr(dim(b), 1), tr(dim(a), 2), tr(dim(b), 2), c, tr(c, 1),
     tr(c, 2), tr(c, 3), tr(dim(d), 3), tr(dim(a), 4), tr(dim(b), 4), inv(c), tr(inv(c), 2),
     tr(c, 5), tr(dim(a), 5), tr(dim(b), 5), tr(c, 6), tr(c, 7)],
]
CONV_MOTIF = ([7, 14], [2, 6])   # at the convergence: the octave leap everyone plays together
CODA = [aug(a), aug(b), rest(1), tr(aug(a), -1), aug(tr(b, -2)), rest(1), a, b, ([0], [8])]


def flatten(parts):
    out, t = [], 0.0
    for degs, durs in parts:
        for dg, du in zip(degs, durs):
            if dg is not None:
                out.append([t, du, dg])
            t += du
    return out, t


body, n_pre = flatten(sum(SECTIONS, []))
conv, n_conv = flatten([CONV_MOTIF])
coda, n_coda = flatten(CODA)
CONV = n_pre
subject = body + [[t + CONV, du, dg] for t, du, dg in conv] + [[t + CONV + n_conv, du, dg] for t, du, dg in coda]
P = CONV + n_conv + n_coda

# rates: slowest voice spans TOTAL; convergence must land at T_CONV for everyone
r1 = CONV / T_CONV               # choose r1 so voice 1 hits CONV exactly at T_CONV...
rates = [r1 * k / RATIOS[0] for k in RATIOS]
starts = [T_CONV - CONV / r for r in rates]

def dyn(t):
    """Overall dynamics: a long crescendo into the convergence, then a settling."""
    if t < T_CONV:
        w = (t / T_CONV) ** 1.6
        return 0.62 + 0.4 * w
    return 1.02 - 0.45 * min((t - T_CONV) / 30, 1) ** 0.8


events = []
for v, (r, s0) in enumerate(zip(rates, starts)):
    for bt, du, dg in subject:
        t = s0 + bt / r
        dur = max(du / r * 0.92, 0.06)
        vel = VELS[v] * (0.9 + 0.1 * np.cos(bt * 1.7)) * dyn(t)
        if CONV <= bt < CONV + n_conv:
            vel = 0.95                       # everyone lands together: accent
        events.append(dict(t=round(t, 5), m=ROOTS[v] + deg_to_semi(dg), v=round(float(vel), 3),
                           d=round(dur, 4), voice=v, beat=bt))

# a Nancarrow sweep at convergence: a four-octave glissando that lands on the unison
for i in range(56):
    events.append(dict(t=round(T_CONV - 0.9 + i * 0.016, 5), m=38 + int(i * 0.9), v=0.45 + 0.4 * i / 56,
                       d=0.12, voice=4, beat=None))
events.sort(key=lambda e: e['t'])
end = max(e['t'] + e['d'] for e in events)

info = dict(total=end, t_conv=T_CONV, rates=rates, starts=starts, subject_beats=P, conv_beat=CONV)
json.dump(dict(info=info, events=events), open('events.json', 'w'))
print(json.dumps(info, indent=1))
print('notes', len(events), ' per voice', [sum(e['voice'] == v for e in events) for v in range(5)])
