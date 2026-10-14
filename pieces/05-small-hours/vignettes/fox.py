"""Fox: "And by the bins a fox walks slowly like she owns the town".

A corner shop shut for the night (roller shutter, fascia, a flat upstairs with one lamp on), two wheelie
bins with one lid ajar, a paper bag, and a street lamp throwing a stepped paper cone of warm light onto the
wall. The fox walks in from the left with a slow, deliberate walk cycle (feet planted, head level, brush
held low and swaying), stops in the lamp light with one forepaw raised, turns her head to look straight at
us (eyeshine), blinks once, looks away and walks on past the bins.

Light: PIL polygons with alpha would punch holes in the layer, so the lamp's light is drawn as opaque
"relit" copies of each set shape clipped to nested cone/halo polygons (a stepped paper gradient), and the
fox is tinted by where she stands in the cone.
"""
import math
from functools import lru_cache

TAU = 2 * math.pi

INK = (21, 26, 51)
INDIGO = (31, 37, 80)
NAVY = (42, 47, 94)
MID = (59, 63, 116)
GOLD = (255, 201, 120)
RED = (184, 57, 46)
FOXC = (212, 110, 51)
PAPER = (239, 230, 210)
ROSE = (244, 199, 168)

FOX_DARK = (150, 70, 36)
SOCK = (58, 36, 40)
WHITE = (236, 226, 204)


# ------------------------------------------------------------------ small geometry kit
def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def P(pts, col):
    return ('poly', [(float(x), float(y)) for x, y in pts], col)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def ell(cx, cy, rx, ry, n=20, rot=0.0):
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


def seg(a, b, w0, w1=None):
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


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ the lamp and its light
def lamp_geom(cx, ground):
    post_x = cx - 176
    head = (cx - 84, ground - 336)             # the glass
    return post_x, head


def light_regions(cx, ground, inten=1.0):
    """Nested convex polygons with their light amount k (ascending)."""
    _, (hx, hy) = lamp_geom(cx, ground)
    ay = hy + 8
    regs = []
    for k, (bot, topw) in enumerate(((168, 16), (124, 12), (84, 9), (46, 6))):
        regs.append(([(hx - topw, ay), (hx + topw, ay), (hx + bot, ground), (hx - bot, ground)], (0.28 + 0.2 * k) * inten))
    for k, r in enumerate((44, 28, 15)):
        regs.append((ell(hx, hy + 2, r * 1.15, r, 22), (0.45 + 0.22 * k) * inten))
    for k, (rx, ry) in enumerate(((190, 24), (140, 17), (95, 11), (52, 6))):
        regs.append((ell(hx, ground + 5, rx, ry, 28), (0.3 + 0.2 * k) * inten))
    regs.sort(key=lambda r: r[1])
    return regs


def relit(col, k):
    tgt = tuple(min(255.0, c * g / 255 * 2.1 + g * 0.3) for c, g in zip(col, GOLD))
    k = min(1.0, max(0.0, k))
    return tuple(int(round(c + (t - c) * k)) for c, t in zip(col, tgt))


def cone_light(cx, ground, x, y, inten=1.0):
    """Continuous light amount at (x, y) for tinting moving things."""
    _, (hx, hy) = lamp_geom(cx, ground)
    u = (y - hy) / (ground - hy)
    if u <= 0:
        return 0.0
    half = 16 + (168 - 16) * u
    return inten * max(0.0, 1 - abs(x - hx) / half) ** 0.8


def flicker(tl):
    """The lamp is steady except for two brief buzzing dips."""
    v = 1.0
    for t0 in (1.55, 6.35):
        d = tl - t0
        if 0 <= d < 0.42:
            v = (0.45, 0.9, 0.35, 0.8, 0.55)[int(d * 12) % 5]
    return v


# ------------------------------------------------------------------ the static set
@lru_cache(maxsize=8)
def _base(cx, ground):
    g = ground
    s = []                                                  # (pts, col, relight?)

    def add(pts, col, light=True):
        s.append((pts, col, light))
    # the pavement and road (already drawn by the street layer): listed here only so the lamp's pool
    # can be cut from them
    add(rect(cx - 330, g, cx + 330, g + 60), (26, 26, 40), 'only')
    for xx in range(-400, 20000, 160):
        if cx - 480 < xx < cx + 330:
            add(rect(xx, g - 4, xx + 150, g + 6), (58, 56, 74), 'only')
    wall = (40, 45, 90)
    add(rect(cx - 330, 420, cx + 330, g), wall)
    add(rect(cx - 336, 408, cx + 336, 424), (58, 62, 108))                                   # cornice
    add(rect(cx - 330, 424, cx + 330, 430), (30, 34, 70))
    # upstairs flat: three windows, one lamp on behind a curtain
    for k, x0 in enumerate((cx - 280, cx - 60, cx + 170)):
        add(rect(x0 - 5, 456, x0 + 75, 546), (56, 60, 104))
        if k == 2:
            add(rect(x0, 461, x0 + 70, 541), (170, 112, 78))
            add([(x0, 461), (x0 + 30, 461), (x0 + 20, 541), (x0, 541)], (128, 78, 70))
            add([(x0 + 40, 461), (x0 + 70, 461), (x0 + 70, 541), (x0 + 52, 541)], (128, 78, 70))
        else:
            add(rect(x0, 461, x0 + 70, 541), (26, 30, 62))
            add([(x0 + 40, 461), (x0 + 52, 461), (x0 + 22, 541), (x0 + 10, 541)], (34, 38, 74))
        add(rect(x0, 461, x0 + 70, 465), (16, 20, 44))
        add(rect(x0 - 8, 546, x0 + 78, 552), (66, 70, 114))                                     # sill
    # fascia sign (shop name as cut-paper letter blocks) and the shutter
    add(rect(cx - 306, 576, cx + 104, 616), (100, 42, 46))
    add(rect(cx - 306, 612, cx + 104, 618), (70, 30, 38))
    font = {'O': ('111', '101', '101', '101', '111'), 'P': ('111', '101', '111', '100', '100'),
            'E': ('111', '100', '110', '100', '111'), 'N': ('1001', '1101', '1011', '1001', '1001'),
            'L': ('100', '100', '100', '100', '111'), 'A': ('0110', '1001', '1111', '1001', '1001'),
            'T': ('111', '010', '010', '010', '010'), ' ': ('000',) * 5}
    cell = 4.4
    lx = cx - 150
    for ch in 'OPEN LATE':
        for r, row in enumerate(font[ch]):
            c0 = None
            for c, bit in enumerate(row + '0'):
                if bit == '1' and c0 is None:
                    c0 = c
                elif bit != '1' and c0 is not None:
                    add(rect(lx + c0 * cell, 585 + r * cell, lx + c * cell, 585 + (r + 1) * cell), (222, 196, 160))
                    c0 = None
        lx += (len(font[ch][0]) + 1) * cell
    add(rect(cx - 290, 588, cx - 196, 604), (130, 60, 58))                                    # a painted stripe
    add(rect(cx - 300, 620, cx + 98, g), (72, 76, 116))
    y = 626
    while y < g - 4:
        add(rect(cx - 300, y, cx + 98, y + 3), (56, 60, 98))
        y += 10
    add(rect(cx - 300, 620, cx + 98, 628), (52, 56, 94))                                       # shutter box
    add(rect(cx - 306, 620, cx - 300, g), (58, 62, 104))
    add(rect(cx + 98, 620, cx + 104, g), (58, 62, 104))
    add(rect(cx - 246, g - 22, cx - 236, g - 12), (110, 110, 122))                             # padlock
    add(rect(cx - 244, g - 27, cx - 238, g - 22), (90, 90, 104))
    # someone's painted a small heart on the shutter
    hx, hy = cx + 30, 700
    add(ell(hx - 6, hy, 7, 7, 14), (206, 120, 128))
    add(ell(hx + 6, hy, 7, 7, 14), (206, 120, 128))
    add([(hx - 13, hy + 2), (hx + 13, hy + 2), (hx, hy + 17)], (206, 120, 128))
    # drainpipe
    add(rect(cx + 296, 420, cx + 306, g), (58, 60, 100))
    for yy in (470, 620, 770):
        add(rect(cx + 292, yy, cx + 310, yy + 6), (66, 68, 108))
    # the wheelie bins (side view, hinges at the back)
    add_bins(add, cx, g)
    # the lamp post (not relit: it's the light)
    post_x, (lx, ly) = lamp_geom(cx, g)
    col = (30, 34, 66)
    add(rect(post_x - 9, g - 34, post_x + 9, g), col, False)
    add(rect(post_x - 5, ly - 10, post_x + 5, g - 34), col, False)
    arc = [(post_x + (lx - post_x) * (i / 8), ly - 12 - 30 * math.sin(math.pi * i / 8) * (1 - i / 16))
           for i in range(9)]
    for a, b in zip(arc, arc[1:]):
        add(seg(a, b, 6), col, False)
    add(ell(post_x, ly - 14, 6, 6, 10), col, False)
    add([(lx - 20, ly - 2), (lx - 8, ly - 14), (lx + 8, ly - 14), (lx + 20, ly - 2)], col, False)   # shade
    return tuple(s)


def add_bins(add, cx, g):
    for (x0, body, lid, ajar) in ((cx + 128, (46, 76, 66), (34, 58, 52), 0.0),
                                  (cx + 214, (66, 70, 112), (48, 52, 90), 0.2)):
        w, h = 74, 150
        top = g - h
        add([(x0, top + 10), (x0 + w, top + 10), (x0 + w - 4, g - 8), (x0 + 6, g - 2)], body)
        add([(x0 + 4, top + 22), (x0 + w - 6, top + 22), (x0 + w - 6, top + 26), (x0 + 4, top + 26)],
            tuple(int(c * 0.8) for c in body))
        add([(x0 + 8, top + 60), (x0 + 24, top + 60), (x0 + 24, top + 70), (x0 + 8, top + 70)],
            (200, 196, 184))                                                               # house number label
        add(ell(x0 + w - 14, g - 13, 13, 13, 18), (26, 28, 44))                             # wheel
        add(ell(x0 + w - 14, g - 13, 5, 5, 10), (70, 72, 90))
        add(rect(x0 + 2, g - 12, x0 + 12, g), tuple(int(c * 0.7) for c in body))            # front foot
        hinge = (x0 + w + 2, top + 10)
        lidp = [(x0 - 6, top), (x0 + w + 2, top), (x0 + w + 2, top + 10), (x0 - 6, top + 10)]
        if ajar:
            add([(x0 + 2, top + 10), (x0 + w - 2, top + 10), (x0 + w - 2, top + 4), (x0 + 2, top - 4)],
                (18, 20, 36))                                                              # the dark gap
            add(rot([(x0 + 4, top + 6), (x0 + 30, top + 6), (x0 + 28, top - 14), (x0 + 12, top - 12)],
                    -0.1, x0 + 20, top + 6), (208, 188, 150))                                # chip paper poking out
        lidp = rot(lidp, -ajar, *hinge)
        add(lidp, lid)
        hb = rot([(x0 + w + 2, top + 2), (x0 + w + 12, top + 4), (x0 + w + 12, top + 10), (x0 + w + 2, top + 10)],
                 -ajar * 0.5, *hinge)
        add(hb, lid)


def relight_list(shapes, regs, only_light=False):
    out = []
    boxes = [(bbox(r), r, k) for r, k in regs]
    for pts, col, light in shapes:
        if not only_light and light != 'only':
            out.append(P(pts, col))
        if not light:
            continue
        bx = bbox(pts)
        for (rb, r, k) in boxes:
            if bx[2] < rb[0] or bx[0] > rb[2] or bx[3] < rb[1] or bx[1] > rb[3]:
                continue
            c = clip(pts, r)
            if len(c) >= 3:
                out.append(P(c, relit(col, k)))
    return out


def lamp_glass(cx, g, inten):
    _, (lx, ly) = lamp_geom(cx, g)
    glass = mix((120, 96, 80), (255, 226, 170), inten)
    return [P([(lx - 16, ly - 2), (lx + 16, ly - 2), (lx + 11, ly + 8), (lx - 11, ly + 8)], glass),
            P(ell(lx, ly + 3, 6, 4, 12), mix((140, 110, 90), (255, 240, 205), inten))]


@lru_cache(maxsize=8)
def _set(cx, ground):
    out = relight_list(_base(cx, ground), light_regions(cx, ground, 1.0))
    return tuple(out + lamp_glass(cx, ground, 1.0))


def set_items(cx, ground):
    return list(_set(cx, ground))


# ------------------------------------------------------------------ the fox
V = 80.0                       # walking speed, world px / s
STRIDE = 72.0                  # body travel per gait cycle
DUTY = 0.62                    # stance fraction
T1, T2, T3, T4 = 2.2, 3.0, 5.2, 5.8
SCALE = 1.22                   # the fox is drawn a touch larger than life, so she reads at zoom 2.1


def travel(tl):
    """Distance walked since tl = 0 (negative before), with an eased stop and start in the lamp light."""
    if tl < T1:
        return V * tl
    d = V * T1
    if tl < T2:
        u = (tl - T1) / (T2 - T1)
        return d + V * (T2 - T1) * (u - u * u / 2)
    d += V * (T2 - T1) / 2
    if tl < T3:
        return d
    if tl < T4:
        u = (tl - T3) / (T4 - T3)
        return d + V * (T4 - T3) * u * u / 2
    d += V * (T4 - T3) / 2
    return d + V * (tl - T4)


D_STOP = V * T1 + V * (T2 - T1) / 2


def foot(q, lift):
    """Foot offset from its joint for leg phase q (0..1): stance slides back, swing arcs forward."""
    q %= 1.0
    half = DUTY * STRIDE / 2
    if q < DUTY:
        return half - 2 * half * (q / DUTY), 0.0
    u = (q - DUTY) / (1 - DUTY)
    return -half + 2 * half * smooth(u), -lift * math.sin(math.pi * u)


def ik(a, f, l1, l2, bend):
    dx, dy = f[0] - a[0], f[1] - a[1]
    d = min(math.hypot(dx, dy), l1 + l2 - 0.5)
    d = max(d, abs(l1 - l2) + 0.5)
    ang = math.atan2(dy, dx)
    c = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    al = math.acos(max(-1.0, min(1.0, c)))
    k = (a[0] + l1 * math.cos(ang + bend * al), a[1] + l1 * math.sin(ang + bend * al))
    fe = (k[0] + l2 * math.cos(math.atan2(f[1] - k[1], f[0] - k[0])),
          k[1] + l2 * math.sin(math.atan2(f[1] - k[1], f[0] - k[0])))
    return k, fe


HEAD_PROFILE = {
    'far_ear': [(-3, -14), (1, -36), (10, -16)],
    'face': [(-5, -13), (5, -19), (17, -19), (27, -13), (42, -6), (49, -3), (47, 2), (35, 5), (21, 8),
             (8, 10), (-5, 6)],
    'white': [(6, 2), (20, 0), (33, 2), (45, 1), (35, 5), (21, 8), (8, 10), (-3, 7)],
    'ear': [(5, -16), (11, -39), (19, -16)],
    'ear_tip': [(9, -31), (11, -39), (13.6, -31)],
    'eyes': [(23, -10.5)],
    'nose': (48, -2),
}
HEAD_34 = {
    'far_ear': [(14, -17), (27, -37), (30, -11)],
    'face': [(-6, -12), (3, -18), (17, -19), (28, -13), (37, -3), (35, 3), (23, 10), (9, 11), (-4, 6)],
    'white': [(-5, 1), (7, 3), (18, 4), (22, 10), (9, 11), (-4, 6)],
    'white2': [(26, 0), (35, 2), (33, 5), (25, 9), (22, 4)],
    'ear': [(-5, -13), (-3, -39), (10, -18)],
    'ear_tip': [(-4.4, -31), (-3, -39), (2, -31)],
    'eyes': [(9, -8), (25, -8)],
    'nose': (36, 0),
}
HEAD_FRONT = {
    'far_ear': [(17, -17), (34, -41), (32, -10)],
    'face': [(-8, -13), (0, -19), (12, -20), (24, -19), (32, -13), (33, -3), (23, 7), (12, 14), (1, 7), (-9, -3)],
    'white': [(-9, -3), (-1, -1), (7, 6), (12, 14), (1, 7)],
    'white2': [(33, -3), (25, -1), (17, 6), (12, 14), (23, 7)],
    'ear': [(-8, -10), (-10, -41), (7, -17)],
    'ear_tip': [(-9.6, -33), (-10, -41), (-5, -34)],
    'far_ear_tip': [(29, -34), (34, -41), (33.2, -33)],
    'eyes': [(4, -6), (20, -6)],
    'nose': (12, 10),
}


def action_items(tl, cx, ground):
    g = ground
    it = []
    inten = flicker(tl)
    if inten < 0.999:                                   # the lamp buzzes: redraw the light at this strength
        it += relight_list(_base(cx, g), light_regions(cx, g, inten), only_light=True)
        # levels that dropped below the set's must also be covered where they no longer reach
        it += lamp_glass(cx, g, inten)
    _, (lx, ly) = lamp_geom(cx, g)

    # two moths around the lamp
    for k in range(2):
        a = tl * (2.3 + 0.9 * k) + k * 2.1
        mx = lx + (26 + 8 * k) * math.cos(a) + 5 * math.sin(a * 3.1)
        my = ly + 10 + 14 * math.sin(a * 1.3 + k)
        wing = 1.6 + 1.2 * abs(math.sin(tl * 25 + k))
        it.append(P(ell(mx, my, wing, 1.4, 8), (240, 226, 196)))

    # the paper bag by the bins: a breeze nudges it now and then
    bx, by = cx + 96, g - 2
    nud = 0.06 * math.sin(tl * 1.7) * math.sin(tl * 0.45) + 0.05 * math.exp(-((tl - 6.8) / 0.3) ** 2)
    bag = rot([(bx - 14, by), (bx + 14, by), (bx + 12, by - 22), (bx + 15, by - 30), (bx + 6, by - 27),
               (bx - 2, by - 32), (bx - 8, by - 26), (bx - 13, by - 28), (bx - 11, by - 20)], nud, bx, by)
    it.append(P(bag, (170, 136, 98)))
    it.append(P(rot([(bx - 12, by - 20), (bx + 12, by - 22), (bx + 12, by - 19), (bx - 12, by - 17)], nud, bx, by),
                (146, 114, 84)))

    it += fox_items(tl, cx, g)
    return it


def fox_items(tl, cx, g):
    d = travel(tl)
    fx = cx - 84 - D_STOP + d                             # body centre x; the stop is under the lamp
    if fx < cx - 560 or fx > cx + 560:
        return []
    phase = d / (STRIDE * SCALE)                          # feet stay planted at this scale
    inten = flicker(tl)
    walking = 0.0 if T2 <= tl < T3 else 1.0
    if T1 <= tl < T2:
        walking = 1 - (tl - T1) / (T2 - T1)
    if T3 <= tl < T4:
        walking = (tl - T3) / (T4 - T3)
    bob = 1.3 * math.sin(TAU * phase * 2) * walking
    gy = g - 3                                            # paws just above the kerb stones
    base_y = gy + bob

    out = []

    def col(c, pts):
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        f = cone_light(cx, g, x, y, inten)
        tgt = tuple(min(255, v * 1.12 + gg * 0.14) for v, gg in zip(c, GOLD))
        dark = tuple(v * 0.66 + n * 0.1 for v, n in zip(c, INK))
        return tuple(int(dk + (t - dk) * min(1.0, f * 1.3)) for dk, t in zip(dark, tgt))

    def add(pts, c):
        out.append(P(pts, col(c, pts)))

    def L(x, y):
        return (fx + x, base_y + y)

    # ---- tail (behind everything); swish slowly, more when she's still
    sway_amp = 0.10 + 0.08 * (1 - walking)
    base = L(-44, -50)
    spine = [base]
    ang = math.radians(196)
    seglen = 12.0
    for i in range(8):
        ang += math.radians(-3.2) + sway_amp * 0.35 * math.sin(TAU * 0.5 * tl - i * 0.55) * (i + 1) / 4
        ang += 0.04 * math.sin(TAU * phase) * walking
        p = spine[-1]
        spine.append((p[0] + seglen * math.cos(ang), p[1] + seglen * math.sin(ang)))
    widths = [9, 15, 20, 23, 23, 21, 17, 11, 3]

    def strip(i0, i1):
        left, right = [], []
        for i in range(i0, i1 + 1):
            a = spine[max(0, i - 1)]
            b = spine[min(len(spine) - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy) or 1
            nx, ny = -dy / n, dx / n
            w = widths[i] / 2
            left.append((spine[i][0] + nx * w, spine[i][1] + ny * w))
            right.append((spine[i][0] - nx * w, spine[i][1] - ny * w))
        return left + right[::-1]
    add(strip(0, 8), FOXC)
    add(strip(6, 8), WHITE)
    # a darker streak along the top of the brush
    top = []
    for i in range(1, 7):
        a, b = spine[i - 1], spine[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        top.append((spine[i][0] - dy / n * widths[i] * 0.35, spine[i][1] + dx / n * widths[i] * 0.35))
    for a, b in zip(top, top[1:]):
        add(seg(a, b, 3.5), FOX_DARK)

    # contact shadow on the pavement
    out.append(P(ell(fx - 4, g + 1, 50, 4.5, 20), (24, 20, 30)))

    # ---- legs: offsets in the gait cycle (lateral walk): LH 0, LF .25, RH .5, RF .75
    def leg(joint, off, fore, near):
        q = phase + off
        fxo, fyo = foot(q, 9 if fore else 8)
        if walking < 1:                                   # when she stops, her feet stay where they are
            pass
        target = (joint[0] + fxo, gy + fyo)
        bend = -1 if fore else 1
        l1, l2 = (24, 23) if fore else (22, 24)
        knee, paw = ik(joint, target, l1, l2, bend)
        shade = 1.0 if near else 0.62
        up = tuple(int(c * shade) for c in (FOXC if not fore else FOX_DARK))
        low = tuple(int(c * shade) for c in SOCK)
        add(seg(joint, knee, 13 if not fore else 10, 8 if not fore else 7), up)
        add(seg(knee, paw, 7, 5.5), low)
        add(ell(paw[0] + 3, paw[1] - 2.5, 5.5, 3, 10), low)

    fore_j = L(28, -40)
    hind_j = L(-30, -40)
    leg((fore_j[0] - 4, fore_j[1]), 0.75, True, False)     # far legs first
    leg((hind_j[0] - 4, hind_j[1]), 0.5, False, False)

    # ---- body
    body = [L(-40, -54), L(-20, -58), L(4, -58), L(26, -61), L(40, -67), L(50, -60), L(48, -46),
            L(40, -38), L(20, -35), L(-6, -36), L(-26, -38), L(-42, -41), L(-49, -49)]
    add(body, FOXC)
    add([L(-28, -38), L(-6, -36), L(20, -35), L(30, -37), L(20, -39), L(-6, -40)], mix(FOXC, WHITE, 0.35))   # belly
    add(ell(fx - 31, base_y - 47, 17, 13, 18), mix(FOXC, FOX_DARK, 0.25))                    # haunch
    add([L(-18, -58), L(22, -61), L(10, -57)], mix(FOXC, FOX_DARK, 0.4))                    # darker saddle line
    leg(fore_j, 0.25, True, True)
    leg(hind_j, 0.0, False, True)
    add(ell(fx + 30, base_y - 47, 12, 11, 16), FOXC)                                         # shoulder

    # ---- neck, bib, head (the head stays level: undo the bob)
    hb = -bob
    add([L(28, -60), L(44, -74 + hb), L(58, -70 + hb), L(54, -50), L(44, -42)], FOXC)
    add([L(46, -70 + hb), L(58, -66 + hb), L(55, -50), L(46, -40), L(40, -46), L(44, -60)], WHITE)   # bib

    # head choice: profile -> 3/4 -> front while paused (replacement heads, like real cut-out animation)
    turn = 0
    if 3.25 <= tl < 3.42 or 4.85 <= tl < 5.02:
        turn = 1
    elif 3.42 <= tl < 4.85:
        turn = 2
    blink = 4.25 <= tl < 4.42
    twitch = 1 if (3.9 <= tl < 4.05) else 0
    H = (HEAD_PROFILE, HEAD_34, HEAD_FRONT)[turn]
    ox, oy = fx + (52, 48, 44)[turn], base_y - 76 + hb + (0, 0, -2)[turn]
    tilt = (0.0, 0.05, -0.08)[turn]

    def T(pts):
        return rot([(ox + x, oy + y) for x, y in pts], tilt, ox, oy)
    add(T(H['far_ear']), FOX_DARK)
    if 'far_ear_tip' in H:
        add(T(H['far_ear_tip']), SOCK)
    add(T(H['face']), FOXC)
    add(T(H['white']), WHITE)
    if 'white2' in H:
        add(T(H['white2']), WHITE)
    ear = H['ear']
    if twitch:
        ear = rot(ear, -0.25, *ear[0])
    add(T(ear), FOXC)
    add(T(rot(H['ear_tip'], -0.25, *H['ear'][0]) if twitch else H['ear_tip']), SOCK)
    if turn == 2:                                         # inner ears when facing us
        add(T([(-7, -13), (-9, -33), (3, -17)]), (120, 60, 50))
        add(T([(21, -17), (31, -33), (30, -13)]), (120, 60, 50))
    for (ex, ey) in H['eyes']:
        if blink:
            add(T(seg((ex - 3.5, ey), (ex + 3.5, ey), 1.4)), SOCK)
        elif turn == 0:
            add(T([(ex - 4.5, ey + 0.5), (ex, ey - 2.4), (ex + 4.5, ey - 0.5), (ex, ey + 1.8)]), SOCK)
            add(T(ell(ex + 1, ey - 0.6, 1.1, 1.0, 6)), (255, 214, 130))
        else:                                             # eyeshine: she looks at us and the lamp is in her eyes
            out.append(P(T([(ex - 4.8, ey + 1), (ex - 1, ey - 2.8), (ex + 4.8, ey - 1), (ex + 1, ey + 2.6)]),
                         SOCK))
            out.append(P(T(ell(ex, ey, 3.2, 2.2, 10, -0.3)), (255, 222, 150)))
            out.append(P(T(ell(ex, ey, 0.9, 2.0, 6)), (40, 24, 20)))
    nx_, ny_ = H['nose']
    add(T(ell(nx_, ny_, 3.4, 2.6, 10)), SOCK)
    if turn == 0:
        add(T(seg((33, 4.5), (45, 2), 1.2)), SOCK)
    # whiskers catching the light
    if turn == 2:
        for sgn in (-1, 1):
            for k in range(2):
                a = (nx_ + sgn * 3, ny_ + 1 + k * 2)
                b = (nx_ + sgn * 16, ny_ - 1 + k * 5)
                out.append(P(T(seg(a, b, 0.7)), (220, 206, 180)))
    sy = g - 3
    return [(k, [(fx + (x - fx) * SCALE, sy + (y - sy) * SCALE) for x, y in pts], c) for k, pts, c in out]
