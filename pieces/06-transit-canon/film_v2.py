"""Transit Canon v2: the film. v1's map and look; v2's score (canon.py, events_v2.json). See design_v2.md.

python film_v2.py still OUT.png T [T ...]   -> stills (contact sheet if several), T in real seconds
python film_v2.py video OUT.mp4 [T0 T1]      -> frames piped to ffmpeg (24 fps)
python film_v2.py pan                        -> writes each note's stop x into events_v2.json (stereo pan)
"""
import bisect
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import canon
import film as V1
from craft import clamp01, ease_in_out

W, H, FPS, SS = V1.W, V1.H, V1.FPS, V1.SS
PAPER, GHOST, INK, GRID, LW, FONT = V1.PAPER, V1.GHOST, V1.INK, V1.GRID, V1.LW, V1.FONT
TR = V1.TR
CENTRAL_W = (V1.CENTRAL[0] * GRID, V1.CENTRAL[1] * GRID)
ORDER = ["teal", "rose", "amber", "violet"]              # slowest (longest route) to fastest
BEAT_AT = [0, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 14]
PHRASES = [canon.P1, canon.P2, canon.P3, canon.P4]
S_C = {n: T.L.st_s[T.L.stations.index(V1.CENTRAL)] for n, T in TR.items()}
EVJ = json.load(open("events_v2.json"))
EV = EVJ["events"]
T_CONV = EVJ["info"]["t_conv"]                           # real time of the meeting
TOTAL = EVJ["info"]["total"] + 1.5
LAP_S = {n: canon.LAP_U[n] * canon.U for n in ORDER}

# ------------------------------------------------------------------ time: real seconds <-> score seconds
_G = np.array(canon._G)


def score_time(t):
    """Inverse of canon.warp: the score second at real second t."""
    i = int(np.searchsorted(_G, t))
    if i <= 0:
        return t
    if i >= len(_G):
        return (len(_G) - 1) * 0.01 + (t - _G[-1])
    a, b = _G[i - 1], _G[i]
    return (i - 1 + (t - a) / (b - a)) * 0.01


def line_state(name, s):
    """At score second s: (present, lap, frac, inked) where inked[k] in 0..1 is how much of phrase k is laid."""
    upb, octv, enter, laps = canon.LINES[name]
    e = enter * canon.U
    conv = canon.T_CONV_U * canon.U
    final = (enter + (laps + 1) * canon.LAP_U[name] + canon.DWELL_U) * canon.U
    if s < e:
        return False, 0, 0.0, [0.0] * 4
    x = s - e
    if s > conv:
        x -= min(s - conv, canon.DWELL_S)                # standing at Central
    if s >= final:
        return False, laps + 1, 0.0, [1.0] * 4
    lap = int(x // LAP_S[name])
    frac = (x % LAP_S[name]) / LAP_S[name]
    inked = [0.0] * 4
    for j in range(min(lap + 1, laps)):
        sung = canon.LEVELS[canon.LEARN[name][j]]
        for q, ph in enumerate(PHRASES):
            if not ph <= sung:
                continue
            f0 = BEAT_AT[min(ph)] / 16
            f1 = (BEAT_AT[max(ph)] + canon.RHYTHM[max(ph)]) / 16
            if j < lap:
                inked[q] = 1.0
            else:
                inked[q] = max(inked[q], clamp01((frac - f0) / (f1 - f0)))
    if lap >= laps:
        inked = [1.0] * 4
    return True, lap, frac, inked


def arc(name, f):
    return S_C[name] + f * TR[name].length


# ------------------------------------------------------------------ stops, interchanges, names
STOPS = {n: [TR[n].at(arc(n, b / 16)) for b in BEAT_AT] for n in ORDER}          # world px; stop 0 is Central
_pts = [(n, k, p) for n in ORDER for k, p in enumerate(STOPS[n]) if k]
GROUP = {}                                                                        # (line, k) -> group id
groups = []
for n, k, p in _pts:
    for gi, g in enumerate(groups):
        if any(m != n for m, _, _ in g) and min(math.dist(p, q) for _, _, q in g) < 0.55 * GRID \
                and all(m != n for m, _, _ in g):
            g.append((n, k, p))
            GROUP[(n, k)] = gi
            break
    else:
        groups.append([(n, k, p)])
        GROUP[(n, k)] = len(groups) - 1
GPOS = [(sum(p[0] for _, _, p in g) / len(g), sum(p[1] for _, _, p in g) / len(g)) for g in groups]
NAMES = V1.NAMES + ["Bridge Street", "Netmakers", "Larkfield", "Bakers Row", "Tidewater", "Cinder Path", "Mapmakers",
                    "Lockkeepers", "Haymarket", "Glassworks", "Cooper's Yard", "Little Venice", "Fishgate",
                    "Ironbridge", "Beacon Hill", "Woolstore"]
GNAME = [NAMES[(i * 7) % len(NAMES)] for i in range(len(groups))]
assert len(set(GNAME)) == len(GNAME)


def stop_pos(n, k):
    return CENTRAL_W if k == 0 else GPOS[GROUP[(n, k)]]


# first time each stop is sung (real time); every arrival for pulses
FIRST, HITS = {}, {}
for e in EV:
    if e.get("harmony"):
        continue
    key = ("C",) if e["note"] == 0 else ("G", GROUP[(e["line"], e["note"])])
    FIRST.setdefault(key, e["t"])
    HITS.setdefault(key, []).append((e["t"], e["line"]))
    FIRST.setdefault((e["line"], e["note"]), e["t"])
LAST = {n: max(e["t"] for e in EV if e["line"] == n) for n in ORDER}          # each line's final arrival
SIGH = min(e["t"] for e in EV if e["line"] == "violet" and T_CONV + 0.1 < e["t"] < T_CONV + 3)   # G falls to F
ECHO0 = min(e["t"] for e in EV if e.get("harmony"))


# label placement: greedy, avoiding other labels and stops
def _place_labels():
    font = ImageFont.truetype(FONT, 15)
    boxes, out = [], {}
    pts = [GPOS[g] for g in range(len(groups))] + [CENTRAL_W]
    for gi in sorted(range(len(groups)), key=lambda g: GPOS[g][1]):
        x, y = GPOS[gi]
        w = font.getlength(GNAME[gi]) + 4
        best = None
        for dx, dy in ((12, -26), (12, 8), (-12 - w, -26), (-12 - w, 8), (-w / 2, -34), (-w / 2, 14)):
            b = (x + dx, y + dy, x + dx + w, y + dy + 18)
            hit = sum(1 for c in boxes if not (b[2] < c[0] or b[0] > c[2] or b[3] < c[1] or b[1] > c[3]))
            hit += sum(1 for p in pts if p != (x, y) and b[0] - 6 < p[0] < b[2] + 6 and b[1] - 6 < p[1] < b[3] + 6)
            if best is None or hit < best[0]:
                best = (hit, (dx, dy), b)
        boxes.append(best[2])
        out[gi] = best[1]
    return out


LABEL = _place_labels()


# ------------------------------------------------------------------ camera
def camera(t):
    """(centre x, centre y in world px, zoom) at real time t."""
    T0 = TR["teal"]
    pr = line_state("teal", score_time(t))
    tx, ty = T0.at(arc("teal", pr[2])) if pr[0] else CENTRAL_W
    mid = (16 * GRID, 9 * GRID)
    c = CENTRAL_W
    keys = [  # (time, follow-weight, zoom, target)
        (0, 0.85, 2.3, None), (13, 0.6, 1.8, None), (20, 0.35, 1.4, None), (40, 0.0, 1.02, mid),
        (T_CONV - 13, 0.0, 1.0, mid), (T_CONV, 0.0, 1.75, c), (T_CONV + 9, 0.0, 1.25, mid), (TOTAL, 0.0, 0.86, mid)]
    for (a, fa, za, pa), (b, fb, zb, pb) in zip(keys, keys[1:]):
        if a <= t <= b:
            u = ease_in_out((t - a) / (b - a))
            f = fa + (fb - fa) * u
            z = za * (zb / za) ** u
            pa_, pb_ = pa or mid, pb or mid
            base = (pa_[0] + (pb_[0] - pa_[0]) * u, pa_[1] + (pb_[1] - pa_[1]) * u)
            x = base[0] * (1 - f) + tx * f
            y = base[1] * (1 - f) + ty * f
            dx = 22 * math.sin(t * 0.05) * (1 - f)
            dy = 12 * math.sin(t * 0.037 + 1) * (1 - f)
            return x + dx, y + dy, z
    return mid[0], mid[1], 0.86


def mixc(c, a, base=PAPER):
    return tuple(int(base[q] + (c[q] - base[q]) * a) for q in range(3))


# ------------------------------------------------------------------ drawing
def frame(t):
    s = score_time(t)
    cx, cy, z = camera(t)
    S = z * SS

    def P(p):
        return ((p[0] - cx) * S + W * SS / 2, (p[1] - cy) * S + H * SS / 2)

    im = Image.new("RGB", (W * SS, H * SS), PAPER)
    d = ImageDraw.Draw(im)
    glow = Image.new("RGB", (W * SS // 4, H * SS // 4), (0, 0, 0))
    gd = ImageDraw.Draw(glow)

    def G(p):
        q = P(p)
        return (q[0] / 4, q[1] / 4)

    lw = max(2, int(LW * S))
    st = {n: line_state(n, s) for n in ORDER}
    # the whole network in pencil, faintly there from the first frame
    pa = 0.55 + 0.45 * clamp01(t / 6)
    for T in TR.values():
        d.line([P(p) for p in T.pv], fill=mixc(GHOST, pa), width=max(1, int(3 * S)), joint="curve")
    # ink: each phrase laid behind the train the first time the line sings it; fades back to pencil as it leaves
    for n in ORDER:
        T = TR[n]
        fade = clamp01((t - LAST[n] - 1.5) / 7)
        col = mixc(INK[n], 1 - 0.85 * fade, GHOST)
        for q, ph in enumerate(PHRASES):
            k = st[n][3][q]
            if k <= 0:
                continue
            f0 = BEAT_AT[min(ph)] / 16
            f1 = (BEAT_AT[max(ph)] + canon.RHYTHM[max(ph)]) / 16
            pts = T.sub(arc(n, f0), arc(n, f0 + (f1 - f0) * k))
            if len(pts) > 1:
                d.line([P(p) for p in pts], fill=col, width=lw, joint="curve")
    # stops: a pencil tick until first sung, then stamped (interchanges as white rings)
    font = ImageFont.truetype(FONT, max(8, int(15 * S)))
    for gi, g in enumerate(groups):
        x, y = P(GPOS[gi])
        ts = FIRST.get(("G", gi))
        if ts is None or t < ts:
            r = 4 * S
            d.ellipse([x - r, y - r, x + r, y + r], outline=GHOST, width=max(1, int(2 * S)))
            continue
        k = V1.back_pop(t - ts)
        if len(g) > 1:
            r = 12 * S * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=(40, 38, 44), width=max(2, int(4 * S)))
        else:
            n = g[0][0]
            fade = clamp01((t - LAST[n] - 1.5) / 7)
            r = 7 * S * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=mixc(INK[n], 1 - 0.85 * fade, GHOST),
                      width=max(1, int(3 * S)))
        # label, brightened by recent arrivals
        hs = [h for h in HITS.get(("G", gi), []) if h[0] <= t]
        age = t - hs[-1][0] if hs else 99
        a = clamp01((t - ts) / 0.6)
        c = int(150 - 110 * math.exp(-age / 1.2))
        dx, dy = LABEL[gi]
        d.text((x + dx * S, y + dy * S), GNAME[gi], font=font, fill=mixc((c, c - 4, c - 10), a))
    # Central
    x, y = P(CENTRAL_W)
    ts = FIRST.get(("C",), 0)
    r = 20 * S * V1.back_pop(t - ts)
    d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=(40, 38, 44), width=max(2, int(5 * S)))
    d.text((x + 26 * S, y - 42 * S), "CENTRAL", font=ImageFont.truetype(FONT, max(8, int(19 * S))), fill=(40, 38, 36))
    # arrival pulses: ink rings spreading on the paper
    for key, hs in HITS.items():
        pos = CENTRAL_W if key == ("C",) else GPOS[key[1]]
        i0 = bisect.bisect_left([h[0] for h in hs], t - 1.6)
        for (th, n) in hs[i0:]:
            age = t - th
            if 0 <= age < 1.6:
                x, y = P(pos)
                r = (14 + 70 * V1.ease_out(age / 1.6)) * S
                a = (1 - age / 1.6) ** 1.5 * 0.85
                d.ellipse([x - r, y - r, x + r, y + r], outline=mixc(INK[n], a), width=max(1, int((2 + 4 * (1 - age / 1.6)) * S)))
    # trains
    for n in ORDER:
        present, lap, frac, inked = st[n]
        if not present:
            continue
        T = TR[n]
        sa_ = arc(n, frac)
        p, back = T.at(sa_), T.at(sa_ - 0.35)
        gx, gy = G(p)
        rg = 16 * S / 4
        gd.ellipse([gx - rg, gy - rg, gx + rg, gy + rg], fill=(90, 70, 30))
        if n == "teal" and t >= ECHO0 - 1:                   # the echo it carries: violet's glow, travelling with it
            a = clamp01((t - ECHO0 + 1) / 2) * (1 - clamp01((t - TOTAL + 4) / 3))
            re = 30 * S / 4
            gd.ellipse([gx - re, gy - re, gx + re, gy + re], fill=tuple(int(v * 0.55 * a) for v in INK["violet"]))
        x, y = P(p)
        bx, by = P(back)
        ang = math.atan2(y - by, x - bx)
        ca, sa = math.cos(ang), math.sin(ang)

        def box(ln, wd):
            return [(x + ca * ln / 2 - sa * wd, y + sa * ln / 2 + ca * wd), (x + ca * ln / 2 + sa * wd, y + sa * ln / 2 - ca * wd),
                    (x - ca * ln / 2 + sa * wd, y - sa * ln / 2 - ca * wd), (x - ca * ln / 2 - sa * wd, y - sa * ln / 2 + ca * wd)]
        d.polygon(box(30 * S, 9 * S), fill=INK[n], outline=tuple(int(v * 0.55) for v in INK[n]))
        d.polygon(box(22 * S, 3.2 * S), fill=(255, 244, 205))
        hx, hy = x + ca * 15 * S, y + sa * 15 * S
        hr = 2.6 * S
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(255, 250, 225))
    # the meeting: four rings leave Central; a wave passes over the stations; then the sigh, a smaller second pulse
    x, y = P(CENTRAL_W)
    for t0, scale, wave in ((T_CONV, 1.0, True), (SIGH, 0.45, False)):
        age = t - t0
        if not -0.2 <= age < 9:
            continue
        if age >= 0:
            for k, n in enumerate(ORDER):
                u = clamp01(age / (3.5 + 1.2 * k))
                if u >= 1:
                    continue
                r = (30 + (500 + 160 * k) * scale * V1.ease_out(u)) * S
                d.ellipse([x - r, y - r, x + r, y + r], outline=mixc(INK[n], (1 - u) ** 1.2),
                          width=max(1, int((3 + 6 * (1 - u)) * S * (0.6 + 0.4 * scale))))
            if wave:
                front = age * 240
                for gi in range(len(groups)):
                    dist = math.dist(GPOS[gi], CENTRAL_W)
                    k = math.exp(-((dist - front) / 40) ** 2) * math.exp(-age / 5)
                    if k > 0.05:
                        sx, sy = P(GPOS[gi])
                        rr = (12 + 14 * k) * S
                        d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], outline=mixc((60, 50, 40), k), width=max(1, int(3 * S)))
        gx, gy = G(CENTRAL_W)
        a = clamp01(1 - abs(age) / 0.2) if age < 0 else math.exp(-age / 1.2)
        rr = 70 * S / 4 * scale
        gd.ellipse([gx - rr, gy - rr, gx + rr, gy + rr], fill=(int(120 * a), int(100 * a), int(60 * a)))
    # legend (bottom left) and title (top right), in world space, as v1
    lf = ImageFont.truetype(FONT, max(8, int(14 * S)))
    tf = ImageFont.truetype(FONT, max(8, int(20 * S)))
    la = clamp01((t - 1) / 3)
    if la > 0:
        x0, y0 = P((0.45 * GRID, 14.7 * GRID))
        x1, y1 = P((4.95 * GRID, 17.55 * GRID))
        d.rectangle([x0, y0, x1, y1], outline=mixc((60, 56, 50), la), width=max(1, int(2 * S)))
        d.text((x0 + 10 * S, y0 + 8 * S), "NIGHT NETWORK", font=tf, fill=mixc((40, 38, 36), la))
        for k, n in enumerate(ORDER):
            e0 = canon.LINES[n][2] * canon.U
            a = clamp01((t - e0) / 1.5) * la
            if a <= 0:
                continue
            fade = clamp01((t - LAST[n] - 1.5) / 7)
            yy = y0 + (40 + 30 * k) * S
            d.line([(x0 + 12 * S, yy + 8 * S), (x0 + 52 * S, yy + 8 * S)], fill=mixc(INK[n], a * (1 - 0.7 * fade)), width=lw)
            d.text((x0 + 62 * S, yy), f"{n.title()} Line  ·  every {LAP_S[n]:.1f} s", font=lf,
                   fill=mixc((50, 48, 44), a * (1 - 0.6 * fade)))
        tx, ty = P((26.9 * GRID, 0.35 * GRID))
        d.text((tx, ty), "TRANSIT CANON", font=tf, fill=mixc((40, 38, 36), la))
        d.text((tx, ty + 26 * S), "four loops, one song", font=lf, fill=mixc((90, 86, 80), la))
    glow = glow.filter(ImageFilter.GaussianBlur(3)).resize(im.size, Image.BILINEAR)
    im = ImageChops.add(im, glow)
    return im.resize((W, H), Image.LANCZOS)


FIN = None


def finished(t, i):
    global FIN
    if FIN is None:
        from craft import Finisher, PRESETS
        FIN = Finisher(W, H, seed=7, **dict(PRESETS["paper"], paper=0.03, grain=0.018))
    fade = min(1.0, t / 1.5, max(0.0, (TOTAL - t) / 2.5))
    return FIN(np.asarray(frame(t)).astype(np.float32) / 255.0, i) * fade


def to_u8(x):
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "pan":
        for e in EV:
            p = stop_pos(e["line"], e["note"])
            e["x"], e["y"] = round(p[0] / GRID, 2), round(p[1] / GRID, 2)
        json.dump(EVJ, open("events_v2.json", "w"), indent=0)
        print("panned", len(EV), "notes by stop position;", len(groups), "stops,",
              sum(1 for g in groups if len(g) > 1), "interchanges")
    elif mode == "still":
        out = sys.argv[2]
        ts = [float(x) for x in sys.argv[3:]]
        ims = [Image.fromarray(to_u8(finished(t, int(t * FPS)))) for t in ts]
        if len(ims) == 1:
            ims[0].save(out)
        else:
            cols, tw, th = 3, 640, 360
            sheet = Image.new("RGB", (tw * cols, th * math.ceil(len(ims) / cols)))
            for k, im in enumerate(ims):
                sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
            sheet.save(out)
    else:
        out = sys.argv[2]
        t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        t1 = float(sys.argv[4]) if len(sys.argv) > 4 else TOTAL
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                               "-pix_fmt", "yuv420p", "-threads", "2", out], stdin=subprocess.PIPE)
        for i in range(int(round(t0 * FPS)), int(round(t1 * FPS))):
            ff.stdin.write(to_u8(finished(i / FPS, i)).tobytes())
            if i % 240 == 0:
                print(f"{i / FPS:.0f}s", flush=True)
        ff.stdin.close()
        ff.wait()
