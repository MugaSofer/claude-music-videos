"""Clockwork: the gear train that composes the piece. Writes events.json.

The spring gives a tempo curve; beat position b(t) is its integral. Gear g turns at 1 rev per
REV[g] beats; its pins strike when they pass the top (angle 0). Gears join at ENTER times.
"""
import json
import math

import numpy as np

TOTAL = 172.0
BPM0 = 100.0
RUN_DOWN = 118.0                 # the spring starts to give out
STOP = 163.0                     # the mechanism stops (tempo reaches ~0)
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def m(n):
    pc = NOTE[n[0]] + (1 if "#" in n else -1 if "b" in n[1:2] else 0)
    return 12 * (int(n[-1]) + 1) + pc


# name: (beats per rev, pin notes in order around the gear, entry time s, instrument)
GEARS = {
    "A": (4, ["D2", "A1", "C2", "G1"], 8.0, "bell"),
    "B": (3, ["D4", "F4", "A4", "C5", "A4", "F4"], 20.0, "tongue"),
    "C": (6, ["A3", "G3", "F3", "E3"], 32.0, "wood"),
    "D": (8, ["C5", "E5", "D5", "A4", "G4"], 44.0, "tongue"),
    "E": (2, ["A5", "G5", "E5"], 56.0, "glass"),
}


def tempo(t):
    if t < RUN_DOWN:
        return BPM0
    if t >= STOP:
        return 0.0
    u = (t - RUN_DOWN) / (STOP - RUN_DOWN)
    return BPM0 * (1 - u) ** 1.25         # the spring gives out


DT = 0.001
TS = np.arange(0, TOTAL, DT)
BEATS = np.cumsum([tempo(t) / 60 * DT for t in TS])


def beat_at(t):
    return float(np.interp(t, TS, BEATS))


def time_of_beat(b):
    return float(np.interp(b, BEATS, TS)) if b <= BEATS[-1] else None


def build():
    ev = []
    b_end = BEATS[-1]
    # escapement: tick/tock every half beat, from the start until it stops
    k = 0
    while k * 0.5 <= b_end:
        t = time_of_beat(k * 0.5)
        if t is None or t > STOP + 0.05:
            break
        ev.append(dict(t=round(t, 4), kind="esc", tock=k % 2, vel=round(0.5 * min(1, tempo(t) / BPM0 + 0.3), 3)))
        k += 1
    for g, (rev, pins, enter, inst) in GEARS.items():
        b0 = beat_at(enter)
        step = rev / len(pins)
        j = math.ceil(b0 / step)
        while j * step <= b_end:
            t = time_of_beat(j * step)
            if t is None or t > STOP:
                break
            sp = tempo(t) / BPM0
            ev.append(dict(t=round(t, 4), kind="pin", gear=g, pin=j % len(pins), midi=m(pins[j % len(pins)]),
                           inst=inst, vel=round(0.35 + 0.45 * sp ** 0.5, 3), speed=round(sp, 3)))
            j += 1
    # the last tick, after the stop
    ev.append(dict(t=STOP + 2.2, kind="esc", tock=0, vel=0.4, last=True))
    ev.sort(key=lambda e: e["t"])
    return ev


if __name__ == "__main__":
    ev = build()
    json.dump(dict(total=TOTAL, gears={g: dict(rev=r, pins=p, enter=e, inst=i) for g, (r, p, e, i) in GEARS.items()},
                   run_down=RUN_DOWN, stop=STOP, events=ev), open("events.json", "w"), indent=0)
    pins = [e for e in ev if e["kind"] == "pin"]
    print(f"{len(pins)} pin strikes, {sum(1 for e in ev if e['kind'] == 'esc')} escapement ticks, beats total {BEATS[-1]:.1f}")
    for a in range(0, int(TOTAL), 20):
        print(f"{a:3d}s pins {sum(1 for e in pins if a <= e['t'] < a + 20):3d}  tempo {tempo(a):5.1f}")
