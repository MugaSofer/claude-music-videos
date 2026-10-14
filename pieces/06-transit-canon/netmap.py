"""Transit Canon: the network. Lines are closed loops on a Beck-style octilinear grid.

A train runs each loop at constant speed. Arriving at a station plays that station's
note, so the map's geometry is the rhythm. Every line passes CENTRAL. Train phases are
chosen so that all trains reach Central together at T_CONV, the piece's convergence.
"""
import math

GRID = 60                      # px per grid unit at 1920x1080 (32 x 18 units)
T_CONV = 120.0
CENTRAL = (16, 9)

# name: (colour, loop period in seconds, station list in grid units, looped)
LINES = {
    "amber":  ((236, 170, 60), 23.5,
               [(6, 4), (12, 4), (16, 9), (20, 4), (24, 7), (24, 11), (21, 14), (16, 14),
                (11, 14), (6, 12), (6, 8)]),
    "teal":   ((70, 190, 180), 25.9,
               [(3, 2), (8, 2), (12, 4), (16, 9), (20, 12), (24, 11), (29, 11), (29, 16),
                (22, 16), (16, 16), (8, 16), (3, 12)]),
    "violet": ((160, 110, 220), 29.3,
               [(10, 9), (16, 9), (22, 9), (26, 5), (26, 2), (18, 2), (16, 4), (12, 7)]),
    "rose":   ((230, 100, 120), 31.7,
               [(6, 8), (11, 14), (16, 9), (21, 14), (26, 14), (29, 7), (22, 5), (16, 4),
                (10, 5)]),
}


def route(p, q):
    """Octilinear path from p to q: diagonal for the shorter axis, then straight."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    k = min(abs(dx), abs(dy))
    mid = (p[0] + k * math.copysign(1, dx) if dx else p[0],
           p[1] + k * math.copysign(1, dy) if dy else p[1])
    pts = [p]
    if mid != p and mid != q:
        pts.append(mid)
    pts.append(q)
    return pts


class Line:
    def __init__(self, name, colour, period, stations):
        self.name, self.colour, self.period, self.stations = name, colour, period, stations
        # full polyline (grid units) and the arc length of each station
        self.path = [stations[0]]
        self.st_s = [0.0]
        s = 0.0
        n = len(stations)
        for i in range(n):
            seg = route(stations[i], stations[(i + 1) % n])
            for a, b in zip(seg, seg[1:]):
                s += math.dist(a, b)
                self.path.append(b)
            if i < n - 1:
                self.st_s.append(s)
        self.length = s
        # phase: at T_CONV the train is at Central
        ci = stations.index(CENTRAL)
        self.phase = self.st_s[ci] / self.length - (T_CONV / period) % 1.0

    def frac(self, t):
        return (t / self.period + self.phase) % 1.0

    def pos(self, t):
        """Train position in grid units at time t."""
        target = self.frac(t) * self.length
        s = 0.0
        for a, b in zip(self.path, self.path[1:]):
            d = math.dist(a, b)
            if s + d >= target:
                u = (target - s) / d if d else 0
                return (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]))
            s += d
        return self.path[-1]

    def arrivals(self, t0, t1):
        """(time, station index) for every arrival in [t0, t1)."""
        out = []
        k0 = math.floor(t0 / self.period) - 1
        k1 = math.ceil(t1 / self.period) + 1
        for k in range(k0, k1 + 1):
            for i, s in enumerate(self.st_s):
                f = s / self.length - self.phase
                t = (k + f) * self.period
                if t0 <= t < t1:
                    out.append((t, i))
        return sorted(out)


NET = [Line(n, *v) for n, v in LINES.items()]


def interchanges():
    seen = {}
    for L in NET:
        for s in L.stations:
            seen.setdefault(s, []).append(L.name)
    return {s: v for s, v in seen.items() if len(v) > 1}


if __name__ == "__main__":
    for L in NET:
        print(f"{L.name:7s} stations={len(L.stations):2d} length={L.length:6.1f} "
              f"period={L.period}s  mean gap={L.period / len(L.stations):.2f}s")
    print("interchanges:", interchanges())
    # near-coincidences at interchanges (within 0.2 s), over 0-180 s
    ev = []
    for L in NET:
        for t, i in L.arrivals(0, 180):
            ev.append((t, L.stations[i], L.name))
    ev.sort()
    hits = []
    for j, (t, s, n) in enumerate(ev):
        for t2, s2, n2 in ev[j + 1:]:
            if t2 - t > 0.2:
                break
            if s2 == s and n2 != n:
                hits.append((round(t, 2), s, n, n2))
    print(f"{len(hits)} interchange meetings:")
    for h in hits:
        print("  ", h)
