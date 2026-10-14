"""Transit Canon: arrivals -> notes. Writes events.json.

Pitch comes from the map: a station's height on the map picks a scale degree, and each
line adds its own octave. Because degree depends only on position, interchange stations
sound the same pitch class on every line that serves them, and Central is the tonic, so
the convergence at T_CONV is F in four octaves. Stereo pan comes from the station's x.
Lines enter one by one (the map draws itself) and leave in reverse after the convergence.
"""
import json

from netmap import NET, T_CONV

TOTAL = 170.0
SCALE = [0, 2, 4, 7, 9, 11]        # F lydian-ish hexatonic (no 4th): F G A C D E
TONIC = 53                          # F3
REGISTER = {"violet": -1, "rose": 0, "amber": 1, "teal": 2}   # octaves above/below F3
VEL = {"violet": 0.62, "rose": 0.58, "amber": 0.55, "teal": 0.5}
ENTER = {"violet": 0.0, "rose": 14.0, "amber": 30.0, "teal": 46.0}
LEAVE = {"teal": 138.0, "amber": 148.0, "rose": 156.0, "violet": 166.0}
# rush hour: a second train half a lap behind, then out of service before the meeting
RUSH = {"amber": (64.0, 110.0), "teal": (72.0, 112.0), "rose": (84.0, 108.0)}


def pitch(line, st):
    deg = (16 - st[1]) - 1            # Central (y=9) -> degree 6 -> tonic an octave up
    o, i = divmod(deg, len(SCALE))
    return TONIC + 12 * (REGISTER[line] + o - 1) + SCALE[i]


def build():
    ev = []
    for L in NET:
        arr = [(t, i, 0) for t, i in L.arrivals(ENTER[L.name], LEAVE[L.name])]
        if L.name in RUSH:
            h = L.period / 2
            a, b = RUSH[L.name]
            arr += [(t + h, i, 1) for t, i in L.arrivals(a - h, b - h)]
        arr.sort()
        for k, (t, i, train) in enumerate(arr):
            st = L.stations[i]
            nxt = arr[k + 1][0] if k + 1 < len(arr) else t + 4
            conv = abs(t - T_CONV) < 0.01
            ev.append(dict(t=round(t, 4), m=pitch(L.name, st),
                           v=round(min(0.9, VEL[L.name] * (1.35 if conv else 0.8 if train else 1.0)), 3),
                           d=round(min(4.0, max(0.6, nxt - t) * 1.3), 3),
                           line=L.name, train=train, station=i, x=st[0], y=st[1]))
    ev.sort(key=lambda e: e["t"])
    return ev


if __name__ == "__main__":
    ev = build()
    json.dump(dict(info=dict(total=TOTAL, t_conv=T_CONV), events=ev), open("events.json", "w"), indent=0)
    ms = [e["m"] for e in ev]
    print(f"{len(ev)} notes, midi {min(ms)}-{max(ms)}, {len(ev) / TOTAL:.2f}/s")
    print("at convergence:", [(e["line"], e["m"]) for e in ev if abs(e["t"] - T_CONV) < 0.01])
