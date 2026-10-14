"""The eight keepers' versions, each made from the one before by a transmission rule.

A version is a dict: notes [(degree, beats)], scale, meter, bpm, and per-note
timing jitter (free rhythm). The chronology runs forward from the shepherd; the
PARLOUR tune in tune.py is where the line settles in the middle, so the early
versions are written as its ancestors (simpler, freer) and the later ones as its
descendants.
"""
import numpy as np

from tune import PARLOUR, MAJOR

PENTA_AS_MAJOR = {3: 2, 6: 5, 10: 9, -1: -2, -4: -3}     # fa->mi, ti->la: pentatonic levelling
DORIAN = [0, 2, 3, 5, 7, 9, 10]
MIXOLYDIAN = [0, 2, 4, 5, 7, 9, 10]


def level_pentatonic(notes):
    out = []
    for d, b in notes:
        out.append((PENTA_AS_MAJOR.get(d, d), b))
    return out


def merge_repeats(notes):
    out = []
    for d, b in notes:
        if out and out[-1][0] == d:
            out[-1] = (d, out[-1][1] + b)
        else:
            out.append((d, b))
    return out


def plain_rhythm(notes):
    """Before anyone wrote it down, the dotted figure didn't exist: la. sol -> la sol."""
    out = []
    for d, b in notes:
        out.append((d, {1.5: 1.0, 0.5: 1.0}.get(b, b)))
    return out


def even_out(notes, unit=1.0):
    """Chant: every syllable the same length; long notes become two units."""
    return [(d, unit if b < 1.5 else 2 * unit) for d, b in notes]


def to_common_time(notes):
    """Shanty: 3/4 bars become 4/4 work beats: the held notes get the extra beat (the haul)."""
    out = []
    for d, b in notes:
        out.append((d, b + 1 if b >= 2 else b))
    return out


def with_response(notes, bar_beats=4, response=((0, 1), (4, 1), (0, 2))):
    """Call and response: after each 4-bar phrase the crew answers."""
    out, acc = [], 0
    for d, b in notes:
        out.append((d, b)); acc += b
        if acc >= 4 * bar_beats:
            out += [(rd, rb, 'crew') for rd, rb in response]
            acc = 0
    return out


def ornament(notes):
    """Music box: grace notes from above on long notes (tines make them free)."""
    out = []
    for d, b in notes:
        if b >= 2:
            out += [(d + 1, 0.25), (d, b - 0.25)]
        else:
            out.append((d, b))
    return out


def swing_march(notes):
    """Band: dotted rhythms on pairs of equal beats."""
    out, i = [], 0
    while i < len(notes):
        d, b = notes[i]
        if i + 1 < len(notes) and b == 1 and notes[i + 1][1] == 1:
            out += [(d, 1.5), (notes[i + 1][0], 0.5)]
            i += 2
        else:
            out.append((d, b)); i += 1
    return out


def ringtone(notes):
    """Phone: the catchiest four bars, quantised to eighths, twice as fast."""
    head = []
    acc = 0
    for d, b in notes:
        if acc >= 13:
            break
        head.append((d, max(0.5, round(b * 2) / 2) / 2)); acc += b
    return head + head


def remember(notes, rng):
    """Humming from memory: the shape survives, fussy detail is lost, the end slows down."""
    out = merge_repeats(level_pentatonic(notes))
    out = [(d, b) for d, b in out if b >= 0.5]
    return out


def child_echo(notes):
    """The child's first try: two bars, one note wrong (sol lands on la), a big breath."""
    head = notes[:6]
    return [(5 if d == 4 else d, b) for d, b in head[:4]] + head[4:]


def build(seed=7):
    rng = np.random.default_rng(seed)
    shepherd = plain_rhythm(merge_repeats(level_pentatonic(PARLOUR)))
    monks = even_out(shepherd)
    sailors = with_response(to_common_time(PARLOUR[:18]))
    musicbox = ornament(PARLOUR)
    parlour = PARLOUR
    radio = swing_march(to_common_time(PARLOUR))
    phone = ringtone(PARLOUR)
    kitchen = remember(PARLOUR, rng)
    child = child_echo(kitchen)
    return [
        dict(name='shepherd', notes=shepherd, scale=MAJOR, bpm=84, free=0.18, do=587.3),
        dict(name='monks', notes=monks, scale=DORIAN, bpm=76, free=0.03, do=196.0),
        dict(name='sailors', notes=sailors, scale=MIXOLYDIAN, bpm=112, free=0.0, do=293.7),
        dict(name='musicbox', notes=musicbox, scale=MAJOR, bpm=120, free=0.0, do=1046.5),
        dict(name='parlour', notes=parlour, scale=MAJOR, bpm=92, free=0.06, do=392.0),
        dict(name='radio', notes=radio, scale=MAJOR, bpm=126, free=0.0, do=349.2),
        dict(name='phone', notes=phone, scale=MAJOR, bpm=150, free=0.0, do=1318.5),
        dict(name='kitchen', notes=kitchen, scale=MAJOR, bpm=80, free=0.12, do=233.1),
        dict(name='child', notes=child, scale=MAJOR, bpm=60, free=0.2, do=466.2),
    ]


if __name__ == '__main__':
    for v in build():
        tot = sum(n[1] for n in v['notes'])
        print(f"{v['name']:9s} notes {len(v['notes']):3d}  beats {tot:5.1f}  secs {tot * 60 / v['bpm']:5.1f}")
