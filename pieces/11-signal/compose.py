"""Signal v3: the dialogue -> Morse, now set inside a composed song. Writes score.json.

v1/v2 let the system make the music (alphabet -> pitch, one pad chord per message), and Muga found it
"slow and dull musically". v3 keeps every Morse mark exactly where it was in rhythm (the lights still
flash the real code), but the music around it is written:
  * 120 bpm 4/4, one Morse unit = a 16th, 16 units a bar; every message starts on a bar line;
  * a chord per BAR, a progression per message (A minor, turning to A major at GOODNIGHT);
  * each letter is one note whose rhythm is its code; its pitch is a chord tone picked to follow a
    melodic arch over each word (the question WHO IS OUT THERE ends rising), voice-led;
  * the breath after each message is a bar where the sea (a piano) answers and leads into the next;
  * an arrangement that builds: bass, then piano comping, then shaker and kick; a hush for THANK YOU;
    GOODNIGHT broad and major; a piano coda.
"""
import json

import numpy as np

BPM = 120
UNIT = 60 / BPM / 4
BAR = 16
MORSE = {"A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....", "I": "..",
         "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
         "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--.."}
CH = {"Am": [57, 60, 64], "F": [53, 57, 60], "C": [48, 52, 55], "G": [55, 59, 62], "E": [52, 56, 59],
      "Esus": [52, 57, 59], "Dm": [50, 53, 57], "A": [57, 61, 64], "Asus": [57, 62, 64], "Em": [52, 55, 59]}
ROOTS = {"Am": 45, "F": 41, "C": 48, "G": 43, "E": 40, "Esus": 40, "Dm": 38, "A": 45, "Asus": 45, "Em": 40}
REG = {"light": (45, 66), "boat": (60, 81), "both": (52, 72)}      # the senders' ranges
# (sender, text, progression, contour start, arch height, end gesture, level)
DIALOGUE = [
    ("light", "WHO IS OUT THERE", ["Am", "F", "C", "G"], 0.35, 0.30, +0.30, 1),
    ("boat", "A SMALL BOAT AND A TIRED CREW", ["F", "C", "G", "Am", "F", "C", "Esus", "E"], 0.45, 0.28, -0.1, 2),
    ("light", "THE HARBOUR IS THIS WAY", ["Am", "F", "C", "G"], 0.40, 0.35, 0.0, 3),
    ("boat", "WE SEE YOUR LIGHT", ["C", "G", "Am", "F"], 0.55, 0.35, +0.15, 4),
    ("light", "KEEP IT ON YOUR LEFT", ["Dm", "Am", "F", "G"], 0.45, 0.30, -0.1, 4),
    ("boat", "THANK YOU", ["F", "G"], 0.50, 0.25, -0.15, 1),
    ("both", "GOODNIGHT", ["F", "G", "Asus", "A"], 0.40, 0.45, -0.2, 5),
]
NEXT_DOM = {"Am": "E", "F": "C", "C": "G", "Dm": "A", "G": "D"}


def tones(chord, lo, hi):
    pcs = {n % 12 for n in CH[chord]}
    return [m for m in range(lo, hi + 1) if m % 12 in pcs]


def build():
    ev, msgs, bars, acc = [], [], [], []      # acc: accompaniment notes (t, midi, vel, dur, voice)
    u = 2 * BAR                               # two bars of sea and piano before the first call
    bars += [dict(u=0, chord="Am", lvl=0), dict(u=BAR, chord="Am", lvl=0)]
    prev = None
    for mi, (sender, text, prog, c0, arch, end, lvl) in enumerate(DIALOGUE):
        u0 = u
        lo, hi = REG[sender]
        letters = []
        words = text.split()
        for wi, word in enumerate(words):
            if wi:
                u += 7 - 3
            for li, ch in enumerate(word):
                bar_k = (u - u0) // BAR
                chord = prog[bar_k % len(prog)]
                x = (li + 0.5) / len(word)
                c = c0 + 0.12 * ((wi % 2) * 2 - 1) * 0.5 + arch * np.sin(np.pi * x)   # an arch per word
                if wi == len(words) - 1 and li == len(word) - 1:
                    c += end                                                      # the phrase's last gesture
                target = lo + c * (hi - lo)
                cand = tones(chord, lo, hi)
                if prev is not None and abs(prev - target) < 3:                  # voice-lead: prefer small steps
                    target = 0.6 * target + 0.4 * prev
                midi = min(cand, key=lambda m: abs(m - target))
                prev = midi
                lu0 = u
                for sym in MORSE[ch]:
                    n = 1 if sym == "." else 3
                    ev.append(dict(t=round(u * UNIT, 4), dur=round(n * UNIT, 4), kind="mark", sender=sender,
                                   msg=mi, ch=ch, sym=sym, midi=midi))
                    u += n + 1
                u += 2
                letters.append(dict(ch=ch, t_done=round((u - 3) * UNIT, 4), t0=round(lu0 * UNIT, 4), word=wi))
        u_end = u
        nb = -(-(u_end - 3 - u0) // BAR)                                          # bars the message spans
        for k in range(nb):
            bars.append(dict(u=u0 + k * BAR, chord=prog[k % len(prog)], lvl=lvl, msg=mi))
        u = u0 + nb * BAR
        msgs.append(dict(msg=mi, sender=sender, text=text, t0=round(u0 * UNIT, 4), t1=round(u_end * UNIT, 4),
                         chord=[ROOTS[prog[0]]] + CH[prog[0]], letters=letters))
        # the breath: the sea answers (1 bar; 2 before GOODNIGHT; a coda of 4 after it)
        nxt = DIALOGUE[mi + 1][2][0] if mi + 1 < len(DIALOGUE) else None
        nbreath = 2 if mi == len(DIALOGUE) - 2 else (4 if nxt is None else 1)
        for k in range(nbreath):
            if nxt is None:
                chord = ["F", "Asus", "A", "A"][k]
            elif k == nbreath - 1:
                chord = NEXT_DOM.get(nxt, "E")
            else:
                chord = prog[(nb + k) % len(prog)]
            bars.append(dict(u=u + k * BAR, chord=chord, lvl=lvl if mi != 5 else 1, breath=True, msg=mi,
                             last=(k == nbreath - 1), coda=nxt is None))
        u += nbreath * BAR
        prev = None
    total = u * UNIT + 5
    arrange(bars, acc)
    return ev, msgs, bars, acc, total


def arrange(bars, acc):
    """Bass, piano comping, the sea's answers and drums, from each bar's chord and level."""
    def put(u, m, v, d, voice):
        acc.append(dict(t=round(u * UNIT, 4), midi=int(m), vel=round(v, 3), dur=round(d * UNIT, 4), voice=voice))

    for i, b in enumerate(bars):
        u, ch, lvl = b["u"], b["chord"], b["lvl"]
        r = ROOTS[ch]
        tri = CH[ch]
        nxt = bars[i + 1]["chord"] if i + 1 < len(bars) else ch
        if b.get("coda"):
            lvl = 0
        # bass
        if lvl >= 2:
            for k, (o, d, v) in enumerate([(0, 6, 0.55), (6, 2, 0.4), (8, 6, 0.5), (14, 2, 0.4)]):   # a dotted lope
                put(u + o, r if k != 3 else ROOTS[nxt] + (1 if ROOTS[nxt] < r else -1) * 0 , v, d, "bass")
        elif lvl == 1 or (lvl == 0 and i >= 2):
            put(u, r, 0.45, 16, "bass")
        # piano comping
        if lvl in (2, 3):
            for o in (4, 12):
                for m in tri:
                    put(u + o, m, 0.26, 3, "comp")
        elif lvl >= 4:
            for o in range(0, 16, 2):                                    # broken 8ths, up and back
                m = (tri + [tri[0] + 12, tri[1] + 12])[[0, 1, 2, 3, 4, 3, 2, 1][o // 2]]
                put(u + o, m, 0.22 + 0.06 * (o % 8 == 0), 2.2, "comp")
        elif lvl == 5:
            pass
        if lvl == 5:                                                     # GOODNIGHT: broad held chords
            for m in tri + [tri[0] + 12]:
                put(u, m, 0.35, 15, "comp")
        # drums
        if lvl >= 3 and not b.get("coda"):
            for o in range(0, 16, 2):
                put(u + o, 0, 0.35 + 0.15 * (o % 4 == 0), 1, "shaker")
            for o in ((0, 8) if lvl < 5 else (0,)):
                put(u + o, 0, 0.6, 1, "kick")
            if lvl == 4:
                for o in (4, 12):
                    put(u + o, 0, 0.45, 1, "rim")
        # the sea's answer in the breaths (and the intro): a falling arpeggio that leads on
        if b.get("breath") or b["u"] < 2 * BAR:
            hi = sorted(m + 12 for m in tri)
            seq = [hi[2], hi[1], hi[0]] if not b.get("coda") else [hi[0], hi[1], hi[2]]
            for k, m in enumerate(seq):
                put(u + 4 * k, m, 0.42 - 0.04 * k, 5, "answer")
            lead = min(tones(nxt, 64, 80), key=lambda m: abs(m - seq[-1]))
            put(u + 12, lead + (2 if lead < seq[-1] else -1) if not b.get("coda") else hi[2] + 12 - 12, 0.3, 4, "answer")
            if b.get("coda") and b.get("last"):
                for m in (45, 57, 61, 64, 69, 73, 76):
                    put(u, m, 0.4, 32, "answer")


if __name__ == "__main__":
    ev, msgs, bars, acc, total = build()
    json.dump(dict(bpm=BPM, unit=UNIT, total=round(total, 3), messages=msgs, events=ev, bars=bars, acc=acc),
              open("score.json", "w"), indent=0)
    print(f"{len(ev)} marks, {len(acc)} accompaniment notes, {len(bars)} bars, total {total:.1f}s")
    for m in msgs:
        print(f"  {m['t0']:6.1f}-{m['t1']:6.1f}s {m['sender']:5s} {m['text']}")
