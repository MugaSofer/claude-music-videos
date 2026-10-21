"""Transit Canon v2 (voices renamed 10-19 so the slow bass runs the longest of v1's routes, teal): a mensuration canon. Every line plays the SAME tune, at its own speed (2:3:4:6).

One lap of a line is one statement of the tune: the train leaves Central on the tune's first note (the tonic) and
is back at Central for the next lap's first note. All lap lengths share a grid (U = 1/6 of teal's beat), and the
entries are chosen so that every line is at Central together at T_CONV, where the canon cadences on F in four
octaves. Before that, three trains meet at Central at 40 s and again at 80 s. After T_CONV each line plays one more
lap and stops at Central, fastest first (the coda), leaving teal's slow statement alone at the end.

The tune is composed with a search: melodic rules for the line itself, and the vertical harmony it makes with
itself at all four speeds at every moment of the piece. canon.py search -> tune.json; canon.py show prints the
harmony; canon.py events -> events_v2.json (the score, in the same form as v1's events.json).
"""
import json
import math
import random
import sys

U = 2.5 / 6                       # seconds per grid unit: teal's beat is 6U = 2.5 s
BEATS = 16                        # tune length in teal beats: teal lap = 40 s
SCALE = [0, 2, 4, 5, 7, 9, 11]    # F major (Bb allowed, but it must earn its place)
TONIC = 53                        # F3
# line: (units per beat, octave vs F3, entry time in units, laps before T_CONV)
LINES = {"teal": (6, -1, 0, 3), "rose": (4, 0, 32, 4), "amber": (3, 1, 48, 5), "violet": (2, 2, 96, 6)}
T_CONV_U = 288                    # 120 s
LAP_U = {k: v[0] * BEATS for k, v in LINES.items()}


RHYTHM = [1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2]   # beats per note (sums to BEATS): two phrases of 8, each ending held


def notes_of(tune):
    """tune: one scale degree per note of RHYTHM."""
    out, b = [], 0
    for ln, d in zip(RHYTHM, tune):
        out.append((b, ln, d))
        b += ln
    return out                     # (beat, length in beats, degree)


def midi(deg, octv):
    o, i = divmod(deg, 7)
    return TONIC + 12 * (octv + o) + SCALE[i]


# v3, "learning the song": each line starts knowing only the tune's long notes and learns more of it each lap; the
# last lap into Central is the first time it sings the whole thing. Then the trains stand at Central together for a
# breath (DWELL) before the coda, where they leave one by one, singing it whole.
# v5: learned phrase by phrase, so every fragment is a melody you can hold onto (v3 learned the long notes, scattered
# across the tune, and the opening sounded disconnected). Phrases: F A C- | D C A- | Bb A G A | C- E-
P1, P2, P3, P4 = {0, 1, 2}, {3, 4, 5}, {6, 7, 8, 9}, {10, 11}
LEVELS = [P1,                                # the rising opening figure
          P1 | P2,                           # the first half, rising and falling back
          P1 | P2 | P4,                      # + the way home (C, the leap down to E)
          P1 | P2 | P3 | P4]                 # + the turn in the middle: the whole tune
LEARN = {"teal": [2, 2, 3], "rose": [1, 1, 2, 3], "amber": [0, 1, 2, 3, 3], "violet": [0, 1, 1, 2, 3, 3]}   # v6: the longer a line has been travelling, the more it knows
DWELL_U = 7                                  # ~2.9 s standing at Central


def timeline(tune, coda=True):
    """Every note every line sings: (t0 units, t1 units, midi, line, lap, index, passing)."""
    ns = notes_of(tune)
    seq = [d for _, _, d in ns]
    nxt = seq[1:] + [0]
    prv = [seq[-1]] + seq[:-1]
    passing = [abs(d - a) == 1 and abs(d - b) == 1 for d, a, b in zip(seq, prv, nxt)]
    ev = []
    for name, (upb, octv, enter, laps) in LINES.items():
        total = laps + (1 if coda else 0)
        for lap in range(total):
            base = enter + lap * LAP_U[name] + (DWELL_U if lap >= laps else 0)
            sung = LEVELS[LEARN[name][lap]] if lap < laps else LEVELS[3]
            idx = sorted(sung)
            for j, k in enumerate(idx):
                b, ln, d = ns[k]
                nb = ns[idx[j + 1]][0] if j + 1 < len(idx) else BEATS        # ring on until the next sung note
                t0 = base + b * upb
                t1 = base + nb * upb
                if lap == laps and k == 0:
                    t0 -= DWELL_U                                           # the meeting chord, held through the dwell
                ev.append((t0, t1, midi(d, octv), name, lap, k, passing[k] and ln == 1 and len(idx) == 12))
        end = enter + total * LAP_U[name] + DWELL_U                         # the last arrival at Central: the tonic, held
        ev.append((end, end + 12, midi(0, octv), name, total, 0, False))
    return sorted(ev)


DISS = {1: 1.0, 2: 0.7, 6: 0.8, 10: 0.6, 11: 1.0}


def harmony_cost(tune):
    ev = timeline(tune)
    T = max(e[1] for e in ev)
    cost = 0.0
    sound = [[] for _ in range(T + 1)]
    for t0, t1, m, name, lap, k, ps in ev:
        for t in range(t0, min(t1, T + 1)):
            sound[t].append((m, t0, t1, ps))
    for t, s in enumerate(sound):
        if len(s) < 2:
            continue
        bass = min(x[0] for x in s)
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                (a, a0, a1, pa), (b, b0, b1, pb) = s[i], s[j]
                ic = abs(a - b) % 12
                w = DISS.get(ic, 0.0)
                if ic == 5 and min(a, b) == bass:                     # a fourth over the bass is a dissonance
                    w = 0.5
                if w == 0:
                    continue
                short = min(a1 - a0, b1 - b0) <= 3                      # quick notes may pass through
                treated = pa or pb                                      # a passing note: in and out by step
                fresh = t in (a0, b0)                                   # struck together, not just overlapping
                cost += w * (0.3 if short else 1.0) * (0.3 if treated else 1.0) * (1.4 if fresh else 1.0)
    return cost


def melody_cost(tune):
    ns = notes_of(tune)
    ds = [d for _, _, d in ns]
    c = 0.0
    seq = ds + [0]                                                       # the lap ends back on the tonic
    for a, b in zip(seq, seq[1:]):
        step = abs(a - b)
        c += {0: 3.0, 1: 0.0, 2: 0.7, 3: 1.0, 4: 1.2, 5: 2.5}.get(step, 6.0)
    for x, y, z in zip(seq, seq[1:], seq[2:]):                           # a leap should turn back by step
        if abs(y - x) >= 3 and not (abs(z - y) == 1 and (z - y) * (y - x) < 0):
            c += 1.5
    for x, y, z in zip(seq, seq[1:], seq[2:]):                           # no see-sawing between two notes
        if x == z and x != y:
            c += 1.0
    if len(set(d % 7 for d in ds)) < 5:                                   # use the scale, not just the triad
        c += 2.0 * (5 - len(set(d % 7 for d in ds)))
    hi, lo = max(ds), min(ds)
    if hi - lo > 9:
        c += 4 * (hi - lo - 9)
    if ds.count(hi) > 1:                                                  # one climax
        c += 2.0
    if ds[-1] not in (1, -1, 4, 6):                                       # lead back into the tonic
        c += 4.0
    c += 1.5 * sum(1 for d in ds if d % 7 == 3)                           # Bb, sparingly
    if ds[5] not in (2, 4, 1):                                            # the half-way held note: A, C or G
        c += 1.5
    return c


def cost(tune):
    return harmony_cost(tune) / 15.0 + melody_cost(tune)


def mutate(tune, rng):
    t = tune[:]
    i = rng.randrange(1, len(t))                       # note 0 stays the tonic (Central)
    if rng.random() < 0.7:
        t[i] = max(-3, min(9, t[i] + rng.choice([-2, -1, 1, 2])))
    else:
        t[i] = rng.randrange(-2, 8)
    return t


def search(seed, iters=20000):
    rng = random.Random(seed)
    tune = [0] + [rng.randrange(0, 6) for _ in range(len(RHYTHM) - 1)]
    c = cost(tune)
    best, bc = tune, c
    T = 3.0
    for k in range(iters):
        T = 3.0 * (1 - k / iters) + 0.02
        n = mutate(tune, rng)
        nc = cost(n)
        if nc < c or rng.random() < math.exp((c - nc) / T):
            tune, c = n, nc
            if c < bc:
                best, bc = tune, c
    return best, bc


NAMES = ["F", "G", "A", "Bb", "C", "D", "E"]


def spell(tune):
    out = []
    for b, ln, d in notes_of(tune):
        o, i = divmod(d, 7)
        out.append(f"{NAMES[i]}{4 + o + (i >= 4)}" + ("-" if ln == 2 else ""))
    return " ".join(out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "search":
        res = []
        for s in range(int(sys.argv[2]) if len(sys.argv) > 2 else 8):
            t, c = search(s)
            res.append((c, t))
            print(f"seed {s}: cost {c:.2f} (harmony {harmony_cost(t) / 15:.2f}, melody {melody_cost(t):.2f})  {spell(t)}",
                  flush=True)
        res.sort(key=lambda r: r[0])
        json.dump([dict(cost=c, tune=t, spelled=spell(t)) for c, t in res], open("tunes.json", "w"), indent=1)


def report(tune, limit=40):
    """Every audible clash, worst first: when, which lines, which notes, and whether one is a passing note."""
    ev = timeline(tune)
    names = {}
    T = max(e[1] for e in ev)
    clashes = {}
    for t in range(T + 1):
        s = [e for e in ev if e[0] <= t < e[1]]
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                a, b = s[i], s[j]
                ic = abs(a[2] - b[2]) % 12
                w = DISS.get(ic, 0.0)
                if ic == 5 and min(a[2], b[2]) == min(x[2] for x in s):
                    w = 0.5
                if not w:
                    continue
                key = (a[3], a[4], a[5], b[3], b[4], b[5])
                c = clashes.setdefault(key, dict(t=t, n=0, a=a, b=b, w=w))
                c["n"] += 1
    PC = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    rows = sorted(clashes.values(), key=lambda c: -c["n"] * c["w"] * (0.3 if (c["a"][6] or c["b"][6]) else 1))
    print(f"{len(rows)} clashing note pairs; total weight {sum(c['n'] * c['w'] for c in rows):.0f}")
    for c in rows[:limit]:
        a, b = c["a"], c["b"]
        tag = " (passing)" if a[6] or b[6] else ""
        print(f"  {c['t'] * U:6.1f}s  {c['n'] * U:4.1f}s long  {a[3]:>6} {PC[a[2] % 12]:<2} (note {a[5] + 1:>2}) vs "
              f"{b[3]:>6} {PC[b[2] % 12]:<2} (note {b[5] + 1:>2}){tag}")


def parse(s):
    """'F A C D C A Bb A G A G E' with an optional trailing octave mark: ' (up) , (down) on each name."""
    out = []
    for tok in s.split():
        up = tok.count("'") - tok.count(",")
        name = tok.strip("',")
        out.append(NAMES.index(name) + 7 * up)
    return out


if __name__ == "__main__" and sys.argv[1] == "check":
    t = parse(sys.argv[2])
    assert len(t) == len(RHYTHM), (len(t), len(RHYTHM))
    print(spell(t), f"   melody cost {melody_cost(t):.1f}")
    report(t, int(sys.argv[3]) if len(sys.argv) > 3 else 30)


TUNE = parse("F A C D C A Bb A G A C E,")          # v2's tune (composed by hand; checked with report())
VEL = {"teal": 0.62, "rose": 0.58, "amber": 0.55, "violet": 0.5}
PAN_X = {"teal": 9, "rose": 14, "amber": 19, "violet": 24}  # sketch only: map x (0-32) until the map is rebuilt

# v4, expression. The lines broaden together into Central (a ritardando: the trains brake), stand there, then pick up
# speed as they leave. warp() maps score seconds to real seconds; the map will use the same warp, so trains slow too.
RIT = (110.0, 120.0, 1.6)                    # from, to, how much slower at the meeting
DWELL_S = DWELL_U * U
RECOVER = 7.0                                # seconds (score time) to get back up to speed after the dwell
_G = [0.0]
for _i in range(1, 20001):                   # real time at score time i * 0.01 s
    _s = _i * 0.01
    if _s < RIT[0]:
        f = 1.0
    elif _s < RIT[1]:
        u = (_s - RIT[0]) / (RIT[1] - RIT[0])
        f = 1 + (RIT[2] - 1) * u * u * (3 - 2 * u)
    elif _s < RIT[1] + DWELL_S:
        f = RIT[2]
    else:
        u = min(1.0, (_s - RIT[1] - DWELL_S) / RECOVER)
        f = RIT[2] - (RIT[2] - 1) * u * u * (3 - 2 * u)
    _G.append(_G[-1] + 0.01 * f)


def warp(sec):
    i = min(int(sec / 0.01), len(_G) - 2)
    return _G[i] + (_G[i + 1] - _G[i]) * (sec / 0.01 - i)


if __name__ == "__main__" and sys.argv[1] == "events":
    ev = []
    conv = T_CONV_U
    ALONE_U = LINES["violet"][2] + (LINES["violet"][3] + 1) * LAP_U["violet"] + DWELL_U     # violet's last arrival: it has gone

    def add(s0, s1, m, v, name, lap, k, harm=False):
        t0, t1 = warp(s0), warp(s1)
        ev.append(dict(t=round(t0, 4), m=m, v=round(min(0.9, v), 3), d=round(t1 - t0, 3), line=name, lap=lap, note=k,
                       harmony=harm, x=PAN_X[name], y=9))

    for t0, t1, m, name, lap, k, ps in timeline(TUNE):
        upb, octv, enter, laps = LINES[name]
        s0, s1 = t0 * U, t1 * U
        final = k == 0 and lap == laps + 1
        if lap < laps:                                           # learning: lonely and soft, fuller as it knows more
            know = len(LEVELS[LEARN[name][lap]]) / 12
            v = VEL[name] * (0.68 + 0.32 * know) * (0.85 + 0.15 * s0 / 120)
        elif t0 == conv:
            v = VEL[name] * 1.25
        else:                                                    # the coda: quieter as each line goes
            v = VEL[name] * (0.85 - 0.3 * min(1.0, (s0 - 120) / 45))
        v *= 0.85 if ps else 1.0
        dur_end = s1 + (s1 - s0) * (1.5 if final else 0.15)
        if t0 == conv and name == "violet":                        # the sigh: the top line arrives a step high, then falls
            add(s0, s0 + 1.1, midi(1, octv), v, name, lap, k)
            add(s0 + 1.1, dur_end, m, v * 0.8, name, lap, k)
            continue
        add(s0, dur_end, m, v, name, lap, k)
        if name == "teal" and lap == laps and t0 >= ALONE_U:
            # once violet (the first to leave) has gone, teal sings a soft third high above itself, in violet's register:
            # the last train carries an echo of the others
            add(s0, dur_end, midi(TUNE[k] + 2, octv + 3), v * 0.42, name, lap, k, harm=True)
    ev.sort(key=lambda e: e["t"])
    total = max(e["t"] + e["d"] for e in ev)
    json.dump(dict(info=dict(total=round(total, 2), t_conv=round(warp(T_CONV_U * U), 3)), events=ev),
              open("events_v2.json", "w"), indent=0)
    print(f"{len(ev)} notes, ends {total:.1f}s; meeting at {warp(T_CONV_U * U):.1f}s real")
