"""Tidal Clock: the harbour simulation that composes the piece. Writes events.json.

Water height h(x, t) = tide(t) * sum_k A_k sin(k_k x - w_k t + p_k), with deep-water dispersion
w = sqrt(g k). x is in metres across the harbour (0 = mouth, 120 = quay).
"""
import json
import math

import numpy as np

G = 9.81
TOTAL = 180.0
HARBOUR = 120.0
# (wavelength m, amplitude m, phase): close wavelengths beat -> sets of waves
TRAINS = [(34.0, 0.34, 0.0), (24.0, 0.28, 1.7), (46.0, 0.16, 4.1), (12.0, 0.05, 2.2)]   # 34 vs 24 m beat in ~25 s sets
K = np.array([2 * math.pi / L for L, _, _ in TRAINS])
W = np.sqrt(G * K)
A = np.array([a for _, a, _ in TRAINS])
P = np.array([p for _, _, p in TRAINS])

PENTA = [0, 2, 4, 7, 9]
ROOT = 50            # D3
# boats: (x metres, scale step, threshold as a fraction of the local maximum swell, name)
BOATS = [(8, 0, 0.62, "Maud"), (17, 1, 0.56, "Kittiwake"), (25, 2, 0.5, "Brown Bess"), (33, 3, 0.47, "Tern"),
         (42, 4, 0.44, "Little Owl"), (50, 5, 0.42, "Mary Ann"), (59, 6, 0.4, "Heron"), (67, 7, 0.38, "Dulcie"),
         (76, 8, 0.36, "Swift"), (85, 9, 0.35, "Periwinkle"), (95, 10, 0.34, "Wren"), (106, 11, 0.33, "Jenny")]
LIGHT_PERIOD = 12.0


def tide(t):
    """Sea state envelope: calm dusk, rising to a swell at ~110 s, easing to a still night."""
    rise = 0.35 + 0.65 * (0.5 - 0.5 * math.cos(math.pi * min(t, 110) / 110))
    fall = 1.0 if t < 120 else 0.2 + 0.8 * max(0.0, 1 - (t - 120) / 45) ** 1.5
    return rise * fall


def height(x, t):
    return tide(t) * float(np.sum(A * np.sin(K * x - W * t + P)))


def slope(x, t):
    return tide(t) * float(np.sum(A * K * np.cos(K * x - W * t + P)))


def midi(step):
    o, i = divmod(step, len(PENTA))
    return ROOT + 12 * o + PENTA[i]


def simulate(dt=1 / 240):
    amax = float(A.sum())
    ev = []
    last_ring = [-9.0] * len(BOATS)
    last_tick = [-9.0] * len(BOATS)
    prev = [height(b[0], 0) for b in BOATS]
    t = 0.0
    while t < TOTAL:
        for i, (x, step, thr, name) in enumerate(BOATS):
            h = height(x, t)
            th = thr * amax * tide(t) ** 0.45
            if prev[i] < th <= h and t - last_ring[i] > 1.2:
                v = min(0.9, 0.45 + 0.6 * (tide(t) - 0.3))
                ev.append(dict(t=round(t, 4), kind="bell", boat=i, midi=midi(step), vel=round(v, 3), x=x))
                last_ring[i] = t
            s = abs(slope(x, t))
            if s > 0.095 * tide(t) ** 0.5 and t - last_tick[i] > 1.6 and tide(t) > 0.7:
                ev.append(dict(t=round(t, 4), kind="tick", boat=i, vel=round(min(0.7, s * 4), 3), x=x))
                last_tick[i] = t
            prev[i] = h
        t += dt
    k = 0
    while k * LIGHT_PERIOD < TOTAL - 4:
        ev.append(dict(t=round(k * LIGHT_PERIOD + 3.0, 4), kind="light", midi=ROOT - 12, vel=0.5, x=0))
        k += 1
    ev.sort(key=lambda e: e["t"])
    return ev


if __name__ == "__main__":
    ev = simulate()
    json.dump(dict(total=TOTAL, boats=BOATS, trains=TRAINS, events=ev), open("events.json", "w"), indent=0)
    bells = [e for e in ev if e["kind"] == "bell"]
    ticks = [e for e in ev if e["kind"] == "tick"]
    print(f"{len(bells)} bells, {len(ticks)} ticks")
    for a in range(0, int(TOTAL), 15):
        print(f"{a:3d}s bells {sum(1 for e in bells if a <= e['t'] < a + 15):3d}  ticks {sum(1 for e in ticks if a <= e['t'] < a + 15):3d}"
              f"  tide {tide(a):.2f}")
    print("wave periods (s):", [round(2 * math.pi / w, 2) for w in W], " speeds (m/s):", [round(w / k, 1) for w, k in zip(W, K)])
