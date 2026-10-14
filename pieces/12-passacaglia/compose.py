"""Passacaglia: an 8-bar ground in D minor with ten variations. Writes events.json.

Every note: t (s), m (midi), v (velocity), d (duration s), var (0-9), voice, bar (0-7), beat (0..3).
"""
import json

import numpy as np

BPM = 76
BEAT = 60 / BPM
BAR = 3 * BEAT
GROUND = [50, 48, 46, 45, 43, 46, 45, 38]                 # D3 C3 Bb2 A2 G2 Bb2 A2 D2
CHORDS = [[2, 5, 9], [0, 4, 7], [10, 2, 5], [9, 1, 4], [7, 10, 2], [4, 7, 10], [9, 1, 4, 7], [2, 5, 9]]
SCALE = [2, 4, 5, 7, 9, 10, 0, 1]                          # D minor (harmonic: C# allowed)
rng = np.random.default_rng(12)
EV = []


def add(t, m, v, d, var, voice, bar, beat):
    EV.append(dict(t=round(t, 4), m=int(m), v=round(float(v), 3), d=round(d, 4), var=var, voice=voice, bar=bar,
                   beat=round(beat, 3)))


def tones(bar, lo, hi):
    return [m for m in range(lo, hi + 1) if m % 12 in CHORDS[bar]]


def scale_notes(lo, hi, bar):
    allowed = set(SCALE) | set(CHORDS[bar])
    if 1 not in CHORDS[bar]:
        allowed.discard(1)                                 # C# only over A chords
    return [m for m in range(lo, hi + 1) if m % 12 in allowed]


def nearest(target, cands):
    return min(cands, key=lambda c: (abs(c - target), c))


def voice_lead(prev, bar, ranges):
    out = []
    for p, (lo, hi) in zip(prev, ranges):
        c = [x for x in tones(bar, lo, hi) if x not in out]
        out.append(nearest(p, c))
    return out


def melody_for_var(seed):
    """A singing line: chord tone on each downbeat, passing tones between, quarters (3 per bar)."""
    r = np.random.default_rng(seed)
    line, cur = [], 74
    for bar in range(8):
        down = nearest(cur + int(r.integers(-3, 4)), tones(bar, 67, 81))
        nxt = nearest(down + int(r.integers(-4, 5)), tones((bar + 1) % 8, 67, 81))
        sc = scale_notes(64, 84, bar)
        mid = sorted(sc, key=lambda m: abs(m - (down + nxt) / 2))[0]
        third = sorted(sc, key=lambda m: abs(m - (mid + nxt) / 2) + (m == mid) * 9)[0]
        line.append([down, mid, third])
        cur = nxt
    line[-1] = [74, 73, 74]                                # end the phrase home on D (via C#)
    return line


MELODY = melody_for_var(4)


def ground(var, t0, vel=0.55, octave=False):
    for bar, b in enumerate(GROUND):
        t = t0 + bar * BAR
        add(t, b, vel, BAR * 0.98, var, "ground", bar, 0)
        if octave:
            add(t, b - 12, vel * 0.85, BAR * 0.98, var, "ground", bar, 0)


def variation(var, t0):
    voices = [62, 65, 69]
    if var == 0:
        ground(var, t0, 0.5)
        for bar in range(8):
            add(t0 + bar * BAR, nearest(69, tones(bar, 62, 74)), 0.32, BAR, var, "upper", bar, 0)
    elif var == 1:                                           # chorale
        ground(var, t0, 0.5)
        for bar in range(8):
            voices = voice_lead(voices, bar, [(57, 67), (62, 72), (67, 77)])
            for k, m in enumerate(voices):
                add(t0 + bar * BAR, m, 0.42, 2 * BEAT, var, f"ch{k}", bar, 0)
                add(t0 + bar * BAR + 2 * BEAT, m, 0.36, BEAT, var, f"ch{k}", bar, 2)
    elif var == 2:                                           # broken chords in 8ths
        ground(var, t0, 0.52)
        for bar in range(8):
            ch = tones(bar, 57, 72)[:4]
            pat = [0, 2, 1, 2, 3 if len(ch) > 3 else 1, 2]
            for k, i in enumerate(pat):
                add(t0 + bar * BAR + k * BEAT / 2, ch[i], 0.38, BEAT / 2 * 1.4, var, "broken", bar, k / 2)
    elif var in (3, 4, 9):                                   # melody (4: + canon; 9: return, alone)
        ground(var, t0, 0.5 if var != 9 else 0.38)
        for bar in range(8):
            for k, m in enumerate(MELODY[bar]):
                mm = m + (12 if var == 9 else 0)
                add(t0 + bar * BAR + k * BEAT, mm, 0.55 if var != 9 else 0.45, BEAT * 0.95, var, "melody", bar, k)
                if var == 4 and bar < 7:                     # canon an octave lower, one bar behind
                    add(t0 + (bar + 1) * BAR + k * BEAT, m - 12, 0.42, BEAT * 0.95, var, "canon", bar + 1, k)
            if var == 3:
                ch = tones(bar, 57, 67)[:3]
                for k in range(6):
                    add(t0 + bar * BAR + k * BEAT / 2, ch[k % len(ch)], 0.26, BEAT / 2, var, "acc", bar, k / 2)
    elif var == 5:                                           # running 16ths
        ground(var, t0, 0.52)
        cur = 62
        for bar in range(8):
            sc = scale_notes(55, 79, bar)
            target = nearest(cur + (7 if bar % 2 == 0 else -7), tones((bar + 1) % 8, 57, 77))
            i = sc.index(nearest(cur, sc))
            step = 1 if target > cur else -1
            for k in range(12):
                m = sc[max(0, min(len(sc) - 1, i))]
                add(t0 + bar * BAR + k * BEAT / 4, m, 0.34 + 0.08 * (k % 4 == 0), BEAT / 4 * 1.2, var, "run", bar, k / 4)
                i += step
                if (step > 0 and sc[min(i, len(sc) - 1)] > target + 2) or (step < 0 and sc[max(i, 0)] < target - 2):
                    step = -step
            cur = target
    elif var == 6:                                           # suspension chain: half notes, prepared and resolved
        ground(var, t0, 0.5)
        prev = 72
        for bar in range(8):
            res = nearest(prev - 1, tones(bar, 62, 77))
            sus = prev                                       # hold the previous note over the barline (a dissonance)
            add(t0 + bar * BAR, sus, 0.46, 2 * BEAT, var, "sus", bar, 0)
            add(t0 + bar * BAR + 2 * BEAT, res, 0.38, BEAT, var, "sus", bar, 2)
            low = nearest(res - 9, tones(bar, 55, 67))
            add(t0 + bar * BAR, low, 0.3, BAR, var, "sus2", bar, 0)
            prev = res
    elif var == 7:                                           # triplet arpeggios sweeping
        ground(var, t0, 0.56)
        for bar in range(8):
            ch = tones(bar, 55, 86)
            up = bar % 2 == 0
            seq = ch if up else ch[::-1]
            for k in range(9):
                m = seq[min(k * len(seq) // 9, len(seq) - 1)]
                add(t0 + bar * BAR + k * BEAT / 3, m, 0.3 + 0.25 * k / 9, BEAT / 3 * 1.5, var, "trip", bar, k / 3)
    elif var == 8:                                           # climax: full chords, octaves
        ground(var, t0, 0.68, octave=True)
        for bar in range(8):
            ch = tones(bar, 60, 76)
            for k in range(3):
                for m in ch[:4]:
                    add(t0 + bar * BAR + k * BEAT, m, 0.5 if k == 0 else 0.4, BEAT * 0.9, var, "chord", bar, k)
            for k, m in enumerate(MELODY[bar]):
                add(t0 + bar * BAR + k * BEAT, m + 12, 0.62, BEAT * 0.95, var, "melody", bar, k)
                add(t0 + bar * BAR + k * BEAT, m, 0.5, BEAT * 0.95, var, "melody", bar, k)


def build():
    t0 = 1.0
    for var in range(10):
        variation(var, t0)
        t0 += 8 * BAR
    # the Picardy third: D major, held
    for m in [38, 50, 57, 62, 66, 69, 74]:
        add(t0, m, 0.5, 6.0, 10, "final", 0, 0)
    EV.sort(key=lambda e: e["t"])
    return t0 + 8.0


if __name__ == "__main__":
    total = build()
    json.dump(dict(bpm=BPM, bar=BAR, total=round(total, 3), ground=GROUND, events=EV), open("events.json", "w"), indent=0)
    from collections import Counter
    c = Counter(e["var"] for e in EV)
    print(f"{len(EV)} notes, total {total:.1f}s, per variation {8 * BAR:.1f}s:", dict(sorted(c.items())))
