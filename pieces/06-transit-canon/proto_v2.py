"""Transit Canon v2, layout prototypes (stills only). python proto_v2.py LAYOUT OUT.png T [T ...]

Every line runs the same tune; with all trains at one speed, a line's loop length is its lap time, so the four loops
are one shape at four sizes (6:4:3:2), all through Central. Stations sit at the tune's note onsets along the loop.
A phrase's stretch of track is inked the first time the line sings it; until then the route is pencil.
LAYOUT: petals (four directions out of Central) or nested (one direction, scaled out from Central).
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, "../..")
from craft import clamp01  # noqa: E402
import canon  # noqa: E402

W, H, SS = 1920, 1080, 2
GRID = 60
PAPER = (238, 230, 210)
PENCIL = (206, 196, 176)
INK = {"amber": (222, 146, 36), "teal": (18, 148, 142), "violet": (118, 78, 178), "rose": (208, 68, 94)}
FONT = "C:/Windows/Fonts/bahnschrift.ttf"
SIZE = {"violet": 6, "rose": 4, "amber": 3, "teal": 2}       # = lap time / (20/3 s): one speed for every train
# a petal-shaped loop in "beats" (perimeter ~16), Central at its tip (0, 0), pointing +x
BASE = [(0, 0), (2, -2), (5, -2), (6, -1), (6, 1), (5, 2), (2, 2), (0, 0)]
BEAT_AT = [0, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 14]          # note onsets in beats (RHYTHM)
PHRASES = [canon.P1, canon.P2, canon.P3, canon.P4]


def layout(kind):
    if kind == "petals":
        c = (16, 9.2)
        rot = {"violet": 0, "rose": 180, "amber": 270, "teal": 90}
        k = {"violet": 2.45, "rose": 2.45, "amber": 2.45, "teal": 2.45}
    else:
        c = (4.6, 9.0)
        rot = {n: 0 for n in SIZE}
        k = {n: 3.85 for n in SIZE}
    out = {}
    for n, sz in SIZE.items():
        s = sz / 6 * k[n]
        a = math.radians(rot[n])
        pts = []
        for x, y in BASE:
            x, y = x * s, y * s
            pts.append((c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a)))
        out[n] = pts
    return c, out


LANE = {"violet": 1.5, "rose": 0.5, "amber": -0.5, "teal": -1.5}   # parallel lanes on shared track (outward +)
SP = 13


class Loop:
    """A line's loop, sampled densely and offset into its lane; indexed by fraction of the lap."""

    def __init__(self, pts, lane, centre, n=1200):
        raw = [(x * GRID, y * GRID) for x, y in pts]
        cum = [0.0]
        for a, b in zip(raw, raw[1:]):
            cum.append(cum[-1] + math.dist(a, b))
        L = cum[-1]

        def at(f):
            s_ = (f % 1.0) * L
            i = max(0, min(len(cum) - 2, int(np.searchsorted(cum, s_, side="right") - 1)))
            u = (s_ - cum[i]) / max(1e-9, cum[i + 1] - cum[i])
            return (raw[i][0] + u * (raw[i + 1][0] - raw[i][0]), raw[i][1] + u * (raw[i + 1][1] - raw[i][1]))
        base = [at(k / n) for k in range(n)]
        cx, cy = centre[0] * GRID, centre[1] * GRID
        self.p = []
        for k in range(n):
            a, b = base[(k - 4) % n], base[(k + 4) % n]
            tx, ty = b[0] - a[0], b[1] - a[1]
            m = math.hypot(tx, ty) or 1
            ox, oy = ty / m, -tx / m                                   # outward (loops run clockwise on screen)
            dc = math.dist(base[k], (cx, cy))
            ramp = clamp01((dc - 14) / 46)                             # lanes merge into Central's platform
            o = lane * SP * ramp
            self.p.append((base[k][0] + ox * o, base[k][1] + oy * o))
        self.n = n
        self.pts = self.p + [self.p[0]]

    def at(self, f):
        x = (f % 1.0) * self.n
        i = int(x)
        u = x - i
        a, b = self.p[i % self.n], self.p[(i + 1) % self.n]
        return (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]))

    def sub(self, f0, f1):
        k = max(2, int((f1 - f0) * self.n))
        return [self.at(f0 + (f1 - f0) * j / k) for j in range(k + 1)]


def state(name, s):
    """(present, lap, frac in lap, learned phrase set so far) at score time s."""
    upb, octv, enter, laps = canon.LINES[name]
    lap_s = canon.LAP_U[name] * canon.U
    e = enter * canon.U
    if s < e:
        return False, 0, 0.0, set()
    x = s - e
    conv = canon.T_CONV_U * canon.U
    if s > conv:
        x -= min(s - conv, canon.DWELL_S)
    lap = int(x // lap_s)
    frac = (x % lap_s) / lap_s
    learned = set()
    for j in range(min(lap + 1, laps)):
        sung = canon.LEVELS[canon.LEARN[name][j]]
        for P in PHRASES:
            if P <= sung and (j < lap or frac >= BEAT_AT[min(P)] / 16):
                learned |= P
    if lap >= laps:
        learned = set(range(12))
    final = enter + (laps + 1) * canon.LAP_U[name] + canon.DWELL_U
    return s <= final * canon.U + 0.5, lap, frac, learned


def draw(kind, s):
    c, shapes = layout(kind)
    loops = {n: Loop(p, LANE[n], c) for n, p in shapes.items()}
    im = Image.new("RGB", (W * SS, H * SS), PAPER)
    d = ImageDraw.Draw(im)
    P = lambda p: (p[0] * SS, p[1] * SS)
    lw = 9 * SS
    for n, L in loops.items():
        d.line([P(p) for p in L.pts], fill=PENCIL, width=3 * SS, joint="curve")
    x, y = P((c[0] * GRID, c[1] * GRID))
    r = 30 * SS
    d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=(40, 38, 44), width=5 * SS)
    for n, L in loops.items():
        present, lap, frac, learned = state(n, s)
        for ph in PHRASES:
            if ph <= learned:
                f0 = BEAT_AT[min(ph)] / 16
                f1 = (BEAT_AT[max(ph)] + canon.RHYTHM[max(ph)]) / 16
                d.line([P(p) for p in L.sub(f0, f1)], fill=INK[n], width=lw, joint="curve")
        for k, b in enumerate(BEAT_AT):
            x, y = P(L.at(b / 16))
            r = 8 * SS
            if k in learned:
                d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=INK[n], width=3 * SS)
            else:
                d.ellipse([x - r * .6, y - r * .6, x + r * .6, y + r * .6], outline=PENCIL, width=2 * SS)
        if present:
            x, y = P(L.at(frac))
            bx, by = P(L.at(frac - 0.004))
            ang = math.atan2(y - by, x - bx)
            ca, sa = math.cos(ang), math.sin(ang)
            ln, wd = 30 * SS, 9 * SS
            box = [(x + ca * ln / 2 - sa * wd, y + sa * ln / 2 + ca * wd), (x + ca * ln / 2 + sa * wd, y + sa * ln / 2 - ca * wd),
                   (x - ca * ln / 2 + sa * wd, y - sa * ln / 2 - ca * wd), (x - ca * ln / 2 - sa * wd, y - sa * ln / 2 + ca * wd)]
            d.polygon(box, fill=INK[n], outline=tuple(int(v * .55) for v in INK[n]))
    f = ImageFont.truetype(FONT, 26 * SS)
    cx_, cy_ = P((c[0] * GRID, c[1] * GRID))
    d.text((cx_ - 60 * SS, cy_ - 80 * SS), "CENTRAL", font=f, fill=(60, 56, 50))
    d.text((W * SS - 420 * SS, 30 * SS), f"{kind}  t={s:.0f}s", font=f, fill=(120, 110, 100))
    return im.resize((W, H), Image.LANCZOS)


if __name__ == "__main__":
    kind, out = sys.argv[1], sys.argv[2]
    ts = [float(x) for x in sys.argv[3:]]
    ims = [draw(kind, t) for t in ts]
    cols = 3
    tw, th = 640, 360
    sheet = Image.new("RGB", (tw * cols, th * math.ceil(len(ims) / cols)), (255, 255, 255))
    for k, im in enumerate(ims):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
    sheet.save(out)
    ims[min(4, len(ims) - 1)].save(out.replace(".png", "_big.png"))
