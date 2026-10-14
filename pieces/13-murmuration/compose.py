"""Murmuration: phasing pianos and a cello in E minor. Writes score.json.

Piano A loops a 12-note figure; piano B loops the same figure minus its last note (11), so the two
drift and realign. The harmony changes every 4 bars (Em, Cmaj7, G, D/F#); the figure is re-voiced
onto each chord. The cello plays long notes in the middle section.
"""
import json

BPM = 132
E8 = 60 / BPM / 2                          # an 8th note
BAR = 6 * E8                               # 6/8-ish feel: 6 eighths per bar
CHORDS = [[52, 55, 59, 64, 67, 71], [48, 55, 59, 64, 67, 71], [55, 59, 62, 67, 71, 74], [54, 57, 62, 66, 69, 74]]
FIGURE = [0, 2, 4, 5, 3, 1, 2, 4, 5, 4, 2, 3]          # indices into the current chord's 6 notes
CELLO = [(40, 8), (47, 6), (45, 6), (43, 8), (42, 6), (43, 6), (47, 8), (52, 10), (50, 6), (47, 8), (40, 14)]


def chord_at(k):
    return CHORDS[(k // (4 * 6)) % 4]       # 4 bars of 6 eighths per chord


def build():
    ev, sections = [], {}
    gather, dance, dusk = 120, 528, 120     # in 8ths: 120 = 20 bars
    end = gather + dance + dusk
    sections = dict(gather=0.0, dance=gather * E8, dusk=(gather + dance) * E8, end=end * E8)
    ka = kb = 0
    for k in range(end):
        t = k * E8
        ch = chord_at(k)
        sec = "gather" if k < gather else "dance" if k < gather + dance else "dusk"
        thin = 1.0
        if sec == "dusk":
            thin = 1 - (k - gather - dance) / dusk
        # piano A
        if sec != "dusk" or (k % 2 == 0 and thin > 0.15):
            m = ch[FIGURE[ka % 12]] + 12
            ev.append(dict(t=round(t, 4), kind="pianoA", m=m, v=round(0.42 * (0.6 + 0.4 * thin) * (1.15 if k % 6 == 0 else 1), 3),
                           d=round(E8 * 1.6, 4), sec=sec))
        ka += 1
        # piano B (11-note loop: the phasing voice) from the dance onwards
        if sec == "dance" or (sec == "dusk" and k % 3 == 0 and thin > 0.3):
            m = ch[FIGURE[kb % 11]] + 12
            ev.append(dict(t=round(t + 0.004, 4), kind="pianoB", m=m, v=round(0.34 * thin + 0.04, 3), d=round(E8 * 1.6, 4), sec=sec))
            kb += 1
        if k % 6 == 0:
            ev.append(dict(t=round(t, 4), kind="downbeat", sec=sec))
    # the cello: long notes from 1/4 of the way into the dance
    t = (gather + 24) * E8
    for m, bars in CELLO:
        d = bars * BAR
        ev.append(dict(t=round(t, 4), kind="cello", m=m, v=0.5, d=round(d * 0.97, 4), sec="dance" if t < sections["dusk"] else "dusk"))
        t += d
    # the last low piano E
    ev.append(dict(t=round(end * E8, 4), kind="pianoA", m=40, v=0.5, d=6.0, sec="dusk"))
    ev.sort(key=lambda e: e["t"])
    return ev, sections, end * E8 + 7


def phase_offset(k):
    """How far piano B is out of phase with A (0 = in phase, 1 = furthest), for the visuals."""
    gather = 120
    if k < gather:
        return 0.0
    kb = k - gather
    off = (kb % 132) * 12 / 132
    return min(off, 12 - off) / 6


if __name__ == "__main__":
    ev, sections, total = build()
    json.dump(dict(bpm=BPM, e8=E8, bar=BAR, total=round(total, 3), sections=sections, events=ev), open("score.json", "w"), indent=0)
    from collections import Counter
    print(f"{len(ev)} events, total {total:.1f}s, sections {sections}")
    print(Counter(e["kind"] for e in ev))
    cello_end = max(e["t"] + e["d"] for e in ev if e["kind"] == "cello")
    print(f"cello ends at {cello_end:.1f}s")
