"""And the last light in the tower block is someone thinking about you.

A concrete tower block, far taller than its neighbours, running up out of frame: slab bands,
pilasters, end balconies with railings and a satellite dish, a grid of dark windows, two with
the cold blue flicker of a television. Exactly one window is warm. Inside it someone sits by the
glass with a mug held in both hands, looking out across the city: a curtain edge breathes in
the draught, a plant on the sill, steam off the tea. Now and then they sip; at one point their
phone lights up on the sill and they glance down at it, then back out, head tilted a little,
as if they were thinking about someone. A red aircraft light blinks on the roof mast.

All motion loops seamlessly over 8 s (the film keeps this vignette running in the background
with tl = 3 + t % 8). Light is drawn as stepped opaque blends over known colours, because the
cut layer overwrites alpha rather than blending it.
"""
import numpy as np

INK = (21, 26, 51)
INDIGO = (31, 37, 80)
NAVY = (42, 47, 94)
MID = (59, 63, 116)
GOLD = (255, 201, 120)
WARM = (255, 216, 154)
RED = (184, 57, 46)
PAPER = (239, 230, 210)
DBLUE = (159, 182, 216)

CONC = (41, 45, 86)           # the tower's front face
CONC_SIDE = (28, 32, 64)
SLAB = (52, 56, 100)
PIER = (35, 39, 76)
GLASS = (20, 23, 46)
GLASS_HI = (28, 32, 62)
FRAME = (58, 62, 106)
SIL = (44, 32, 46)            # the person, a warm-dark silhouette against the lamp

HALF = 300                    # the tower spans cx-300 .. cx+300 (plus a side face to cx+330)
BAY = 150
FLOOR = 150
LOBBY_TOP = 790
TOP = -110                    # roof line (runs out of the vignette frame above)
LIT_FLOOR, LIT_BAY = 1, 2     # floor index (0 = lowest flat floor) and bay of the one warm window
LOOP = 8.0


# ------------------------------------------------------------------ helpers
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


def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def env(u, a, b, c, d):
    """0 before a, eases to 1 by b, holds, eases back to 0 from c to d."""
    return smooth((u - a) / (b - a)) * (1 - smooth((u - c) / (d - c)))


def hsh(i):
    return (np.sin(i * 12.9898 + 78.233) * 43758.5453) % 1.0


def rot(pts, ox, oy, a):
    c, s = np.cos(a), np.sin(a)
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in pts]


def ellipse_pts(x, y, rx, ry, n=28):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return list(zip(x + rx * np.cos(a), y + ry * np.sin(a)))


def clip_rect(pts, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of a polygon to an axis-aligned rectangle."""
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

    def cx_(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / ((b[0] - a[0]) or 1e-9))

    def cy_(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) or 1e-9), y)
    for inside, cut in ((lambda p: p[0] >= x0, cx_(x0)), (lambda p: p[0] <= x1, cx_(x1)),
                        (lambda p: p[1] >= y0, cy_(y0)), (lambda p: p[1] <= y1, cy_(y1))):
        pts = edge(pts, inside, cut)
        if not pts:
            return []
    return pts


def _scale(items, ox, oy, s):
    out = []
    for kind, c, col in items:
        if kind == 'poly':
            out.append((kind, [(ox + (x - ox) * s, oy + (y - oy) * s) for x, y in c], col))
        else:
            out.append((kind, (ox + (c[0] - ox) * s, oy + (c[1] - oy) * s, ox + (c[2] - ox) * s,
                               oy + (c[3] - oy) * s), col))
    return out


def floor_top(k):
    return LOBBY_TOP - FLOOR * (k + 1)


def big_window(cx, k, b):
    bx = cx - HALF + b * BAY
    ft = floor_top(k)
    return bx + 14, ft + 24, bx + 112, ft + 118


def small_window(cx, k, b):
    bx = cx - HALF + b * BAY
    ft = floor_top(k)
    return bx + 124, ft + 34, bx + 140, ft + 96


def _floors():
    k = 0
    while floor_top(k) >= TOP - 1:
        yield k
        k += 1


TV = [(3, 0), (0, 3)]          # (floor, bay) of the television windows


# ------------------------------------------------------------------ the static set
def set_items(cx, ground):
    g = ground
    it = []
    L, Rr = cx - HALF, cx + HALF
    # neighbours: low blocks either side, so the tower reads as much taller
    it.append(R(cx - 470, 640, L - 6, g, (36, 38, 74)))
    it.append(R(cx - 474, 632, L - 2, 644, (46, 49, 88)))
    for yy in (672, 742, 812):
        for xx in (cx - 450, cx - 400, cx - 350):
            it.append(R(xx, yy, xx + 26, yy + 36, (26, 28, 56)))
    it.append(R(Rr + 36, 700, cx + 480, g, (38, 40, 78)))
    it.append(P([(Rr + 30, 700), (cx + 486, 700), (cx + 470, 684), (Rr + 44, 684)], (46, 49, 88)))
    for yy in (730, 800):
        for xx in (Rr + 60, Rr + 112):
            it.append(R(xx, yy, xx + 30, yy + 40, (26, 28, 56)))

    # the block: side face, front face, roof
    it.append(P([(Rr, TOP), (Rr + 34, TOP + 22), (Rr + 34, g), (Rr, g)], CONC_SIDE))
    for y in range(int(TOP) + 60, g, FLOOR):                                        # side slab lines
        it.append(P([(Rr, y), (Rr + 34, y + 6), (Rr + 34, y + 12), (Rr, y + 8)], (40, 44, 82)))
    it.append(R(L, TOP, Rr, g, CONC))
    it.append(R(L - 6, TOP - 16, Rr + 6, TOP + 2, SLAB))                             # parapet
    it.append(R(cx - 170, TOP - 70, cx - 60, TOP - 14, PIER))                        # lift housing
    it.append(R(cx - 176, TOP - 76, cx - 54, TOP - 68, SLAB))
    it.append(R(cx + 120, TOP - 100, cx + 124, TOP - 14, PIER))                      # the mast
    it.append(R(cx + 110, TOP - 60, cx + 134, TOP - 56, PIER))
    it.append(R(cx + 60, TOP - 40, cx + 100, TOP - 14, PIER))                        # water tank

    # piers between bays
    for b in range(5):
        x = L + b * BAY
        it.append(R(x - 6, TOP, x + 6, LOBBY_TOP, PIER))
    # floors: slab bands, windows, balconies
    lx0, ly0, lx1, ly1 = big_window(cx, LIT_FLOOR, LIT_BAY)
    for k in _floors():
        ft = floor_top(k)
        it.append(R(L, ft + FLOOR - 12, Rr, ft + FLOOR, SLAB))
        it.append(R(L, ft + FLOOR - 2, Rr, ft + FLOOR, (74, 78, 126)))
        for b in range(4):
            x0, y0, x1, y1 = big_window(cx, k, b)
            lit = (k, b) == (LIT_FLOOR, LIT_BAY)
            if lit:
                # warm spill on the concrete round the one lit window (stepped, like tissue layers)
                for pad, kk in ((30, 0.07), (17, 0.13), (8, 0.22)):
                    it.append(R(x0 - pad, y0 - pad, x1 + pad, min(y1 + pad, ft + FLOOR - 12), add(CONC, WARM, kk)))
                it.append(R(x0 - 34, ft + FLOOR - 12, x1 + 34, ft + FLOOR, add(SLAB, WARM, 0.12)))
            it.append(R(x0 - 4, y0 - 4, x1 + 4, y1 + 6, add(FRAME, WARM, 0.25) if lit else FRAME))
            if not lit:
                h = hsh(k * 7 + b * 3 + 1)
                glass = GLASS if h > 0.3 else (38, 30, 56)                           # some have curtains
                it.append(R(x0, y0, x1, y1, glass))
                it.append(P([(x0 + 10, y0), (x0 + 30, y0), (x0 + 8, y1 * 0.5 + y0 * 0.5), (x0, y1 * 0.5 + y0 * 0.5)],
                            GLASS_HI))                                               # a sheen
                it.append(R(x0 + 30, y0, x0 + 34, y1, FRAME))                         # mullion
                it.append(R(x0, y0 + 22, x1, y0 + 25, FRAME))                         # transom
            sx0, sy0, sx1, sy1 = small_window(cx, k, b)
            it.append(R(sx0 - 3, sy0 - 3, sx1 + 3, sy1 + 3, FRAME))
            it.append(R(sx0, sy0, sx1, sy1, (26, 30, 58) if hsh(k * 5 + b) > 0.2 else (60, 70, 100)))
            if b in (0, 3) and not lit:                                               # balconies at the ends
                it += _balcony(x0 - 8, x1 + 8, y1, k, b)

    # the lobby: a cool, empty, fluorescent entrance (not warm: there is only one warm light)
    it.append(R(L, LOBBY_TOP, Rr, g, (44, 48, 90)))
    it.append(R(cx - 70, 810, cx + 70, g, (70, 84, 118)))
    it.append(R(cx - 64, 816, cx + 64, g, (96, 116, 150)))
    it.append(R(cx - 2, 816, cx + 2, g, (70, 84, 118)))
    it.append(R(cx - 96, 800, cx + 96, 808, SLAB))                                  # canopy
    for dx in (-250, -180, 160, 230):
        it.append(R(cx + dx, 820, cx + dx + 36, 860, (26, 30, 58)))
    it.append(R(cx - 290, g - 18, cx - 130, g, (30, 44, 50)))                      # a hedge
    it.append(R(cx + 130, g - 18, cx + 290, g, (30, 44, 50)))

    # the lit room (behind the figure): back wall, a standard lamp, a picture, the sill
    x0, y0, x1, y1 = lx0, ly0, lx1, ly1
    it.append(R(x0, y0, x1, y1, (226, 162, 104)))
    for ex, ey, rx, ry, col in ((x1 - 20, y0 + 42, 90, 80, (242, 190, 126)), (x1 - 18, y0 + 40, 58, 54, (252, 210, 146)),
                                (x1 - 16, y0 + 38, 30, 30, (255, 228, 176))):
        it.append(P(clip_rect(ellipse_pts(ex, ey, rx, ry), x0, y0, x1, y1), col))     # lamp glow on the wall
    it.append(R(x0 + 40, y0 + 34, x0 + 62, y0 + 52, (214, 158, 104)))              # a small picture
    it.append(R(x0 + 43, y0 + 37, x0 + 59, y0 + 49, (236, 186, 128)))
    it.append(P([(x1 - 22, y0 + 30), (x1 - 4, y0 + 30), (x1 - 8, y0 + 44), (x1 - 18, y0 + 44)], (255, 238, 196)))  # lampshade
    it.append(R(x1 - 14, y0 + 44, x1 - 12, y1, (196, 136, 92)))
    it.append(R(x0, y1 - 8, x1, y1, (214, 150, 98)))                               # the inner sill
    return it


def _balcony(x0, x1, y, k, b):
    it = []
    it.append(R(x0, y - 2, x1, y + 8, SLAB))                                         # slab
    it.append(R(x0, y - 36, x1, y - 32, (78, 82, 128)))                              # rail
    for xx in np.arange(x0 + 4, x1, 9):
        it.append(R(xx, y - 32, xx + 2, y - 2, (60, 64, 108)))
    h = hsh(k * 11 + b)
    if h < 0.35:                                                                     # a satellite dish
        dx = x0 + 18
        it.append(E(dx - 12, y - 64, dx + 10, y - 38, (86, 90, 132)))
        it.append(R(dx - 1, y - 40, dx + 2, y - 30, (60, 64, 108)))
    elif h < 0.65:                                                                   # a plant in a pot
        px = x1 - 24
        it.append(R(px - 8, y - 20, px + 8, y - 2, (58, 46, 60)))
        it.append(P([(px - 14, y - 40), (px - 2, y - 20), (px, y - 50), (px + 4, y - 20), (px + 16, y - 42),
                     (px + 6, y - 18), (px - 6, y - 18)], (34, 50, 58)))
    else:                                                                            # a drying rack
        it.append(P([(x0 + 20, y - 2), (x0 + 50, y - 46), (x0 + 54, y - 46), (x0 + 24, y - 2)], (70, 74, 118)))
        it.append(R(x0 + 30, y - 44, x0 + 50, y - 22, (92, 84, 118)))
    return it


# ------------------------------------------------------------------ the living part
def _tv(k, b, u):
    step = int(u * 5)
    v = hsh(step * 3.1 + k * 17 + b)
    return mix((52, 70, 128), (120, 150, 208), v)


def action_items(tl, cx, ground):
    it = []
    u = tl % LOOP
    # televisions flicker, cold blue
    for k, b in TV:
        x0, y0, x1, y1 = big_window(cx, k, b)
        c = _tv(k, b, u)
        it.append(R(x0, y0, x1, y1, mix(c, GLASS, 0.62)))
        it.append(R(x0 + 30, y0, x0 + 34, y1, FRAME))
        it.append(R(x0, y0 + 22, x1, y0 + 25, FRAME))
        it.append(R(x0 + 50, y0 + 44, x1 - 8, y1, mix(c, GLASS, 0.4)))              # the glow of the screen
        it.append(R(x0 + 4, y1 - 30, x0 + 44, y1, mix(GLASS, INK, 0.3)))             # a sofa back
    # aircraft warning light on the mast
    on = (u % 2.0) < 0.35
    mx, my = cx + 122, TOP - 102
    it.append(circ(mx, my, 9 if on else 5, (255, 96, 70) if on else (110, 40, 40)))
    if on:
        it.append(circ(mx, my, 4, (255, 200, 170)))

    # ---- the one warm window
    x0, y0, x1, y1 = big_window(cx, LIT_FLOOR, LIT_BAY)
    sip = env(u, 0.8, 1.4, 2.1, 2.8)                      # the mug rises to the lips and back
    phone = env(u, 4.0, 4.2, 6.2, 6.9)                    # the phone lights on the sill
    glance = env(u, 4.35, 4.75, 5.6, 6.1)                 # head dips to look at it
    after = env(u, 5.9, 6.6, 7.2, 7.9)                    # then a small tilt, looking out again
    breathe = np.sin(2 * np.pi * u / 4.0)

    # phone light on the sill and wall (cool)
    px, py = x0 + 43, y1 - 8
    if phone > 0.02:
        it.append(E(px - 18, py - 10, px + 22, py + 4, mix((214, 150, 98), (200, 214, 230), 0.5 * phone)))

    # the person, seated, facing left (out across the city), from the waist up
    person = []
    hx, hy = x0 + 64, y0 + 42 + 0.6 * breathe                # head centre
    nx, ny = x0 + 66, y0 + 56                               # neck pivot
    head_a = -0.28 * glance + 0.09 * after + 0.07 * sip     # - = dips toward the phone, + = looks up
    sh_y = y0 + 62 + 0.8 * breathe
    body = [(x0 + 50, y1 - 6), (x0 + 52, sh_y + 10), (x0 + 58, sh_y + 1), (x0 + 70, sh_y - 2),
            (x0 + 82, sh_y + 4), (x0 + 88, sh_y + 18), (x0 + 92, y1 - 6)]
    person.append(P(body, SIL))
    person.append(P([(x0 + 84, sh_y + 6), (x0 + 88, sh_y + 18), (x0 + 92, y1 - 6), (x0 + 89, y1 - 6),
                 (x0 + 85, sh_y + 18)], (120, 76, 60)))                       # rim light from the lamp
    person.append(R(x0 + 61, y0 + 50, x0 + 71, sh_y + 4, SIL))                       # neck
    # head: profile facing left, with a loose bun
    prof = [(hx + 9, hy - 9), (hx + 2, hy - 12), (hx - 6, hy - 11), (hx - 9, hy - 6), (hx - 10, hy - 2),
            (hx - 13, hy + 2), (hx - 10, hy + 4), (hx - 10, hy + 7), (hx - 8, hy + 8), (hx - 9, hy + 10),
            (hx - 5, hy + 13), (hx + 2, hy + 12), (hx + 8, hy + 10), (hx + 11, hy + 2)]
    person.append(P(rot(prof, nx, ny, head_a), SIL))
    bun = rot([(hx + 10, hy - 8)], nx, ny, head_a)[0]
    person.append(circ(bun[0], bun[1], 6.5, SIL))
    nape = rot([(hx + 6, hy + 4), (hx + 11, hy + 3), (hx + 10, hy + 12), (hx + 5, hy + 14)], nx, ny, head_a)
    person.append(P(nape, SIL))
    # arms and the mug: both hands round it, in front of the chest
    mug_x = x0 + 46 + 4 * sip
    mug_y = y0 + 72 - 16 * sip
    person.append(P([(x0 + 60, sh_y + 6), (x0 + 54, sh_y + 26), (mug_x + 8, mug_y + 10), (mug_x + 10, mug_y + 2),
                 (x0 + 62, sh_y + 16)], mix(SIL, INK, 0.2)))                        # forearm
    person.append(R(mug_x - 4, mug_y - 3, mug_x + 6, mug_y + 8, SIL))                      # the mug
    person.append(P([(mug_x - 4, mug_y), (mug_x - 8, mug_y + 1), (mug_x - 8, mug_y + 5), (mug_x - 4, mug_y + 6),
                 (mug_x - 4, mug_y + 4.5), (mug_x - 6.5, mug_y + 4), (mug_x - 6.5, mug_y + 2), (mug_x - 4, mug_y + 1.5)], SIL))
    person.append(circ(mug_x + 6, mug_y + 3, 4, SIL))                                      # hand
    it += _scale(person, x0 + 72, y1, 1.15)
    # steam from the mug when it's down
    st = 1 - sip
    for i in range(3):
        age = (u * 0.5 + i / 3) % 1.0
        sx = x0 + 72 + (mug_x - 1 - x0 - 72) * 1.15 + 4 * np.sin(u * 2.4 + i * 2.0 + age * 6) * (0.4 + age)
        sy = y1 + (mug_y - 6 - y1) * 1.15 - age * 26
        r = 1.6 + age * 2.4
        if st > 0.2 and sy > y0 + 4:
            it.append(E(sx - r, sy - r * 1.8, sx + r, sy + r * 1.8, mix((255, 238, 208), (246, 196, 130), age * 0.7)))

    # the sill: a plant and the phone
    for a, L_ in ((-0.9, 18), (-0.4, 24), (0.15, 26), (0.6, 18), (-1.3, 12), (1.0, 12)):
        sway = 0.05 * np.sin(2 * np.pi * u / 4.0 + a)
        tip = (x0 + 22 + np.sin(a + sway) * L_, y1 - 20 - np.cos(a + sway) * L_)
        it.append(P([(x0 + 20, y1 - 19), (tip[0] - 3, tip[1] + 2), tip, (x0 + 24, y1 - 19)], (58, 80, 52)))
    it.append(P([(x0 + 15, y1 - 21), (x0 + 29, y1 - 21), (x0 + 27, y1 - 8), (x0 + 17, y1 - 8)], (164, 90, 62)))  # pot
    it.append(R(px - 7, py - 3, px + 7, py, mix((30, 30, 40), (225, 238, 250), phone)))

    # the curtain at the left edge, breathing in the draught
    sw = 2.2 * np.sin(2 * np.pi * u / 4.0) + 1.2
    cur = [(x0, y0), (x0 + 13, y0), (x0 + 10 + sw * 0.4, y0 + 30), (x0 + 13 + sw, y0 + 60),
           (x0 + 10 + sw * 1.5, y1 - 8), (x0, y1 - 8)]
    it.append(P(cur, (206, 128, 84)))
    it.append(P([(x0 + 3, y0), (x0 + 6, y0), (x0 + 7 + sw * 0.6, y1 - 8), (x0 + 4 + sw * 0.6, y1 - 8)], (180, 104, 70)))
    # the window frame over it all: mullion, transom
    it.append(R(x0 + 30, y0, x0 + 34, y1, add(FRAME, WARM, 0.2)))
    it.append(R(x0, y0 + 11, x1, y0 + 14, add(FRAME, WARM, 0.2)))
    return it
