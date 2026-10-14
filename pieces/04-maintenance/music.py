"""Maintenance v5: a composed score, written to the story's cues (cues.py).

D minor, 3/4, one beat per second, so bars line up with the rituals. Materials:
  * the turn: a three-note motif (A4 D5 C5) for the tap handle, reused for each ritual;
  * the routine: a patient waltz-like left hand under the rituals (the plants doing their jobs);
  * the gardener's theme: an 8-bar melody that arrives with the gloves, returns alone and high where
    the old hum was, and turns to D major as the replica lifts the can and pours.
Synth piano (piece 2, which Muga prefers to the sampled one) + a soft string pad + the ambience, mastered.

    python music.py   ->  E:/Claude/music-video-2-work/04/maintenance_v5.wav
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

import cues as C

sys.path.insert(0, "../02-player-piano")
sys.path.insert(0, "../..")
from piano import SR, render, room  # noqa: E402
from master import master  # noqa: E402

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def m(n):
    pc = NOTE[n[0]] + (1 if "#" in n else -1 if "b" in n[1:2] else 0)
    return 12 * (int(n[-1]) + 1) + pc


EV = []     # (t, midi, vel, dur)
PAD = []    # (t0, t1, [midis], level)


def put(t, notes, vel, dur):
    for n in notes.split():
        EV.append((t, m(n), vel, dur))


THEME = [  # (notes in beats) the gardener's theme, minor
    [("A4", 2), ("D5", 1)], [("C5", 1.5), ("Bb4", 0.5), ("A4", 1)], [("G4", 2), ("F4", 1)], [("E4", 3)],
    [("F4", 1), ("G4", 1), ("A4", 1)], [("Bb4", 2), ("A4", 1)], [("G4", 1), ("F4", 1), ("E4", 1)], [("D4", 3)]]
HARM = ["D3 A3 F4", "C3 A3 F4", "G2 D3 Bb3", "A2 E3 C#4", "D3 A3 F4", "Bb2 F3 D4", "G2 D3 Bb3", "D3 A3 F4"]
HARM_MAJ = ["D3 A3 F#4", "C#3 A3 E4", "G2 D3 B3", "A2 E3 C#4", "D3 A3 F#4", "G2 D3 B3", "A2 E3 G3", "D3 A3 F#4"]


def theme(t0, bars, shift=0, vel=0.5, major=False, bar=3.0):
    for b in bars:
        t = t0 + (b - bars[0]) * bar
        for n, beats in THEME[b]:
            if major:
                n = n.replace("F4", "F#4").replace("Bb4", "B4")
            mm = m(n) + shift
            EV.append((t, mm, vel * (1.1 if beats >= 2 else 1.0), beats * bar / 3 * 0.98))
            t += beats * bar / 3


def chords(t0, bars, vel=0.3, major=False, pattern="waltz", bar=3.0):
    H = HARM_MAJ if major else HARM
    for b in bars:
        t = t0 + (b - bars[0]) * bar
        ns = H[b].split()
        if pattern == "waltz":            # bass on 1, chord on 2 and 3: the routine
            put(t, ns[0], vel * 1.1, bar / 3 * 0.95)
            put(t + bar / 3, " ".join(ns[1:]), vel * 0.8, bar / 3 * 0.9)
            put(t + 2 * bar / 3, " ".join(ns[1:]), vel * 0.75, bar / 3 * 0.9)
        else:                              # held
            put(t, " ".join(ns), vel, bar * 0.98)


# 0-19 s: the empty glasshouse, single notes between the drips
for t, n, v in [(3.0, "D5", 0.28), (8.0, "A4", 0.25), (13.0, "F5", 0.24), (16.5, "E5", 0.22)]:
    put(t, n, v, 3.0)
PAD.append((2.0, 19.0, ["D3", "A3"], 0.25))

# 19-31 s: the tap. The turn motif as the handle turns; the stream as a soft rippling figure
put(C.TAP_GRIP, "D4", 0.3, 2.0)
for k, n in enumerate(["A4", "D5", "C5"]):
    put(C.TAP_TURN[0] + k * 0.7, n, 0.42, 1.2)
t = C.STREAM[0]
while t < C.STREAM[1]:
    for k, n in enumerate(["D6", "A5", "F5", "A5"]):
        put(t + k * 0.25, n, 0.16, 0.5)
    t += 1.0

# 33-57 s: the routines. The waltz under the rituals; the turn motif on the pot nudge and the pane prop
chords(33.0, list(range(8)), vel=0.26)
for tt in (C.POT_NUDGE[0], C.PANE_PROP[0]):
    for k, n in enumerate(["A4", "D5", "C5"]):
        put(tt + k * 0.7, n, 0.36, 1.1)
PAD.append((33.0, 57.0, ["D3", "F3", "A3"], 0.3))

# 58-86 s: the gloves. The gardener's theme arrives and grows with the replica
put(C.GLOVE_FIND, "D5 A5", 0.35, 2.5)
theme(60.0, list(range(8)), vel=0.48)
chords(60.0, list(range(8)), vel=0.24)
PAD.append((60.0, 86.0, ["D3", "A3", "F4"], 0.45))

# 86-90 s: a held A, waiting
put(86.0, "A2 E3 A3 C#4", 0.3, 4.0)
PAD.append((86.0, 90.0, ["A2", "E3", "C#4"], 0.35))

# 90-108 s: the remembered moment (where the hum was): the theme alone, an octave up, a little slower
theme(90.0, list(range(6)), shift=12, vel=0.4, bar=3.0)
PAD.append((90.0, 108.0, ["D3", "A3"], 0.2))

# 108-112 s: gathering. An A pedal, rising
for k, n in enumerate(["A3", "C#4", "E4", "A4", "C#5", "E5"]):
    put(108.0 + k * 0.6, n, 0.25 + 0.05 * k, 2.0)

# 112-121 s: the lift and the pour. The theme's second half in D MAJOR, full and warm
theme(C.LIFT[0], [4, 5, 6], shift=12, vel=0.62, major=True, bar=3.0)
theme(C.LIFT[0], [4, 5, 6], shift=0, vel=0.45, major=True, bar=3.0)
chords(C.LIFT[0], [4, 5, 6], vel=0.4, major=True, pattern="held")
put(C.LIFT[0] + 9.0, "D2 D3 A3 F#4 D5", 0.55, 5.0)
PAD.append((C.LIFT[0], 124.0, ["D3", "A3", "F#4", "D5"], 0.6))

# 122-140 s: dawn. Falling D major arpeggios thin out; the last drop is the last high note
for k, (tt, n) in enumerate([(124.0, "A5"), (124.6, "F#5"), (125.2, "D5"), (125.8, "A4")]):
    put(tt, n, 0.3 - 0.03 * k, 2.5)
put(C.LAST_DROP, "D6", 0.34, 4.0)
put(131.0, "D2 A2 D3 F#3 A3", 0.32, 8.0)
PAD.append((124.0, 139.0, ["D3", "A3", "F#4"], 0.3))


def pad(total):
    """A soft string pad: detuned saws, low-passed, slow bow in and out."""
    n = int(total * SR)
    out = np.zeros(n)
    t = np.arange(n) / SR
    for t0, t1, ns, lvl in PAD:
        i0, i1 = int(t0 * SR), min(n, int((t1 + 2.5) * SR))
        tt = t[i0:i1] - t0
        env = np.clip(tt / 2.5, 0, 1) * np.clip((t1 + 2.5 - t0 - tt) / 2.5, 0, 1) * lvl
        seg = np.zeros(i1 - i0)
        for nn in ns:
            f = 440.0 * 2 ** ((m(nn) - 69) / 12)
            for det in (-0.08, 0.08):
                seg += 2 * ((tt * f * 2 ** (det / 12)) % 1.0) - 1
        out[i0:i1] += seg * env
    return sosfilt(butter(2, 1100, "low", fs=SR, output="sos"), out)


if __name__ == "__main__":
    total = C.TOTAL
    pn = render(sorted(EV), total + 4, metal=0.35)[: int(total * SR)]
    pn /= np.abs(pn).max()
    pd = pad(total)
    pd = pd / np.abs(pd).max() * 0.22
    sr, amb = wavfile.read("E:/Claude/music-video-2-work/04/maintenance_ambient.wav")
    amb = amb.astype(np.float64) / 32768
    amb = amb[: int(total * SR)]
    if amb.ndim == 1:
        amb = np.stack([amb, amb], 1)
    amb = np.pad(amb, ((0, int(total * SR) - len(amb)), (0, 0)))
    mix = pn * 0.75 + pd[:, None] + amb / (np.abs(amb).max() + 1e-9) * 0.35
    mix = room(mix, seconds=2.6, mix=0.25)[: int(total * SR)]
    y = master(mix, target=-16.0)
    wavfile.write("E:/Claude/music-video-2-work/04/maintenance_v5.wav", SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    print(f"{len(EV)} notes, {len(y) / SR:.1f}s written")
