"""Typewriter Weather: the letter -> a typing groove. Writes score.json.

Each line of the letter gets 6 bars at 96 bpm. Characters land on swung 16ths; commas and full
stops add a breath; each line ends with the margin bell ("ding", pitched to the chord's top note, so
the dings make a slow melody) and a carriage return. Each line has its own chord and weather.
"""
import json

BPM = 96
BEAT = 60 / BPM
SWING = 0.58                       # fraction of an 8th given to the first 16th
INTRO = 4 * BEAT * 2               # 2 bars: paper rolls in
LINE_BARS = 6

LETTER = [
    ("Dear you,", "none", ["F2", "A3", "C4", "E4", "G4"]),
    ("it rained here all morning, the soft kind that forgets to stop.", "rain", ["D2", "F3", "A3", "C4", "E4"]),
    ("by noon the wind had the washing flying like flags.", "wind", ["Bb1", "F3", "A3", "D4", "F4"]),
    ("then fog came in off the water and took the far houses away.", "fog", ["G2", "F3", "Bb3", "C4", "D4"]),
    ("at four the sun found one wall and stayed there, warm.", "sun", ["F2", "E3", "A3", "C4", "G4"]),
    ("they say there might be snow tonight. I hope it waits for you.", "snow", ["A1", "G3", "C4", "E4", "A4"]),
    ("the stars are out now, very small, very many.", "stars", ["D2", "F3", "A3", "C4", "E4"]),
    ("I am keeping the weather for you, all of it.", "all", ["Bb1", "A3", "D4", "F4", "C5"]),
    ("come home and I will give it back.", "home", ["C2", "Bb3", "D4", "E4", "G4"]),
    ("love, C", "none", ["F2", "A3", "C4", "E4", "F4"]),
]
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(n):
    pc = NOTE[n[0]] + (1 if "#" in n else -1 if "b" in n[1:2] else 0)
    return 12 * (int(n[-1]) + 1) + pc


def sixteenth_time(k):
    """Onset of the k-th swung 16th from 0."""
    eighth, half = divmod(k, 2)
    return eighth * BEAT / 2 + (SWING * BEAT / 2 if half else 0.0)


def build():
    ev, lines = [], []
    t_line = INTRO
    for li, (text, weather, chord) in enumerate(LETTER):
        k = 0
        typed = []
        for ch in text:
            t = t_line + sixteenth_time(k)
            kind = "space" if ch == " " else "shift" if ch.isupper() else "punct" if ch in ",." else "key"
            ev.append(dict(t=round(t, 4), kind=kind, ch=ch, line=li, col=len(typed)))
            typed.append(ch)
            k += 1
            if ch == ",":
                k += 2                 # a breath
            elif ch == ".":
                k += 4
        line_len = LINE_BARS * 16
        if k > line_len - 4:
            raise ValueError(f"line {li} too long for {LINE_BARS} bars ({k} 16ths)")
        ding_t = t_line + sixteenth_time(line_len - 4)
        ret_t = t_line + sixteenth_time(line_len - 2)
        ev.append(dict(t=round(ding_t, 4), kind="ding", midi=midi(chord[-1]) + 12, line=li))
        ev.append(dict(t=round(ret_t, 4), kind="return", line=li))
        lines.append(dict(line=li, text=text, weather=weather, t0=round(t_line, 4),
                          t1=round(t_line + LINE_BARS * 4 * BEAT, 4), chord=[midi(n) for n in chord]))
        t_line += LINE_BARS * 4 * BEAT
    total = t_line + 4 * BEAT * 3              # 3 bars: the page comes out and folds
    ev.sort(key=lambda e: e["t"])
    return ev, lines, total


if __name__ == "__main__":
    ev, lines, total = build()
    json.dump(dict(bpm=BPM, total=round(total, 3), lines=lines, events=ev), open("score.json", "w"), indent=0)
    print(f"{len(ev)} events, {len(lines)} lines, total {total:.1f}s")
    for L in lines:
        n = sum(1 for e in ev if e["line"] == L["line"] and e["kind"] not in ("ding", "return"))
        print(f"  {L['t0']:6.1f}s {L['weather']:5s} {n:2d} chars  {L['text'][:40]}")
