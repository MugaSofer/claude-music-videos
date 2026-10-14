"""Signal: the dialogue -> Morse -> rhythm and melody. Writes score.json.

One Morse unit = a 16th at 108 bpm. Each letter's pitch comes from its alphabet position on a
pentatonic ladder in the sender's register.
"""
import json

BPM = 120
UNIT = 60 / BPM / 4
MORSE = {"A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....", "I": "..",
         "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
         "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--.."}
PENTA = [0, 3, 5, 7, 10]                # A minor pentatonic, to sit on the A-minor chords
ROOT = {"light": 45, "boat": 57, "both": 45}           # A2.. / A3.. / both: doubled an octave up in sound.py
DIALOGUE = [
    ("light", "WHO IS OUT THERE"),
    ("boat", "A SMALL BOAT AND A TIRED CREW"),
    ("light", "THE HARBOUR IS THIS WAY"),
    ("boat", "WE SEE YOUR LIGHT"),
    ("light", "KEEP IT ON YOUR LEFT"),
    ("boat", "THANK YOU"),
    ("both", "GOODNIGHT"),
]
CHORDS = [[45, 52, 57, 60, 64], [41, 48, 57, 60, 65], [43, 50, 55, 59, 62], [45, 52, 57, 60, 64],
          [38, 45, 53, 57, 60], [40, 47, 55, 59, 62], [45, 52, 57, 61, 64]]    # Am, F, G, Am, Dm, Em, A


def pitch(sender, ch):
    k = ord(ch) - ord("A")                # 0..25 -> a ladder of ~10 steps (letters pair up)
    step = k * 10 // 26
    o, i = divmod(step, 5)
    return ROOT[sender] + 12 * o + PENTA[i]


def build():
    ev, msgs = [], []
    u = 16                                # start after 16 units (one bar) of sea
    for mi, (sender, text) in enumerate(DIALOGUE):
        u0 = u
        letters = []
        for wi, word in enumerate(text.split()):
            if wi:
                u += 7 - 3                # word gap (3 already added after the last letter)
            for ch in word:
                lu0 = u
                for k, sym in enumerate(MORSE[ch]):
                    n = 1 if sym == "." else 3
                    ev.append(dict(t=round(u * UNIT, 4), dur=round(n * UNIT, 4), kind="mark", sender=sender,
                                   msg=mi, ch=ch, sym=sym, midi=pitch(sender, ch)))
                    u += n + 1
                u += 2                    # 3-unit letter gap (1 already added)
                letters.append(dict(ch=ch, t_done=round((u - 3) * UNIT, 4), t0=round(lu0 * UNIT, 4), word=wi))
        msgs.append(dict(msg=mi, sender=sender, text=text, t0=round(u0 * UNIT, 4), t1=round(u * UNIT, 4),
                         chord=CHORDS[mi], letters=letters))
        u += 14                           # a breath between messages
    total = u * UNIT + 6
    return ev, msgs, total


if __name__ == "__main__":
    ev, msgs, total = build()
    json.dump(dict(bpm=BPM, unit=UNIT, total=round(total, 3), messages=msgs, events=ev), open("score.json", "w"), indent=0)
    print(f"{len(ev)} marks, total {total:.1f}s")
    for m in msgs:
        print(f"  {m['t0']:6.1f}-{m['t1']:6.1f}s {m['sender']:5s} {m['text']}")
