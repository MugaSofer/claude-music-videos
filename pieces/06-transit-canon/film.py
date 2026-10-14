"""Transit Canon: the film. See design.md.

python film.py still OUT.png T [T ...]   -> stills (contact sheet if several)
python film.py video OUT.mp4 [T0 T1]      -> frames piped to ffmpeg (24 fps)
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, "../..")
from craft import clamp01, ease_in_out, finisher  # noqa: E402
from compose import ENTER, LEAVE, RUSH  # noqa: E402
from netmap import CENTRAL, GRID, NET, T_CONV, interchanges, route  # noqa: E402

W, H, FPS, SS = 1920, 1080, 24, 2
PAPER = (238, 230, 210)
INK = {"amber": (222, 146, 36), "teal": (18, 148, 142), "violet": (118, 78, 178), "rose": (208, 68, 94)}
GHOST = (214, 204, 184)
SP = 11                       # parallel track spacing, world px
LW = 9                        # line width, world px
FONT = "C:/Windows/Fonts/bahnschrift.ttf"
EV = json.load(open("events.json"))["events"]
TOTAL = 175.0
IX = interchanges()

NAMES = ["Lantern Row", "Low Tide", "Quiet Hill", "Night Bakery", "Old Signal", "Kettle Lane",
         "Glasshouse", "Tannery", "Owl Street", "Ferry Steps", "Clocktower", "Mill Pond",
         "Chapel Yard", "Paper Mill", "North Gate", "Rook Green", "Lamplighters", "Harbour",
         "Weavers", "Salt Market", "Orchard", "Kiln Road", "Bellfounders", "Canal Basin",
         "Starling", "Coldharbour", "Hatters", "Nightjar", "Ropewalk", "Foundry", "Marsh End",
         "Well Close", "Printers", "Coal Drops", "Signal Box", "Wren Park"]


# ------------------------------------------------------------------ geometry
def unit_steps(path):
    """Expand an octilinear polyline into unit grid steps."""
    pts = [path[0]]
    for a, b in zip(path, path[1:]):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])))
        for k in range(1, n + 1):
            pts.append((a[0] + (b[0] - a[0]) * k // n, a[1] + (b[1] - a[1]) * k // n))
    return pts


class Track:
    """A line's drawable path: offset polyline in world px, indexed by original arc length."""

    def __init__(self, L, usage):
        self.L = L
        g = unit_steps(L.path)
        self.grid = g
        edges = list(zip(g, g[1:]))
        offs = []
        for a, b in edges:
            users = usage[frozenset((a, b))]
            k = users.index(L.name)
            o = (k - (len(users) - 1) / 2) * SP
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy)
            offs.append((-dy / n * o, dx / n * o))
        pv = []
        for i, p in enumerate(g):
            e = [offs[j] for j in (i - 1, i) if 0 <= j < len(offs)]
            ox = sum(v[0] for v in e) / len(e)
            oy = sum(v[1] for v in e) / len(e)
            pv.append((p[0] * GRID + ox, p[1] * GRID + oy))
        self.pv = pv
        s = [0.0]
        for a, b in edges:
            s.append(s[-1] + math.dist(a, b))
        self.s = np.array(s)
        self.length = s[-1]
        self.st_pos = [self.at(x) for x in L.st_s]

    def at(self, s):
        s = s % self.length
        i = int(np.searchsorted(self.s, s, side="right") - 1)
        i = min(i, len(self.pv) - 2)
        u = (s - self.s[i]) / (self.s[i + 1] - self.s[i])
        a, b = self.pv[i], self.pv[i + 1]
        return (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]))

    def sub(self, s0, s1, step=0.25):
        """Polyline from arc s0 to s1 (s1 may exceed length: wraps)."""
        if s1 <= s0:
            return []
        n = max(2, int((s1 - s0) / step) + 1)
        return [self.at(s) for s in np.linspace(s0, s1, n)]

    def train_s(self, t, lag=0.0):
        return self.L.frac(t - lag) * self.length


def build_tracks():
    usage = {}
    for L in NET:
        g = unit_steps(L.path)
        for a, b in zip(g, g[1:]):
            usage.setdefault(frozenset((a, b)), []).append(L.name)
    return {L.name: Track(L, usage) for L in NET}


TR = build_tracks()
ALL_ST = sorted({s for L in NET for s in L.stations}, key=lambda p: (p[1], p[0]))
NAME = {s: ("Central" if s == CENTRAL else NAMES[i % len(NAMES)]) for i, s in enumerate(ALL_ST)}

# first arrival (stamp time) per (line, station index); arrivals by station for pulses
FIRST = {}
for e in EV:
    FIRST.setdefault((e["line"], e["station"]), e["t"])
HITS = {}
for e in EV:
    HITS.setdefault((e["x"], e["y"]), []).append((e["t"], e["line"], e["train"]))


# ------------------------------------------------------------------ camera
def camera(t):
    """(centre_x, centre_y in world px, zoom)."""
    L0 = TR["violet"]
    tx, ty = L0.at(L0.train_s(t))
    cx, cy = CENTRAL[0] * GRID, CENTRAL[1] * GRID
    mid = (16 * GRID, 9 * GRID)
    keys = [  # (time, follow-weight, zoom, target)
        (0, 1.0, 2.6, None), (14, 0.7, 2.0, None), (30, 0.35, 1.45, None), (48, 0.0, 1.02, mid),
        (96, 0.0, 1.0, mid), (120, 0.0, 1.85, (cx, cy)), (132, 0.0, 1.2, mid), (175, 0.0, 0.8, mid)]
    for (a, fa, za, pa), (b, fb, zb, pb) in zip(keys, keys[1:]):
        if a <= t <= b:
            u = ease_in_out((t - a) / (b - a))
            f = fa + (fb - fa) * u
            z = za * (zb / za) ** u
            pa_ = pa or mid
            pb_ = pb or mid
            base = (pa_[0] + (pb_[0] - pa_[0]) * u, pa_[1] + (pb_[1] - pa_[1]) * u)
            x = base[0] * (1 - f) + tx * f
            y = base[1] * (1 - f) + ty * f
            dx = 22 * math.sin(t * 0.05) * (1 - f)
            dy = 12 * math.sin(t * 0.037 + 1) * (1 - f)
            return x + dx, y + dy, z
    return mid[0], mid[1], 0.8


# ------------------------------------------------------------------ drawing
def frame(t):
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
    # ghost of the whole network (faint pencil), fading in during the intro
    ghost_a = clamp01(t / 40) * 0.5
    if ghost_a > 0:
        gc = tuple(int(PAPER[i] + (GHOST[i] - PAPER[i]) * ghost_a) for i in range(3))
        for T in TR.values():
            d.line([P(p) for p in T.pv], fill=gc, width=max(1, int(2 * S)), joint="curve")

    # inked track: first lap lays it; after LEAVE it fades back to ghost
    for name, T in TR.items():
        e0 = ENTER[name]
        if t < e0:
            continue
        col = INK[name]
        fade = clamp01((t - LEAVE[name] - 2) / 6)
        col = tuple(int(col[i] + (GHOST[i] - col[i]) * fade * 0.85) for i in range(3))
        s0 = T.train_s(e0)
        laid = min(T.length, (t - e0) / T.L.period * T.length)
        pts = T.sub(s0, s0 + laid)
        if len(pts) > 1:
            d.line([P(p) for p in pts], fill=col, width=lw, joint="curve")

    # stations: stamped on first arrival, pulse on each arrival
    font = ImageFont.truetype(FONT, max(8, int(15 * S)))
    for name, T in TR.items():
        for i, st in enumerate(T.L.stations):
            ts = FIRST.get((name, i))
            if ts is None or t < ts or st in IX:
                continue
            x, y = P(T.st_pos[i])
            k = back_pop(t - ts)
            r = 7 * S * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=INK[name], width=max(1, int(3 * S)))
    for st in IX:
        ts = min((FIRST.get((n, TR[n].L.stations.index(st)), 1e9) for n in IX[st]), default=1e9)
        if t < ts:
            continue
        x, y = P((st[0] * GRID, st[1] * GRID))
        big = 1.35 if st == CENTRAL else 1.0
        r = 15 * S * back_pop(t - ts) * big
        d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=(40, 38, 44), width=max(2, int(4 * S)))

    # labels (after stamping), brightened by recent arrivals
    for st in ALL_ST:
        hs = [h for h in HITS.get(st, []) if h[0] <= t]
        if not hs:
            continue
        age = t - hs[-1][0]
        a = clamp01((t - hs[0][0]) / 0.6)
        glowk = math.exp(-age / 1.2)
        c = int(150 - 110 * glowk)
        x, y = P((st[0] * GRID, st[1] * GRID))
        col = (c, c - 4, c - 10) if a >= 1 else tuple(int(PAPER[i] + ((c, c - 4, c - 10)[i] - PAPER[i]) * a) for i in range(3))
        off = 1.6 if st == CENTRAL else 1.0
        d.text((x + 20 * S * off, y - 26 * S * off - (8 * S if st == CENTRAL else 0)), NAME[st].upper() if st == CENTRAL else NAME[st], font=font, fill=col)

    # arrival pulses: coloured ink rings spreading on the paper
    for st, hs in HITS.items():
        for (th, line, train) in hs:
            age = t - th
            if 0 <= age < 1.6:
                x, y = P((st[0] * GRID, st[1] * GRID))
                r = (14 + 70 * ease_out(age / 1.6)) * S
                a = (1 - age / 1.6) ** 1.5 * (0.55 if train else 0.9)
                c = tuple(int(PAPER[i] + (INK[line][i] - PAPER[i]) * a) for i in range(3))
                d.ellipse([x - r, y - r, x + r, y + r], outline=c, width=max(1, int((2 + 4 * (1 - age / 1.6)) * S)))
    for name, T in TR.items():
        trains = []
        last = max(e["t"] for e in EV if e["line"] == name and e["train"] == 0)
        if ENTER[name] <= t <= last + 0.6:
            trains.append((0.0, 1.0))
        if name in RUSH:
            h = T.L.period / 2
            t1 = [e["t"] for e in EV if e["line"] == name and e["train"] == 1]
            if t1 and t1[0] - 1.5 <= t <= t1[-1] + 0.6:
                trains.append((h, 0.7))
        for lag, size in trains:
            s = T.train_s(t, lag)
            p = T.at(s)
            back = T.at(s - 0.35)
            gx, gy = G(p)
            rg = 16 * S / 4 * size
            gd.ellipse([gx - rg, gy - rg, gx + rg, gy + rg], fill=(90, 70, 30))
            x, y = P(p)
            bx, by = P(back)
            ang = math.atan2(y - by, x - bx)
            ca, sa = math.cos(ang), math.sin(ang)

            def box(ln, wd):
                return [(x + ca * ln / 2 - sa * wd, y + sa * ln / 2 + ca * wd),
                        (x + ca * ln / 2 + sa * wd, y + sa * ln / 2 - ca * wd),
                        (x - ca * ln / 2 + sa * wd, y - sa * ln / 2 - ca * wd),
                        (x - ca * ln / 2 - sa * wd, y - sa * ln / 2 + ca * wd)]
            dark = tuple(int(v * 0.55) for v in INK[name])
            d.polygon(box(30 * S * size, 9 * S * size), fill=INK[name], outline=dark)
            d.polygon(box(22 * S * size, 3.2 * S * size), fill=(255, 244, 205))
            # headlamp
            hx, hy = x + ca * 15 * S * size, y + sa * 15 * S * size
            hr = 2.6 * S * size
            d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(255, 250, 225))

    # convergence: four ink rings leave Central at different speeds; a wave passes the stations
    if T_CONV - 0.2 <= t < T_CONV + 9:
        age = t - T_CONV
        cxw, cyw = CENTRAL[0] * GRID, CENTRAL[1] * GRID
        x, y = P((cxw, cyw))
        if age >= 0:
            for k, name in enumerate(["violet", "rose", "amber", "teal"]):
                u = clamp01(age / (3.5 + 1.2 * k))
                if u >= 1:
                    continue
                r = (30 + (500 + 160 * k) * ease_out(u)) * S
                a = (1 - u) ** 1.2
                c = tuple(int(PAPER[q] + (INK[name][q] - PAPER[q]) * a) for q in range(3))
                d.ellipse([x - r, y - r, x + r, y + r], outline=c, width=max(1, int((3 + 6 * (1 - u)) * S)))
            front = age * 240
            for st in ALL_ST:
                dist = math.dist((st[0] * GRID, st[1] * GRID), (cxw, cyw))
                k = math.exp(-((dist - front) / 40) ** 2) * math.exp(-age / 5)
                if k > 0.05:
                    sx, sy = P((st[0] * GRID, st[1] * GRID))
                    rr = (12 + 14 * k) * S
                    c = tuple(int(PAPER[q] + ((60, 50, 40)[q] - PAPER[q]) * k) for q in range(3))
                    d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], outline=c, width=max(1, int(3 * S)))
        gx, gy = G((cxw, cyw))
        a = clamp01(1 - abs(age) / 0.2) if age < 0 else math.exp(-age / 1.2)
        rr = 70 * S / 4
        gd.ellipse([gx - rr, gy - rr, gx + rr, gy + rr], fill=(int(120 * a), int(100 * a), int(60 * a)))

    # legend (bottom left) and title cartouche (top right), in world space
    lf = ImageFont.truetype(FONT, max(8, int(14 * S)))
    tf = ImageFont.truetype(FONT, max(8, int(20 * S)))
    x0, y0 = P((0.45 * GRID, 14.7 * GRID))
    x1, y1 = P((4.7 * GRID, 17.55 * GRID))
    la = clamp01((t - 1) / 3)
    if la > 0:
        def mix(c, a):
            return tuple(int(PAPER[q] + (c[q] - PAPER[q]) * a) for q in range(3))
        d.rectangle([x0, y0, x1, y1], outline=mix((60, 56, 50), la), width=max(1, int(2 * S)))
        d.text((x0 + 10 * S, y0 + 8 * S), "NIGHT NETWORK", font=tf, fill=mix((40, 38, 36), la))
        for k, name in enumerate(["violet", "rose", "amber", "teal"]):
            a = clamp01((t - ENTER[name]) / 1.5) * la
            if a <= 0:
                continue
            fade = clamp01((t - LEAVE[name] - 2) / 6)
            yy = y0 + (40 + 30 * k) * S
            d.line([(x0 + 12 * S, yy + 8 * S), (x0 + 52 * S, yy + 8 * S)], fill=mix(INK[name], a * (1 - 0.7 * fade)), width=lw)
            per = TR[name].L.period
            d.text((x0 + 62 * S, yy), f"{name.title()} Line  \u00b7  every {per:.1f} s", font=lf,
                   fill=mix((50, 48, 44), a * (1 - 0.6 * fade)))
        cx0, cy0 = P((26.9 * GRID, 0.35 * GRID))
        d.text((cx0, cy0), "TRANSIT CANON", font=tf, fill=mix((40, 38, 36), la))
        d.text((cx0, cy0 + 26 * S), "four loops, one meeting", font=lf, fill=mix((90, 86, 80), la))

    glow = glow.filter(ImageFilter.GaussianBlur(3)).resize(im.size, Image.BILINEAR)
    im = ImageChops.add(im, glow)
    return im.resize((W, H), Image.LANCZOS)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def back_pop(age, dur=0.35):
    if age <= 0:
        return 0.0
    if age >= dur:
        return 1.0
    x = age / dur
    s = 2.2
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


FIN = None


def finished(t, i):
    global FIN
    if FIN is None:
        from craft import Finisher, PRESETS
        FIN = Finisher(W, H, seed=7, **dict(PRESETS["paper"], paper=0.03, grain=0.018))
    return FIN(np.asarray(frame(t)).astype(np.float32) / 255.0, i)


def to_u8(x):
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "still":
        ts = [float(x) for x in sys.argv[3:]]
        ims = [Image.fromarray(to_u8(finished(t, int(t * FPS)))) for t in ts]
        if len(ims) == 1:
            ims[0].save(out)
        else:
            cols = 3
            tw, th = 640, 360
            sheet = Image.new("RGB", (tw * cols, th * math.ceil(len(ims) / cols)))
            for k, im in enumerate(ims):
                sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
            sheet.save(out)
    else:
        t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        t1 = float(sys.argv[4]) if len(sys.argv) > 4 else TOTAL
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                               "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", out],
                              stdin=subprocess.PIPE)
        for i in range(int(t0 * FPS), int(t1 * FPS)):
            ff.stdin.write(to_u8(finished(i / FPS, i)).tobytes())
            if i % 240 == 0:
                print(f"{i / FPS:.0f}s", flush=True)
        ff.stdin.close()
        ff.wait()
