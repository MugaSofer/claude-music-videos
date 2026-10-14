"""The man who paints the lines on roads lays down a long straight wish.

An empty road at 4am behind a roadworks hoarding. A man in an orange hi-vis jacket and a cap
walks a small line-marking machine along the road; behind him the fresh line gleams (paper
white, wet near the nozzle), ahead of him the old line is worn to crumbs. An amber beacon on the
machine turns, a work lamp throws a pool of light ahead, cones stand along the wet paint, his
breath clouds in the cold, and his flask steams on the kerb under the street lamp.

Light is drawn as stepped, *opaque* blends over colours this module knows (road, hoarding),
because the cut layer overwrites alpha rather than blending it.
"""
import numpy as np

# palette (STYLE.md) + a few set colours
INK = (21, 26, 51)
INDIGO = (31, 37, 80)
NAVY = (42, 47, 94)
MID = (59, 63, 116)
GOLD = (255, 201, 120)
WARM = (255, 216, 154)
RED = (184, 57, 46)
FOX = (212, 110, 51)
PAPER = (239, 230, 210)
ROSE = (244, 199, 168)
DBLUE = (159, 182, 216)
ROAD = (26, 26, 40)            # city.STREET's road colour: light pools are blended over this
HOARD = (46, 52, 92)           # plywood hoarding, painted navy
AMBER = (255, 158, 52)

LINE_Y0, LINE_Y1 = 1021, 1030  # the painted line's band on the road (nearer than his feet)
FOOT_Y = 1011                  # where his boots and the machine's wheels meet the road
HOARD_TOP = 736
SC = 1.3                       # the man and his machine are drawn at 1.3x about his feet
V, X0 = 46.0, -250.0           # walking speed (world px/s) and his hip x at tl = 0 (relative to cx)


# ------------------------------------------------------------------ small geometry helpers
def P(pts, col):
    return ('poly', [(float(x), float(y)) for x, y in pts], tuple(int(round(c)) for c in col))


def E(x0, y0, x1, y1, col):
    return ('ell', (float(x0), float(y0), float(x1), float(y1)), tuple(int(round(c)) for c in col))


def R(x0, y0, x1, y1, col):
    return P([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col)


def circ(x, y, r, col):
    return E(x - r, y - r, x + r, y + r, col)


def mix(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(len(a)))


def add(base, light, k):
    return tuple(min(250.0, base[i] + light[i] * k) for i in range(3))


def ellipse_pts(x, y, rx, ry, n=28):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return list(zip(x + rx * np.cos(a), y + ry * np.sin(a)))


def clip_y(pts, lo, hi):
    """Clip a polygon to lo <= y <= hi (Sutherland-Hodgman against two horizontal edges)."""
    def edge(poly, inside, cut):
        out = []
        for i in range(len(poly)):
            a, b = poly[i - 1], poly[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(cut(a, b))
                out.append(b)
            elif ia:
                out.append(cut(a, b))
        return out

    def at(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) or 1e-9), y)
    pts = edge(pts, lambda p: p[1] >= lo, at(lo))
    return edge(pts, lambda p: p[1] <= hi, at(hi)) if pts else []


def limb(a, b, w0, w1, col):
    (ax, ay), (bx, by) = a, b
    d = np.hypot(bx - ax, by - ay) or 1e-6
    nx, ny = -(by - ay) / d, (bx - ax) / d
    return P([(ax + nx * w0, ay + ny * w0), (bx + nx * w1, by + ny * w1),
              (bx - nx * w1, by - ny * w1), (ax - nx * w0, ay - ny * w0)], col)


def ik(a, b, l1, l2, sign):
    (ax, ay), (bx, by) = a, b
    d = min(np.hypot(bx - ax, by - ay), l1 + l2 - 0.5)
    d = max(d, 1e-3)
    ux, uy = (bx - ax), (by - ay)
    n = np.hypot(ux, uy) or 1e-6
    ux, uy = ux / n, uy / n
    along = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = np.sqrt(max(l1 * l1 - along * along, 0))
    return (ax + ux * along - uy * h * sign, ay + uy * along + ux * h * sign)


def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def lit_band(y0, y1, x0, x1, base, light, k, steps=3, feather=0.5):
    """A horizontal gradient pool on the road, as stepped opaque rects (fallback helper)."""
    return [R(x0, y0, x1, y1, add(base, light, k))]


def _scale(items, ox, oy, s):
    out = []
    for kind, c, col in items:
        if kind == 'poly':
            out.append((kind, [(ox + (x - ox) * s, oy + (y - oy) * s) for x, y in c], col))
        else:
            out.append((kind, (ox + (c[0] - ox) * s, oy + (c[1] - oy) * s, ox + (c[2] - ox) * s,
                               oy + (c[3] - oy) * s), col))
    return out


# ------------------------------------------------------------------ the static set
def _worn_dashes(cx):
    """The old, worn line: broken crumbs of grey paint. Deterministic."""
    g = np.random.default_rng(7201)
    out = []
    x = cx - 1500
    while x < cx + 700:
        w = g.uniform(6, 34)
        if g.random() < 0.6:
            y0 = LINE_Y0 + g.uniform(0, 4)
            y1 = LINE_Y1 - g.uniform(0, 4)
            out.append((x, y0, x + w, y1, g.uniform(0.2, 1.0)))
        x += w + g.uniform(3, 26)
    return out


def _lamp_k(x, cx):
    """How strongly the street lamp (at cx+372) lights the hoarding/road at world x."""
    return float(np.exp(-((x - (cx + 350)) / 190.0) ** 2))


def set_items(cx, ground):
    g = ground
    it = []
    # --- the hoarding along the far pavement: plywood panels, posters, a lit wash from the lamp
    x0, x1 = cx - 520, cx + 520
    it.append(R(x0, HOARD_TOP - 6, x1, g - 1, (32, 36, 66)))                    # frame / top rail
    px = x0
    k = 0
    while px < x1:
        w = 118 if k % 3 else 104
        mcx = px + w / 2
        lk = _lamp_k(mcx, cx)
        col = add(mix(HOARD, NAVY, 0.25 * (k % 2)), GOLD, 0.24 * lk)
        it.append(R(px + 2, HOARD_TOP, px + w - 2, g - 3, col))
        # a grain streak on each panel
        it.append(R(px + 14 + (k * 17) % 60, HOARD_TOP + 8, px + 17 + (k * 17) % 60, g - 10,
                    add(mix(HOARD, INK, 0.25), GOLD, 0.18 * lk)))
        px += w
        k += 1
    # posters (gig bills, one torn) pasted on the hoarding
    posters = [(-400, 772, 62, 86, ROSE, 0.0), (-330, 790, 50, 70, DBLUE, 0.3), (-96, 764, 58, 80, PAPER, 0.1),
               (-36, 782, 44, 64, FOX, 0.0), (150, 776, 60, 84, ROSE, 0.2)]
    for dx, py, w, h, col, tear in posters:
        lk = _lamp_k(cx + dx, cx)
        base = mix(col, HOARD, 0.62 - 0.3 * lk)
        pts = [(cx + dx, py), (cx + dx + w, py + 3), (cx + dx + w - 2, py + h), (cx + dx + 2, py + h - 2)]
        if tear:
            pts = pts[:2] + [(cx + dx + w - 1, py + h * (0.6 - tear)), (cx + dx + w * 0.55, py + h * 0.75),
                             (cx + dx + w * 0.7, py + h)] + pts[3:]
        it.append(P(pts, base))
        ink = mix(base, INK, 0.55)
        it.append(R(cx + dx + 8, py + 10, cx + dx + w - 10, py + 22, ink))           # a headline
        it.append(circ(cx + dx + w / 2, py + h * 0.55, min(w, h) * 0.18, ink))       # a moon / a face
        it.append(R(cx + dx + 10, py + h - 18, cx + dx + w * 0.6, py + h - 13, ink))

    # --- the far kerb (a lit band in the lamp pool)
    for xx in range(x0, x1, 40):
        it.append(R(xx, g - 5, xx + 38, g + 5, add((58, 56, 74), GOLD, 0.35 * _lamp_k(xx + 20, cx))))

    # --- the road surface: patches, cracks, a drain, the worn old line
    it.append(R(x0, g + 5, x1, g + 200, ROAD))
    for dx, y, w, h in ((-440, 948, 150, 22), (-120, 1052, 210, 18), (220, 960, 120, 16), (390, 1046, 90, 20)):
        it.append(P([(cx + dx, y), (cx + dx + w, y + 2), (cx + dx + w - 6, y + h), (cx + dx + 4, y + h - 1)],
                    (31, 31, 47)))
    for dx, y in ((-300, 990), (60, 1062), (330, 986)):                         # hairline cracks
        it.append(P([(cx + dx, y), (cx + dx + 40, y + 3), (cx + dx + 70, y + 1), (cx + dx + 71, y + 3),
                     (cx + dx + 40, y + 5), (cx + dx, y + 2)], (18, 18, 30)))
    it.append(R(cx - 212, g + 8, cx - 168, g + 16, (18, 18, 30)))                  # drain grate
    for j in range(5):
        it.append(R(cx - 208 + j * 8, g + 10, cx - 204 + j * 8, g + 14, (40, 40, 58)))
    # the street lamp's pool on the road by the far kerb
    for s, (rx, ry, kk) in enumerate(((230, 30, 0.10), (160, 22, 0.17), (90, 13, 0.25))):
        it.append(P(clip_y(ellipse_pts(cx + 350, g + 12, rx, ry), g + 5, g + 60), add(ROAD, GOLD, kk)))
    for x_, y0, x1_, y1, wear in _worn_dashes(cx):
        it.append(R(x_, y0, x1_, y1, mix((92, 90, 100), ROAD, 0.25 + 0.45 * wear)))

    # --- the street lamp, standing in front of the hoarding
    lx = cx + 372
    it.append(R(lx - 5, 440, lx + 5, g, (36, 40, 72)))
    it.append(R(lx - 9, g - 40, lx + 9, g, (36, 40, 72)))
    it.append(P([(lx - 3, 446), (lx + 1, 438), (lx - 40, 428), (lx - 70, 432), (lx - 70, 438), (lx - 40, 436)],
                (36, 40, 72)))
    it.append(P([(lx - 94, 432), (lx - 50, 432), (lx - 56, 446), (lx - 88, 446)], (46, 50, 86)))
    for r_, col in ((26, add(MID, GOLD, 0.22)), (16, add(MID, GOLD, 0.5)), (9, (255, 222, 160))):
        it.append(E(lx - 72 - r_ * 1.4, 446 - r_ * 0.4, lx - 72 + r_ * 1.4, 446 + r_ * 0.7, col))

    # --- the 'road works' sign on its A-frame at the kerb
    sx = cx + 196
    it.append(limb((sx - 16, g), (sx - 4, g - 70), 2.5, 2.5, INK))
    it.append(limb((sx + 16, g), (sx + 4, g - 70), 2.5, 2.5, INK))
    tri = [(sx, g - 128), (sx + 34, g - 70), (sx - 34, g - 70)]
    it.append(P(tri, mix(RED, HOARD, 0.15)))
    it.append(P([(sx, g - 116), (sx + 24, g - 76), (sx - 24, g - 76)], mix(PAPER, HOARD, 0.3)))
    it.append(circ(sx + 3, g - 103, 3.5, INK))                                     # the little digging man
    it.append(P([(sx + 1, g - 99), (sx + 6, g - 99), (sx + 3, g - 88), (sx - 5, g - 81), (sx - 7, g - 84),
                 (sx - 1, g - 89)], INK))
    it.append(P([(sx - 14, g - 80), (sx - 4, g - 80), (sx - 6, g - 78), (sx - 14, g - 78)], INK))
    it.append(limb((sx + 6, g - 96), (sx - 12, g - 82), 1.2, 1.2, INK))
    it.append(R(sx - 30, g - 70, sx + 30, g - 60, INK))

    # --- the flask and its cup on the kerb, in the lamp pool
    fx = cx + 300
    it.append(E(fx - 18, g - 5, fx + 30, g + 3, (32, 30, 50)))                   # their shadow
    it.append(R(fx - 8, g - 50, fx + 8, g - 4, (48, 92, 88)))
    it.append(R(fx - 8, g - 50, fx - 2, g - 4, (70, 124, 112)))                   # lamp-side highlight
    it.append(R(fx - 6, g - 58, fx + 6, g - 50, (36, 40, 72)))
    it.append(P([(fx + 14, g - 16), (fx + 28, g - 16), (fx + 26, g - 3), (fx + 16, g - 3)], (48, 92, 88)))
    it.append(E(fx + 14, g - 19, fx + 28, g - 13, (130, 90, 60)))                 # tea

    # --- traffic cones along the far side of the line
    for dx in (-700, -540, -380):
        it += _cone(cx + dx, 970, 1.0)
    return it


def _cone(x, base, s):
    it = []
    h, w = 54 * s, 17 * s
    it.append(E(x - 26 * s, base - 4 * s, x + 30 * s, base + 5 * s, (16, 16, 28)))         # shadow
    it.append(P([(x - 20 * s, base - 6 * s), (x + 20 * s, base - 6 * s), (x + 22 * s, base),
                 (x - 22 * s, base)], INK))
    body = [(x - 3 * s, base - h), (x + 3 * s, base - h), (x + w, base - 6 * s), (x - w, base - 6 * s)]
    it.append(P(body, FOX))
    it.append(P([(x - 3 * s, base - h), (x, base - h), (x - 3 * s, base - 6 * s), (x - w, base - 6 * s)],
                (170, 80, 42)))
    yb0, yb1 = base - h * 0.62, base - h * 0.40                                     # reflective collar
    k0, k1 = (yb0 - (base - h)) / (h - 6 * s), (yb1 - (base - h)) / (h - 6 * s)
    it.append(P([(x - 3 * s - (w - 3 * s) * k0, yb0), (x + 3 * s + (w - 3 * s) * k0, yb0),
                 (x + 3 * s + (w - 3 * s) * k1, yb1), (x - 3 * s - (w - 3 * s) * k1, yb1)], (214, 206, 190)))
    return it


# ------------------------------------------------------------------ the living part
def _man(hx, tl, flash):
    """The line painter, walking right, arms forward on the machine's handle. Returns (items, grip)."""
    T = 1.5
    ph = (tl / T) % 1.0
    S = V * T / 2
    bob = 2.2 * abs(np.cos(np.pi * 2 * ph))
    hip = (hx, 917 - bob)
    sh = (hx + 24, 859 - bob)
    head = (hx + 37, 836 - bob + 0.8 * np.sin(tl * 1.1))
    grip = (hx + 68, 904 - bob * 0.3)

    def foot(p):
        if p < 0.5:
            return hx + S / 2 - S * (p / 0.5) - 6, 0.0
        u = (p - 0.5) / 0.5
        return hx - S / 2 + S * smooth(u) - 6, 9 * np.sin(np.pi * u)

    TROUS, TROUS_F = (58, 64, 112), (36, 41, 78)
    JACK, JACK_F = (228, 124, 52), (176, 90, 42)
    band = mix((200, 194, 178), (252, 244, 226), flash)
    it = []
    it.append(E(hx - 40, FOOT_Y - 4, hx + 50, FOOT_Y + 5, (16, 16, 28)))          # his shadow

    for which, ph2 in (('far', (ph + 0.5) % 1), ('near', ph)):
        fx, lift = foot(ph2)
        ankle = (fx, FOOT_Y - 8 - lift)
        h0 = (hip[0] + (-3 if which == 'far' else 3), hip[1])
        knee = ik(h0, ankle, 46, 46, -1)
        col = TROUS_F if which == 'far' else TROUS
        it.append(limb(h0, knee, 11, 9, col))
        it.append(circ(knee[0], knee[1], 8.5, col))
        it.append(limb(knee, ankle, 8.5, 7, col))
        it.append(limb(mix(knee, ankle, 0.5), mix(knee, ankle, 0.66), 8.6, 8.2,
                       mix(band, TROUS_F, 0.45) if which == 'far' else band))               # shin stripe
        boot = INK if which == 'near' else (16, 18, 36)
        toe = 0.25 * lift
        it.append(P([(ankle[0] - 8, ankle[1] - 5), (ankle[0] + 6, ankle[1] - 5), (ankle[0] + 17, ankle[1] + 1 - toe),
                     (ankle[0] + 17, ankle[1] + 8 - toe), (ankle[0] - 9, ankle[1] + 8)], boot))
        if which == 'far':                                                          # far arm, behind the body
            elbow = ik((sh[0] - 3, sh[1] + 4), (grip[0] - 3, grip[1] - 1), 33, 33, 1)
            it.append(limb((sh[0] - 3, sh[1] + 4), elbow, 8, 7, JACK_F))
            it.append(limb(elbow, (grip[0] - 3, grip[1] - 1), 7, 5.5, JACK_F))
            it.append(circ(grip[0] - 3, grip[1] - 1, 5.5, (16, 18, 36)))

    # jacket body (hangs over the hips), with two reflective bands
    lean = (sh[0] - hip[0], sh[1] - hip[1])

    def at(u, s):                                   # point on the torso: u up the spine, s across (-1 back, 1 front)
        return (hip[0] + lean[0] * u + s * (17 + 3 * u), hip[1] + 10 * (1 - u) + lean[1] * u)
    body = [at(0, -1.1), at(0.45, -1.05), at(0.9, -1), at(1.02, -0.5), at(1.02, 0.6), at(0.9, 1.05),
            at(0.45, 1.0), at(0, 1.05)]
    it.append(P(body, JACK))
    it.append(P([at(0, -1.1), at(0.45, -1.05), at(0.9, -1), at(0.9, -0.55), at(0.45, -0.6), at(0, -0.62)],
                mix(JACK, JACK_F, 0.55)))
    for u0, u1 in ((0.22, 0.32), (0.55, 0.65)):
        it.append(P([at(u0, -1.06), at(u0, 1.02), at(u1, 1.02), at(u1, -1.06)], band))
    it.append(P([at(0.96, -0.45), at(1.1, -0.1), at(1.08, 0.5), at(0.96, 0.55)], (36, 40, 72)))    # collar

    # head: neck, face, ear, cap with a brim
    hx_, hy = head
    SKIN = (190, 138, 112)
    it.append(limb((sh[0] + 3, sh[1] - 2), (hx_ - 2, hy + 8), 6, 6, mix(SKIN, INK, 0.3)))
    it.append(E(hx_ - 12, hy - 13, hx_ + 12, hy + 14, SKIN))
    it.append(P([(hx_ + 9, hy - 2), (hx_ + 16, hy + 4), (hx_ + 10, hy + 6)], SKIN))              # nose
    it.append(P([(hx_ - 12, hy - 4), (hx_ - 6, hy - 5), (hx_ - 8, hy + 10), (hx_ - 12, hy + 5)],
                (58, 44, 52)))                                                                 # short hair at the nape
    it.append(E(hx_ - 5, hy - 2, hx_ + 1, hy + 7, mix(SKIN, INK, 0.25)))                       # ear
    it.append(P([(hx_ + 2, hy + 9), (hx_ + 12, hy + 7), (hx_ + 8, hy + 13), (hx_ + 1, hy + 13)],
                mix(SKIN, INK, 0.3)))                                                          # chin shade
    it.append(circ(hx_ + 6, hy - 1, 1.6, INK))                                                 # eye
    it.append(P([(hx_ - 13, hy - 3), (hx_ - 12, hy - 12), (hx_ - 3, hy - 17), (hx_ + 8, hy - 16),
                 (hx_ + 13, hy - 8), (hx_ + 13, hy - 4)], (28, 34, 76)))                       # cap crown
    it.append(P([(hx_ + 6, hy - 7), (hx_ + 26, hy - 5), (hx_ + 25, hy - 2), (hx_ + 6, hy - 3)], INK))  # brim
    it.append(R(hx_ - 12, hy - 5, hx_ + 8, hy - 3, mix(band, (28, 34, 76), 0.5)))            # cap band

    # near arm, over the body, onto the handle
    s0 = (sh[0] + 3, sh[1] + 5)
    elbow = ik(s0, grip, 33, 33, 1)
    it.append(limb(s0, elbow, 9, 8, JACK))
    it.append(limb(elbow, grip, 8, 6.5, JACK))
    it.append(limb(mix(elbow, grip, 0.35), mix(elbow, grip, 0.55), 8.2, 7.5, band))           # cuff stripe
    it.append(circ(grip[0], grip[1], 6.5, INK))                                                # glove
    return it, grip, head


def _machine(tx, tl, flash, grip):
    """The line-marking machine: paint hopper, frame, wheels, handle, beacon, work lamp."""
    it = []
    Y = FOOT_Y
    FRAME = (34, 38, 70)
    BODY, BODY_D = (214, 176, 72), (170, 132, 54)
    it.append(E(tx - 60, Y - 4, tx + 70, Y + 6, (16, 16, 28)))                      # shadow
    # handle: from the grip down to the back of the frame
    it.append(limb(grip, (tx - 44, 966), 3.2, 3.2, FRAME))
    it.append(limb((grip[0] + 20, grip[1] + 18), (tx - 20, 952), 2.2, 2.2, FRAME))  # brace
    # chassis
    it.append(P([(tx - 50, 978), (tx + 52, 978), (tx + 56, 990), (tx - 50, 990)], FRAME))
    # paint hopper: a drum with a lid
    it.append(P([(tx - 34, 946), (tx + 30, 946), (tx + 34, 980), (tx - 38, 980)], BODY))
    it.append(P([(tx - 34, 946), (tx - 20, 946), (tx - 22, 980), (tx - 38, 980)], BODY_D))
    it.append(E(tx - 36, 939, tx + 32, 953, mix(BODY, PAPER, 0.25)))
    it.append(R(tx - 36, 962, tx + 33, 967, mix(BODY, INK, 0.45)))                 # a band on the drum
    it.append(P([(tx - 2, 953), (tx + 26, 953), (tx + 27, 959), (tx - 2, 959)], mix(BODY, PAPER, 0.4)))
    # the spray gun and shield, low on the near side, just behind centre
    it.append(limb((tx - 2, 990), (tx - 6, 1008), 1.8, 1.8, FRAME))                 # the spray gun's pipe
    it.append(P([(tx - 18, 1006), (tx + 6, 1006), (tx + 9, 1019), (tx - 20, 1019)], (60, 66, 106)))
    it.append(R(tx - 20, 1017, tx + 9, 1020, PAPER))                                 # paint on its lip
    # wheels
    for wx, r in ((tx - 34, 16), (tx + 40, 11)):
        it.append(circ(wx, Y - r, r, INK))
        it.append(circ(wx, Y - r, r * 0.45, (80, 84, 120)))
        a = -tl * V / r
        it.append(limb((wx + np.cos(a) * r * 0.45, Y - r + np.sin(a) * r * 0.45),
                       (wx + np.cos(a) * r * 0.85, Y - r + np.sin(a) * r * 0.85), 1.5, 1.5, (80, 84, 120)))
    # beacon: a short mast and an amber dome that pulses
    bx, by = tx + 8, 918
    it.append(R(bx - 2, by + 6, bx + 2, 942, FRAME))
    dome = mix((130, 70, 30), (255, 196, 96), flash)
    it.append(P([(bx - 9, by + 7), (bx + 9, by + 7), (bx + 8, by - 3), (bx, by - 8), (bx - 8, by - 3)], dome))
    it.append(R(bx - 10, by + 6, bx + 10, by + 10, INK))
    if flash > 0.5:
        it.append(P([(bx - 4, by + 5), (bx + 3, by + 5), (bx + 2, by - 3), (bx - 3, by - 3)], (255, 236, 190)))
    # work lamp on a stalk at the front, pointing forward and down
    it.append(limb((tx + 26, 950), (tx + 44, 926), 2.2, 2.2, FRAME))
    it.append(P([(tx + 38, 918), (tx + 54, 922), (tx + 50, 936), (tx + 36, 930)], (48, 52, 86)))
    it.append(P([(tx + 52, 921), (tx + 56, 923), (tx + 52, 936), (tx + 49, 935)], (255, 228, 170)))
    return it


def _beacon(tl):
    """A rotating beacon: a sharp flash twice a second-ish, easing out (backOut feel)."""
    p = (tl / 0.85) % 1.0
    return float(np.clip(np.cos(np.pi * p) ** 6 * 1.1, 0, 1))


def action_items(tl, cx, ground):
    g = ground
    it = []
    hx = cx + X0 + V * tl
    tx = hx + 108                                   # the machine, ahead of him (before scaling)
    nozzle = hx + (tx - 4 - hx) * SC
    flash = _beacon(tl)

    # --- light on the road first (everything else is cut out on top of it)
    # the beacon's amber sweep: a broad pool that pulses with each turn
    if flash > 0.05:
        for rx, ry, kk in ((150, 34, 0.07), (95, 22, 0.13)):
            pts = clip_y(ellipse_pts(hx + (tx + 8 - hx) * SC, 1006, rx, ry), g + 6, 1080)
            it.append(P(pts, add(ROAD, AMBER, kk * flash)))
    # the work lamp's cone and pool ahead of the machine
    lx, ly = hx + (tx + 54 - hx) * SC, FOOT_Y + (929 - FOOT_Y) * SC
    pcx, pcy = lx + 110, 1026
    for rx, ry, kk in ((120, 30, 0.11), (86, 21, 0.2), (52, 13, 0.32)):
        cone = [(lx, ly - 2), (lx, ly + 6)] + [(pcx + rx * np.cos(a), pcy + ry * np.sin(a))
                                              for a in np.linspace(np.pi * 0.62, -np.pi * 0.62, 14)]
        it.append(P(clip_y(cone, g + 6, 1080), add(ROAD, WARM, kk * 0.7)))
        it.append(P(clip_y(ellipse_pts(pcx, pcy, rx, ry), g + 6, 1080), add(ROAD, WARM, kk * 1.35)))
    # the old worn line reappears, lit, inside the pool (ahead of the nozzle only)
    for x_, y0, x1_, y1, wear in _worn_dashes(cx):
        if x1_ < nozzle or x_ > pcx + 120:
            continue
        a, b = max(x_, nozzle), x1_
        base = mix((92, 90, 100), ROAD, 0.25 + 0.45 * wear)
        yy = (y0 + y1) / 2 - pcy
        for rx, ry, kk in ((120, 30, 0.11), (86, 21, 0.2), (52, 13, 0.32)):
            if abs(yy) >= ry:
                continue
            half = rx * np.sqrt(1 - (yy / ry) ** 2)
            aa, bb = max(a, pcx - half), min(b, pcx + half)
            if bb > aa:
                it.append(R(aa, y0, bb, y1, add(base, WARM, kk * 1.2)))

    # --- the new line: dry and matt far behind, wet and gleaming near the nozzle
    start = cx - 1500
    it.append(R(start, LINE_Y0, nozzle, LINE_Y1, (224, 215, 194)))
    for k, (dx, col) in enumerate(((420, (232, 223, 202)), (220, PAPER), (90, (246, 239, 222)))):
        it.append(R(max(start, nozzle - dx), LINE_Y0, nozzle, LINE_Y1, col))
    it.append(R(max(start, nozzle - 160), LINE_Y0, nozzle - 2, LINE_Y0 + 2, (250, 246, 234)))    # wet glint
    it.append(R(start, LINE_Y1, nozzle, LINE_Y1 + 2, (16, 16, 28)))                              # its paper edge
    for k in range(3):                                                             # a glint that travels
        gx = nozzle - 40 - ((tl * 70 + k * 130) % 390)
        it.append(R(gx - 10, LINE_Y0 + 2, gx + 10, LINE_Y0 + 4, (250, 247, 238)))
    # the beacon's amber catching the wet line
    if flash > 0.05:
        it.append(R(max(start, tx - 130), LINE_Y0, nozzle, LINE_Y0 + 3, add((224, 215, 194), AMBER, 0.15 * flash)))

    # --- the man and his machine
    man, grip, head = _man(hx, tl, flash)
    mach = _machine(tx, tl, flash, grip)
    man, mach = _scale(man, hx, FOOT_Y, SC), _scale(mach, hx, FOOT_Y, SC)
    head = (hx + (head[0] - hx) * SC, FOOT_Y + (head[1] - FOOT_Y) * SC)
    bx, by = hx + (tx + 8 - hx) * SC, FOOT_Y + (918 - FOOT_Y) * SC
    if flash > 0.05:                                  # the beacon's halo, blended over what's behind it
        for r_, kk in ((46, 0.10), (30, 0.2), (18, 0.36)):
            pts = ellipse_pts(bx, by, r_ * 1.2, r_)
            for lo, hi, base in ((g + 5, 1100, ROAD),):
                q = clip_y(pts, lo, hi)
                if len(q) > 2:
                    it.append(P(q, add(base, AMBER, kk * flash)))
    it += man[:1] + mach[:1]                          # shadows first
    it += man[1:] + mach[1:]

    # --- his breath clouds in the cold, every few seconds
    for k in range(2):
        age = (tl - k * 1.6) % 3.2
        if age < 1.4:
            u = age / 1.4
            bx = head[0] + 34 + u * 34
            by = head[1] + 8 - u * 16
            r = 3 + u * 9
            col = mix((150, 150, 176), HOARD, u * 0.9)
            it.append(E(bx - r * 1.3, by - r, bx + r * 1.3, by + r, col))
            it.append(E(bx + r * 0.6, by - r * 1.3, bx + r * 2.0, by + r * 0.2, col))

    # --- steam from the tea on the kerb
    fx = cx + 300 + 21
    for k in range(3):
        age = (tl * 0.55 + k / 3) % 1.0
        y = g - 20 - age * 70
        sway = 5 * np.sin(tl * 1.7 + k * 2.1 + age * 5)
        r = 2.5 + age * 5
        col = mix((150, 144, 150), mix(HOARD, GOLD, 0.2), age)
        it.append(E(fx + sway - r, y - r * 1.6, fx + sway + r, y + r * 1.6, col))

    # --- a near cone in the foreground, for depth (drawn last: it is closest)
    it += _cone(cx - 360, 1080, 1.55)
    return it
