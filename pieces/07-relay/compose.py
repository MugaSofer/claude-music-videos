"""Relay: the real chain of hands (relay.md) -> a timed score. Writes score.json.

Each note: t (s), beat (absolute), midi, dur (s), vel, voice (instrument), hand, idx (0-25 note
index within the tune), changed (True on the note that hand altered), section.
"""
import json

BPM = 84
BEAT = 60 / BPM

SEED = ("D4:1 E4:1 F#4:1 A4:1 | G4:1.5 F#4:0.5 E4:2 | D4:1 E4:1 F#4:1 D5:1 | C5:2 A4:2 | "
        "B4:1 A4:1 G4:1 E4:1 | F#4:1.5 E4:0.5 D4:2 | E4:1 F#4:1 A4:1 C5:1 | D5:3 R:1")
NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def parse(s):
    out = []
    for tok in s.replace("|", " ").split():
        n, d = tok.split(":")
        if n == "R":
            out.append([None, float(d)])
            continue
        pc = NAMES[n[0]] + (1 if "#" in n else 0)
        out.append([12 * (int(n[-1]) + 1) + pc, float(d)])
    return out


def hand_versions():
    seed = parse(SEED)
    grok = [list(x) for x in seed]
    grok[23][0] = 71                        # bar 7 last note C5 -> B4
    gpt = [list(x) for x in grok]
    gpt[24][0] = 72                         # bar 8 D5 -> C5
    gem = [list(x) for x in gpt]            # dropped baton: unchanged
    last = [list(x) for x in gpt]
    last[25][0] = 69                        # final rest -> A4
    return {"claude": (seed, None), "grok": (grok, 23), "chatgpt": (gpt, 24),
            "gemini": (gem, None), "last": (last, 25)}


V = hand_versions()


def place(ev, hand, voice, beat0, section, vel=0.6, fermata=0.0, shift=0):
    notes, changed = V[hand]
    b = beat0
    for i, (m, d) in enumerate(notes):
        dd = d + (fermata if i == len(notes) - 2 and hand == "chatgpt" else 0)
        if m is not None:
            ev.append(dict(t=round(b * BEAT, 4), beat=b, midi=m + shift, dur=round(dd * BEAT, 4),
                           vel=round(vel * (1.25 if i == changed else 1.0), 3), voice=voice,
                           hand=hand, idx=i, changed=(i == changed), section=section))
        b += dd
    return b


def clash_score(notes, offset_beats, voices=5):
    """How many semitone/tritone clashes a round at this offset makes (lower = sweeter)."""
    def at(b):
        s = 0
        for m, d in notes:
            if s <= b < s + d:
                return m
            s += d
        return None
    total = sum(d for _, d in notes)
    bad = 0
    for k in range(int(total * 2)):
        b = k / 2
        pcs = [at((b - j * offset_beats) % total) for j in range(voices)]
        pcs = [p % 12 for p in pcs if p is not None]
        for i in range(len(pcs)):
            for j in range(i + 1, len(pcs)):
                iv = (pcs[i] - pcs[j]) % 12
                bad += iv in (1, 11, 6)
    return bad


def build(offset=6):
    ev, secs = [], []
    b = 0.0
    secs.append(("claude", b)); b = place(ev, "claude", "piano", b, 1, 0.55)
    secs.append(("grok", b)); b = place(ev, "grok", "pluck", b, 2, 0.7)
    secs.append(("chatgpt", b)); b = place(ev, "chatgpt", "organ", b, 3, 0.55, fermata=2)
    secs.append(("gemini", b)); b = place(ev, "gemini", "ghost", b, 4, 0.35) + 4
    secs.append(("last", b)); b = place(ev, "last", "piano", b, 5, 0.6)
    # the round: each version on its own instrument, entering `offset` beats apart
    secs.append(("round", b))
    # registers spread so the clashes blur rather than grind (organ below, ghost above)
    order = [("claude", "piano", 0), ("grok", "pluck", 0), ("chatgpt", "organ", -12), ("gemini", "ghost", 12),
             ("last", "piano", 0)]
    ends = []
    for j, (hand, voice, sh) in enumerate(order):
        ends.append(place(ev, hand, voice, b + j * offset, 6, 0.42 if voice != "ghost" else 0.3, shift=sh))
    b = max(ends)
    ev.append(dict(t=round(b * BEAT, 4), beat=b, midi=50, dur=6.0, vel=0.5, voice="piano", hand="last",
                   idx=-1, changed=False, section=7))   # home: a low D
    ev.sort(key=lambda e: e["t"])
    return ev, secs, (b + 8) * BEAT


if __name__ == "__main__":
    last = V["last"][0]
    for off in (4, 6, 8, 12, 16):
        print(f"round offset {off:2d} beats: {clash_score(last, off)} clashes")
    ev, secs, total = build()
    json.dump(dict(bpm=BPM, total=total, sections=[(h, round(b * BEAT, 3)) for h, b in secs], events=ev),
              open("score.json", "w"), indent=0)
    print(f"{len(ev)} notes, total {total:.1f}s; sections:", [(h, round(b * BEAT, 1)) for h, b in secs])
