"""Nurse: "A nurse is counting someone's breaths and writes down that they're okay".

A hospital facade at night (rows of dim panes, one cool corridor light, a blue H sign on the roof).
We look into one warm ward window: an over-bed lamp, an old patient asleep under a blue blanket that
rises and falls, a monitor with a green trace that blips once a second, a drip stand, a privacy curtain
that breathes. The nurse stands behind the bed in profile: she watches the chest and taps her pen on
each breath, then writes a line on her clipboard, then looks back at the patient.

Everything loops every 8 s (the film keeps the nurse running in the background with tl = 3 + t % 8).
"""
import math
from functools import lru_cache

TAU = 2 * math.pi
LOOP = 8.0

# palette (STYLE.md) and derived tones
INK = (21, 26, 51)
INDIGO = (31, 37, 80)
NAVY = (42, 47, 94)
MID = (59, 63, 116)
GOLD = (255, 201, 120)
WARMW = (255, 216, 154)
RED = (184, 57, 46)
PAPER = (239, 230, 210)
DBLUE = (159, 182, 216)

FACADE = (58, 64, 110)
BAND = (70, 76, 124)
FRAME = (92, 98, 146)
PANE = (30, 35, 70)
WALL = (128, 88, 80)
SKIN = (140, 90, 72)
SKIN_P = (214, 158, 128)          # the patient, paler
HAIR = (62, 40, 42)
SCRUB = (58, 78, 138)
TRACE = (140, 240, 170)


# ------------------------------------------------------------------ small geometry kit
def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def P(pts, col):
    return ('poly', [(float(x), float(y)) for x, y in pts], col)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def ell(cx, cy, rx, ry, n=22, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for i in range(n):
        a = TAU * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def rot(pts, ang, ox, oy):
    c, s = math.cos(ang), math.sin(ang)
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in pts]


def move(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def seg(a, b, w0, w1=None):
    """A tapered strip from a to b (a limb, a pole, a line of ink)."""
    w1 = w0 if w1 is None else w1
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / L, dx / L
    return [(a[0] + nx * w0 / 2, a[1] + ny * w0 / 2), (b[0] + nx * w1 / 2, b[1] + ny * w1 / 2),
            (b[0] - nx * w1 / 2, b[1] - ny * w1 / 2), (a[0] - nx * w0 / 2, a[1] - ny * w0 / 2)]


def clip(subject, clipper):
    """Sutherland-Hodgman: clip a polygon to a convex polygon."""
    area = sum(clipper[i][0] * clipper[i - 1][1] - clipper[i - 1][0] * clipper[i][1] for i in range(len(clipper)))
    sgn = -1 if area > 0 else 1
    out = list(subject)
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break

        def inside(p):
            return sgn * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) >= 0

        def cross(p, q):
            x1, y1 = p
            x2, y2 = q
            den = (x1 - x2) * (a[1] - b[1]) - (y1 - y2) * (a[0] - b[0])
            if abs(den) < 1e-9:
                return q
            t = ((x1 - a[0]) * (a[1] - b[1]) - (y1 - a[1]) * (a[0] - b[0])) / den
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        prev = inp[-1]
        for cur in inp:
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
            prev = cur
    return out


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def window_geom(cx):
    return cx - 200, 430, cx + 200, 650


def lamp_light(cx, x, y):
    """How much of the over-bed lamp reaches (x, y): 0..1."""
    lx, ly = cx - 112, 500
    d2 = ((x - lx) / 1.25) ** 2 + (y - ly) ** 2
    return math.exp(-d2 / (2 * 120 ** 2))


def lit(cx, col, pts):
    x = sum(p[0] for p in pts) / len(pts)
    y = sum(p[1] for p in pts) / len(pts)
    f = lamp_light(cx, x, y)
    base = tuple(min(255, c * (0.74 + 0.42 * f) + g * 0.10 * f) for c, g in zip(col, GOLD))
    return tuple(int(v) for v in base)


# ------------------------------------------------------------------ the static set
@lru_cache(maxsize=8)
def _set(cx, ground):
    it = []
    x0, x1, top = cx - 320, cx + 320, 200
    it.append(P(rect(x0, top, x1, ground), FACADE))
    it.append(P(rect(x0 - 6, top - 12, x1 + 6, top + 4), BAND))                     # parapet
    it.append(P(rect(cx + 130, top - 44, cx + 250, top - 12), INDIGO))               # roof plant
    for k in range(5):
        it.append(P(rect(cx + 136 + k * 23, top - 38, cx + 150 + k * 23, top - 16), NAVY))
    # the lit H sign on the roof
    it.append(P(rect(cx - 262, top - 20, cx - 256, top - 12), NAVY))
    it.append(P(rect(cx - 212, top - 20, cx - 206, top - 12), NAVY))
    it.append(P(rect(cx - 272, top - 70, cx - 196, top - 20), (74, 118, 196)))
    it.append(P(rect(cx - 256, top - 62, cx - 247, top - 28), PAPER))
    it.append(P(rect(cx - 221, top - 62, cx - 212, top - 28), PAPER))
    it.append(P(rect(cx - 247, top - 49, cx - 221, top - 41), PAPER))

    rows = [(226, 386), (430, 650), (694, 800)]
    for (ya, yb) in rows:                                                          # floor bands
        it.append(P(rect(x0, ya - 16, x1, ya - 6), BAND))
    it.append(P(rect(x0, 810, x1, 818), BAND))

    def pane(xa, ya, xb, yb, kind):
        out = []
        if kind == 'dim':
            out.append(P(rect(xa, ya, xb, yb), PANE))
            out.append(P([(xa + (xb - xa) * 0.55, ya), (xa + (xb - xa) * 0.72, ya), (xa + (xb - xa) * 0.3, yb),
                          (xa + (xb - xa) * 0.13, yb)], (36, 42, 80)))                   # a faint sheen of sky
        elif kind == 'blind':
            out.append(P(rect(xa, ya, xb, yb), PANE))
            yb2 = ya + (yb - ya) * 0.55
            out.append(P(rect(xa, ya, xb, yb2), (46, 50, 88)))
            y = ya + 9
            while y < yb2 - 2:
                out.append(P(rect(xa, y, xb, y + 2), (40, 44, 80)))
                y += 9
        elif kind == 'corridor':                                                   # cool strip-lit corridor
            out.append(P(rect(xa, ya, xb, yb), (132, 150, 146)))
            m = (xa + xb) / 2
            out.append(P([(xa, ya), (xb, ya), (m + 14, ya + 58), (m - 14, ya + 58)], (164, 178, 170)))   # ceiling
            out.append(P([(xa, yb), (xb, yb), (m + 14, ya + 96), (m - 14, ya + 96)], (104, 118, 118)))   # floor
            out.append(P(rect(m - 14, ya + 58, m + 14, ya + 96), (88, 98, 108)))                        # far door
            out.append(P(rect(m - 5, ya + 64, m + 5, ya + 96), (70, 76, 92)))
            for k, (w, yy) in enumerate(((22, 8), (13, 30), (7, 46))):                               # strip lights
                out.append(P(rect(m - w, ya + yy, m + w, ya + yy + 4 - k), (226, 232, 214)))
        elif kind == 'tv':
            out.append(P(rect(xa, ya, xb, yb), (48, 62, 112)))
            out.append(P(rect(xa, ya + (yb - ya) * 0.6, xb, yb), (40, 50, 94)))
        elif kind == 'drawn':
            out.append(P(rect(xa, ya, xb, yb), (112, 78, 82)))
            for k in range(4):
                xx = xa + (xb - xa) * (k + 0.5) / 4
                out.append(P(rect(xx - 2, ya, xx + 2, yb), (96, 66, 74)))
        # the facade casts a paper shadow into the opening (top and left edges)
        out.append(P(rect(xa, ya, xb, ya + 5), (18, 22, 46)))
        out.append(P(rect(xa, ya, xa + 4, yb), (18, 22, 46)))
        out.append(P(rect(xa - 4, yb, xb + 4, yb + 6), FRAME))                    # sill
        return out

    kinds0 = ['blind', 'dim', 'corridor', 'dim', 'blind']
    kinds2 = ['dim', 'tv', 'dim', 'blind', 'dim']
    for r, kinds in ((0, kinds0), (2, kinds2)):
        ya, yb = rows[r]
        for k in range(5):
            xa = x0 + 22 + k * 122
            it += pane(xa, ya, xa + 108, yb, kinds[k])
    ya, yb = rows[1]
    it += pane(x0 + 20, ya, x0 + 106, yb, 'blind')
    it += pane(x1 - 106, ya, x1 - 20, yb, 'drawn')

    # ground floor: the entrance canopy and glass doors
    it.append(P(rect(cx - 120, 822, cx + 120, ground), (36, 40, 74)))
    it.append(P(rect(cx - 104, 832, cx + 104, ground), (150, 138, 118)))
    for k in range(4):
        it.append(P(rect(cx - 104 + k * 52, 832, cx - 100 + k * 52, ground), (70, 70, 96)))
    it.append(P(rect(cx - 150, 816, cx + 150, 826), BAND))

    # ---- the ward window: back wall, lamp pool, fixtures (things that don't move)
    wx0, wy0, wx1, wy1 = window_geom(cx)
    win = rect(wx0, wy0, wx1, wy1)
    it.append(P(rect(wx0 - 7, wy0 - 7, wx1 + 7, wy1 + 2), FRAME))
    it.append(P(win, mix(WALL, INK, 0.15)))
    lx, ly = cx - 112, 500
    for k in range(5):                                        # the lamp's pool on the wall: nested paper
        f = (k + 1) / 5
        r = 250 * (1 - 0.17 * k)
        col = tuple(int(min(255, c * (0.8 + 0.55 * f) + g * 0.16 * f)) for c, g in zip(WALL, GOLD))
        it.append(P(clip(ell(lx, ly + 10, r * 1.25, r * 0.9, 30), win), col))
    it.append(P(rect(wx0, 562, wx1, 566), lit(cx, (150, 110, 96), rect(wx0, 562, wx1, 566))))   # dado rail
    it.append(P(rect(wx0, 628, wx1, wy1), lit(cx, (82, 58, 60), rect(wx0, 628, wx1, wy1))))     # floor
    it.append(P(rect(wx0, wy0, wx1, wy0 + 12), (86, 62, 66)))                                   # ceiling edge
    it.append(P(rect(wx0, 444, wx1, 447), (150, 140, 140)))                                     # curtain track
    # over-bed lamp
    it.append(P(rect(lx - 26, 466, lx + 26, 474), (214, 200, 178)))
    it.append(P(rect(lx - 22, 474, lx + 22, 478), (255, 236, 190)))
    # oxygen/suction panel on the wall behind the bed head
    it.append(P(rect(cx - 172, 520, cx - 140, 552), lit(cx, (178, 170, 162), rect(cx - 172, 520, cx - 140, 552))))
    it.append(P(ell(cx - 163, 536, 4, 4, 10), (74, 150, 110)))
    it.append(P(ell(cx - 150, 536, 4, 4, 10), (220, 220, 214)))
    # monitor on its bracket
    it.append(P(seg((cx - 190, 500), (cx - 168, 500), 4), (130, 126, 130)))
    it.append(P(rect(cx - 196, 476, cx - 140, 520), (70, 72, 84)))
    it.append(P(rect(cx - 193, 479, cx - 143, 513), (18, 38, 42)))
    it.append(P(rect(cx - 190, 514, cx - 180, 518), (60, 62, 72)))
    # the drip stand (behind the bed): pole, hook arms, bag, chamber
    px = cx - 84
    it.append(P(seg((px, 470), (px, 628), 3), (150, 150, 160)))
    it.append(P(seg((px - 10, 472), (px + 10, 472), 2.5), (150, 150, 160)))
    it.append(P([(px - 12, 474), (px - 1, 474), (px + 1, 506), (px - 5, 512), (px - 11, 506)], (214, 222, 214)))
    it.append(P(rect(px - 10, 484, px - 2, 494), (230, 236, 226)))           # its label
    it.append(P(rect(px - 7, 512, px - 4, 526), (200, 214, 214)))            # drip chamber
    # window: the facade's shadow falling into the room, the sill
    it.append(P(rect(wx0, wy0, wx1, wy0 + 7), (40, 30, 42)))
    it.append(P(rect(wx0, wy0, wx0 + 6, wy1), (40, 30, 42)))
    return tuple(it)


def set_items(cx, ground):
    return list(_set(cx, ground))


# ------------------------------------------------------------------ the living part
def ecg(phase):
    """One heartbeat, phase 0..1."""
    p = phase % 1.0
    v = 0.12 * math.exp(-((p - 0.10) / 0.03) ** 2)                 # P
    v -= 0.15 * math.exp(-((p - 0.20) / 0.008) ** 2)               # Q
    v += 1.00 * math.exp(-((p - 0.225) / 0.012) ** 2)              # R
    v -= 0.25 * math.exp(-((p - 0.25) / 0.01) ** 2)                # S
    v += 0.22 * math.exp(-((p - 0.45) / 0.05) ** 2)                # T
    return v


def breath(p):
    """0..1 chest rise, 4 s per breath (15 a minute, calm)."""
    return 0.5 - 0.5 * math.cos(TAU * p / 4.0)


def action_items(tl, cx, ground):
    p = tl % LOOP
    it = []

    def add(pts, col, light=True):
        it.append(P(pts, lit(cx, col, pts) if light else col))

    # ---- the monitor trace (sweeps left to right, 22 px per second, a beat each second)
    sx0, sx1, sy = cx - 190, cx - 146, 500
    width = sx1 - sx0
    cur = sx0 + (p * 22.0) % width
    prev = None
    step = 1.5
    x = sx0
    while x <= sx1:
        ago = (cur - x) % width
        if ago < 3:                                     # the erase gap just ahead of the sweep
            prev = None
            x += step
            continue
        tt = p - ago / 22.0
        y = sy - 12 * ecg(tt)
        if prev is not None:
            fade = 1 - 0.55 * (ago / width)
            it.append(P(seg(prev, (x, y), 1.3), mix((18, 38, 42), TRACE, fade)))
        prev = (x, y)
        x += step
    beat = math.exp(-((p % 1.0 - 0.23) / 0.08) ** 2)
    it.append(P(rect(sx1 - 5, 482, sx1 - 1, 486), mix((40, 80, 60), TRACE, beat)))       # the heart light
    for k in range(3):
        it.append(P(rect(sx0 + 2 + k * 5, 482, sx0 + 5 + k * 5, 486), (90, 170, 130)))    # the numbers
    # a drop in the drip chamber, every 2 s
    dp = (p % 2.0) / 2.0
    it.append(P(ell(cx - 89.5, 514 + 10 * dp * dp, 1.2, 1.6, 8), (240, 244, 236)))

    # ---- the nurse (behind the bed), facing left
    # phases: 0-2.6 counting breaths, 2.6-5.6 writing, 5.6-8 looking back, a small nod at ~7
    write = smooth((p - 2.5) / 0.5) * (1 - smooth((p - 5.5) / 0.5))
    nod = 0.06 * math.exp(-((p - 6.9) / 0.25) ** 2)
    headang = -0.22 - 0.36 * write - nod + 0.05 * (breath(p) - 0.5) * (1 - write)
    Nx, Ny = cx + 30, 506                              # neck base
    lean = 1.5 * write
    Nx -= lean

    # far (writing) arm, upper part mostly hidden by the torso
    it_back = []
    # torso
    torso = [(Nx + 6, Ny - 2), (Nx + 12, Ny + 8), (Nx + 14, Ny + 40), (Nx + 12, Ny + 90), (Nx - 10, Ny + 90),
             (Nx - 13, Ny + 56), (Nx - 15, Ny + 30), (Nx - 12, Ny + 10), (Nx - 7, Ny - 2)]
    # neck
    add([(Nx - 6, Ny - 12), (Nx + 4, Ny - 12), (Nx + 6, Ny + 2), (Nx - 7, Ny + 2)], mix(SKIN, INK, 0.2))
    add(torso, SCRUB)
    add([(Nx - 7, Ny - 1), (Nx - 1, Ny - 1), (Nx - 7, Ny + 9)], mix(SKIN, INK, 0.1))           # V neck
    add(rect(Nx - 14, Ny + 30, Nx - 5, Ny + 40), mix(SCRUB, INK, 0.2))                       # pocket
    add(rect(Nx - 12, Ny + 26, Nx - 10, Ny + 31), RED)                                        # pens
    add(rect(Nx - 8, Ny + 25, Nx - 6, Ny + 31), PAPER)
    add(seg((Nx + 4, Ny + 4), (Nx + 10, Ny + 30), 12, 10), mix(SCRUB, PAPER, 0.06))          # sleeve (near)

    # lanyard + card (it swings a little as she leans)
    sw = 2.0 * write
    add(seg((Nx + 2, Ny - 3), (Nx - 9 - sw, Ny + 20), 1.8), RED)
    card = rot(rect(Nx - 14 - sw, Ny + 20, Nx - 5 - sw, Ny + 32), 0.1 * write, Nx - 9 - sw, Ny + 20)
    add(card, PAPER)
    add(rot(rect(Nx - 14 - sw, Ny + 20, Nx - 5 - sw, Ny + 23), 0.1 * write, Nx - 9 - sw, Ny + 20), (74, 118, 196))

    # head (rotated about the neck)
    hx, hy = Nx - 2, Ny - 22
    piv = (Nx - 1, Ny - 8)

    def H(pts):
        return rot([(hx + x, hy + y) for x, y in pts], headang, *piv)
    add(H(ell(13, -4, 6.5, 6.5, 14)), HAIR)                                          # bun
    add(H(ell(0, 0, 12, 13, 22)), SKIN)
    add(H([(-2, -12), (-9, -9), (-12, -4), (-12, -1), (-16, 3), (-12.5, 5), (-13, 7.5), (-11.5, 9),
           (-12.3, 10.5), (-9, 13.5), (-3, 15), (4, 12), (7, 4)]), SKIN)
    add(H([(-11, -6), (-9, -11), (-3, -14.5), (5, -14), (11, -9), (13.5, -1), (11, 7), (6, 9), (5, 3),
           (2, -3), (-3, -6.5), (-8, -5)]), HAIR)
    add(H([(10, -9), (15, -8), (13, -6)]), (120, 70, 80))                                      # hair tie
    add(H(ell(3, 2, 2.6, 3.6, 10)), mix(SKIN, INK, 0.18))                                   # ear
    add(H([(-10.5, -1.5), (-6.5, -2.4), (-6, -0.8), (-9.5, -0.6)]), (52, 34, 40))          # eye (lowered lid)
    add(H([(-11, -5.5), (-6, -6.5), (-5.8, -5.4), (-10.5, -4.6)]), mix(HAIR, SKIN, 0.2))   # brow
    add(H([(-12.2, 8.0), (-9.6, 8.6), (-12.0, 9.2)]), (150, 84, 84))                         # lips

    # clipboard, held by the near arm
    cbx, cby = Nx - 28 - 3 * write, Ny + 48 - 16 * write     # lowered while she watches, raised to write
    cang = -0.95 + 0.4 * write
    board = rot(rect(cbx - 15, cby - 20, cbx + 15, cby + 20), cang, cbx, cby)
    sheet = rot(rect(cbx - 12, cby - 15, cbx + 12, cby + 18), cang, cbx, cby)
    clipm = rot(rect(cbx - 6, cby - 23, cbx + 6, cby - 16), cang, cbx, cby)
    add(board, (150, 104, 72))
    add(sheet, PAPER)
    add(clipm, (170, 170, 176))

    def B(x, y):                                     # a point on the sheet, in its own frame
        return rot([(cbx + x, cby + y)], cang, cbx, cby)[0]
    for k in range(3):                               # lines already written
        yy = -9 + k * 6
        add(seg(B(-9, yy), B(9 - 4 * (k == 2), yy), 1.0), (120, 116, 130))
    # tonight's line grows while she writes
    prog = smooth((p - 2.9) / 2.3)
    if prog > 0.02:
        pts = []
        n = int(3 + prog * 14)
        for k in range(n + 1):
            u = k / 14
            pts.append(B(-9 + 18 * u, 11 + 1.2 * math.sin(u * 40)))
        for a, b in zip(pts, pts[1:]):
            add(seg(a, b, 1.1), (60, 60, 110))
    # pen hand (far arm): taps on each breath while counting, writes, then rests
    if write > 0.01:
        u = smooth((p - 2.9) / 2.3)
        wx = -9 + 18 * u
        wy = 11 + 1.8 * math.sin(p * 21)
        tip = B(wx, wy)
        tip = (tip[0] * write + (B(10, -4)[0]) * (1 - write), tip[1] * write + B(10, -4)[1] * (1 - write))
    else:
        tap = math.exp(-(((p % 4.0) - 0.0) / 0.12) ** 2) + math.exp(-(((p % 4.0) - 4.0) / 0.12) ** 2)
        tip = B(10, -4 - 4 * (1 - tap))
    elb_f = (Nx - 6, Ny + 50)
    hand = (tip[0] + 5, tip[1] - 4)
    add(seg(elb_f, hand, 7, 5.5), mix(SKIN, INK, 0.28))
    add(ell(hand[0], hand[1], 4.2, 3.6, 12), mix(SKIN, INK, 0.2))
    add(seg((hand[0] + 4, hand[1] - 6), tip, 1.8, 1.2), (40, 44, 80))                    # pen

    # near arm: upper arm (sleeve) + forearm to the clipboard's lower edge
    elb = (Nx + 9, Ny + 44)
    grip = B(8, 16)
    add(seg((Nx + 10, Ny + 30), elb, 9, 8), SKIN)
    add(seg(elb, grip, 8, 6.5), SKIN)
    add(ell(grip[0], grip[1], 4.5, 4, 12), SKIN)

    # ---- the bed and the patient (in front of the nurse)
    add(rect(cx - 176, 546, cx - 162, 640), (176, 168, 164))                              # headboard
    add(rect(cx - 180, 540, cx - 158, 548), (200, 194, 188))
    add(rect(cx + 76, 560, cx + 88, 640), (176, 168, 164))                                # footboard
    add(rect(cx + 74, 554, cx + 90, 562), (200, 194, 188))
    add(rect(cx - 166, 598, cx + 82, 612), (104, 100, 118))                               # frame
    add(rect(cx - 150, 612, cx - 144, 640), (96, 94, 110))
    add(rect(cx + 60, 612, cx + 66, 640), (96, 94, 110))
    add(rect(cx - 166, 584, cx + 82, 600), (214, 218, 222))                               # mattress + sheet
    add(ell(cx - 136, 580, 28, 11, 18), (232, 226, 214))                                  # pillow

    b = breath(p)
    # patient's head on the pillow, face up (crown toward the headboard)
    phx, phy = cx - 130, 573
    add(ell(phx, phy, 14, 12, 20), SKIN_P)
    add([(phx - 15, phy + 2), (phx - 13, phy - 6), (phx - 7, phy - 11), (phx - 2, phy - 12), (phx - 5, phy - 6),
         (phx - 6, phy + 2), (phx - 4, phy + 9), (phx - 12, phy + 9)], (132, 124, 130))       # grey hair
    add([(phx - 2, phy - 12), (phx + 4, phy - 12), (phx + 6, phy - 19), (phx + 9, phy - 11), (phx + 13, phy - 10),
         (phx + 16, phy - 5), (phx + 13, phy + 2)], SKIN_P)                                   # brow, nose, lips, chin
    add(ell(phx - 1, phy + 1, 2.5, 3.2, 10), mix(SKIN_P, INK, 0.2))                       # ear
    add(seg((phx + 1, phy - 8), (phx + 5, phy - 7.5), 1.4), (110, 64, 66))                # closed eye
    add(seg((phx + 12, phy - 9), (phx + 14, phy - 7), 1.2), (150, 90, 90))                # mouth
    # blanket: its top edge breathes at the chest
    ch = 5.0 * b
    top = [(cx - 116, 582), (cx - 104, 572 - ch * 0.4), (cx - 86, 566 - ch), (cx - 66, 568 - ch * 0.6),
           (cx - 44, 575 - ch * 0.2), (cx - 20, 574), (cx + 4, 566), (cx + 24, 571), (cx + 44, 575),
           (cx + 58, 566), (cx + 70, 568), (cx + 78, 580)]
    blanket = top + [(cx + 80, 606), (cx - 118, 606)]
    add(blanket, DBLUE)
    add([(cx - 118, 588), (cx + 80, 588), (cx + 80, 594), (cx - 118, 594)], mix(DBLUE, INK, 0.12))   # fold
    add(seg((cx - 116, 583), (cx - 88, 572 - ch), 4), (232, 226, 214))                        # sheet turned down
    # the patient's arm on top of the blanket, with the drip line
    add(seg((cx - 96, 574 - ch * 0.7), (cx - 58, 578 - ch * 0.2), 7, 6), (214, 212, 204))     # gown sleeve
    add(ell(cx - 54, 578 - ch * 0.2, 4.5, 3.5, 12), SKIN_P)
    tube = [(cx - 89.5, 526), (cx - 92, 548), (cx - 82, 566), (cx - 62, 576 - ch * 0.2)]
    for a2, b2 in zip(tube, tube[1:]):
        add(seg(a2, b2, 1.2), (206, 214, 214))
    # bed rail (in front)
    add(rect(cx - 112, 574, cx - 14, 578), (170, 170, 180))
    for xx in (cx - 110, cx - 60, cx - 18):
        add(rect(xx, 574, xx + 4, 598), (150, 150, 162))

    # ---- privacy curtain on the right, breathing in a draught
    # a bedside locker with a jug of flowers someone brought
    add(rect(cx + 96, 598, cx + 134, 640), (176, 150, 128))
    add(rect(cx + 96, 594, cx + 136, 600), (196, 172, 148))
    add(rect(cx + 100, 612, cx + 130, 614), (140, 116, 102))
    add([(cx + 104, 594), (cx + 102, 578), (cx + 112, 578), (cx + 110, 594)], (150, 176, 196))        # jug
    fl = 1.2 * math.sin(TAU * p / LOOP)
    for k, (dx, h, col) in enumerate(((-6, 22, (230, 170, 60)), (0, 28, (238, 222, 200)), (7, 20, (214, 110, 110)))):
        tipx, tipy = cx + 107 + dx + fl * (k - 1) * 0.6, 578 - h
        add(seg((cx + 107, 580), (tipx, tipy), 1.4), (90, 120, 80))
        add(ell(tipx, tipy, 4, 3.5, 10), col)
    rx0 = cx + 146
    for k in range(4):
        xa = rx0 + k * 13
        sway = 3.0 * math.sin(TAU * (p / LOOP) * 2 + k * 0.7) + 2.0 * math.sin(TAU * p / LOOP + k)
        col = (168, 118, 116) if k % 2 == 0 else (140, 94, 100)
        add([(xa, 448), (xa + 14, 448), (xa + 14 + sway, 646), (xa + sway * 0.8, 646)], col)
    for k in range(4):
        add(ell(rx0 + 6 + k * 13, 448, 2.5, 2.5, 8), (190, 186, 186), light=False)

    # the window's paper shadow and sill go over everything inside
    wx0, wy0, wx1, wy1 = window_geom(cx)
    it.append(P(rect(wx0, wy0, wx1, wy0 + 7), (40, 30, 42)))
    it.append(P(rect(wx0, wy0, wx0 + 6, wy1), (40, 30, 42)))
    it.append(P(rect(wx0 - 12, wy1, wx1 + 12, wy1 + 14), (120, 124, 158)))
    it.append(P(rect(wx0 - 12, wy1 + 14, wx1 + 12, wy1 + 18), (44, 48, 86)))
    return it
