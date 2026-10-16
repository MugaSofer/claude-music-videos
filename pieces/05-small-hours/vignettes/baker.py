"""The baker: "The baker's hands are in the dough before the bread has heard it's day."

A narrow terraced bakery, its shop window the only warm thing on the street. Through the glass: shelves of
loaves, a brick oven with a live mouth, utensils on a rail, a flour sack slumped against the counter, and the
baker in profile, cap and apron, sleeves rolled, kneading. The shoulders drive each push; the dough stretches
under the heels of his hands and gathers back; flour lifts off the bench on every push. Steam leaves the
extractor vent above the door.

Painted in local coordinates (x from the vignette centre, y up from the pavement as negative numbers) and
placed at the end. The kneading cycle is 4/3 s and the steam 4 s, so the loop is seamless over 8 s (the film
runs this indoor keeper on a t % 8 loop in the background).
"""
import math

import numpy as np

# palette (STYLE.md) and derived paper tones
INK = (21, 26, 51)
PAPER = (239, 230, 210)
GOLD = (255, 201, 120)
WARMWIN = (255, 216, 154)

FACADE = (80, 50, 66)
FACADE_DK = (58, 36, 52)
FACADE_LT = (104, 68, 84)
FASCIA = (150, 52, 46)
WALL = (140, 88, 64)
POOL = [(168, 108, 74), (198, 136, 88), (226, 166, 106), (244, 190, 124)]
WOOD = (112, 68, 46)
WOOD_DK = (84, 50, 38)
WOOD_LT = (150, 98, 64)
FLOURY = (224, 206, 174)
CRUST = [(190, 116, 60), (164, 92, 48), (212, 146, 82), (176, 104, 56)]
BRICK = (118, 60, 50)
BRICK_DK = (92, 44, 40)

SHIRT = (62, 66, 110)
SHIRT_FAR = (44, 46, 82)
SKIN = (168, 106, 84)
SKIN_FAR = (128, 78, 66)
HAIR = (52, 34, 40)
APRON = (230, 218, 194)
TROUSERS = (48, 42, 60)
CAP = (236, 226, 204)
CUFF = (156, 162, 196)
DOUGH = (238, 220, 184)
DOUGH_SH = (210, 186, 148)

KNEAD_T = 4.0 / 3.0


# ---------------------------------------------------------------- small geometry helpers (local coords)
def _mix(a, b, t):
    t = min(max(t, 0.0), 1.0)
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _ellp(x, y, rx, ry, n=18, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        px, py = rx * math.cos(a), ry * math.sin(a)
        out.append((x + px * c - py * s, y + px * s + py * c))
    return out


def _clip(pts, x0, y0, x1, y1):
    """Clamp a convex shape into a window opening (close enough to a true clip for smooth shapes)."""
    return [(min(max(x, x0), x1), min(max(y, y0), y1)) for x, y in pts]


def _deckle(pts, seed, amp=0.9, step=26.0):
    """Cut-paper edge: subdivide long edges and nudge every vertex a little (fixed seed, so it never boils)."""
    g = np.random.default_rng(seed)
    out = []
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        k = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for j in range(k):
            t = j / k
            out.append((x0 + (x1 - x0) * t + g.uniform(-amp, amp), y0 + (y1 - y0) * t + g.uniform(-amp, amp)))
    return out


def _boil(pts, tl, seed, amp=0.7):
    """The figure's outline boils at 8 Hz, as if each drawing were cut again."""
    k = int(math.floor(tl * 8))
    out = []
    for i, (x, y) in enumerate(pts):
        h = (i * 7919 + k * 104729 + seed * 1299709) & 0xFFFFF
        a = (h % 1000) / 1000.0 * 2 * math.pi
        out.append((x + amp * math.cos(a), y + amp * math.sin(a)))
    return out


def _seg(p, q, w):
    (x0, y0), (x1, y1) = p, q
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = -uy * w / 2, ux * w / 2
    x0, y0, x1, y1 = x0 - ux * w * 0.4, y0 - uy * w * 0.4, x1 + ux * w * 0.4, y1 + uy * w * 0.4
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def _limb(a, b, wa, wb):
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    return [(x0 + nx * wa / 2, y0 + ny * wa / 2), (x1 + nx * wb / 2, y1 + ny * wb / 2),
            (x1 - nx * wb / 2, y1 - ny * wb / 2), (x0 - nx * wa / 2, y0 - ny * wa / 2)]


_FONT = {
    'B': [[(0, 0), (0, 3)], [(0, 3), (1.4, 3), (1.9, 2.6), (1.9, 1.9), (1.4, 1.5), (0, 1.5)],
          [(1.4, 1.5), (2, 1.1), (2, 0.4), (1.5, 0), (0, 0)]],
    'A': [[(0, 0), (1, 3), (2, 0)], [(0.45, 1.1), (1.55, 1.1)]],
    'K': [[(0, 0), (0, 3)], [(2, 3), (0, 1.3)], [(0.7, 1.8), (2, 0)]],
    'E': [[(2, 3), (0, 3), (0, 0), (2, 0)], [(0, 1.5), (1.5, 1.5)]],
    'R': [[(0, 0), (0, 3), (1.4, 3), (1.95, 2.6), (1.95, 1.9), (1.4, 1.5), (0, 1.5)], [(1.0, 1.5), (2, 0)]],
    'Y': [[(0, 3), (1, 1.6), (2, 3)], [(1, 1.6), (1, 0)]],
}


def _text(s, x, base, size, w, col):
    out = []
    sc = size / 3.0
    for ch in s:
        for line in _FONT.get(ch, []):
            pts = [(x + px * sc, base - py * sc) for px, py in line]
            for p, q in zip(pts, pts[1:]):
                out.append(('poly', _seg(p, q, w), col))
        x += size * 0.95
    return out


def _loaf(x, y, kind, col, g):
    """One loaf sitting on a shelf at y. Returns items."""
    out = []
    dark = _mix(col, (70, 36, 30), 0.35)
    if kind == 0:                                     # round cob with a cross cut
        out.append(('poly', _ellp(x, y - 11, 15, 12, 16), col))
        out.append(('poly', _seg((x - 7, y - 16), (x + 7, y - 8), 2), dark))
        out.append(('poly', _seg((x - 7, y - 8), (x + 7, y - 16), 2), dark))
    elif kind == 1:                                   # bloomer with diagonal slashes
        pts = [(x - 24, y), (x - 26, y - 8), (x - 18, y - 17), (x, y - 20), (x + 18, y - 17), (x + 26, y - 8), (x + 24, y)]
        out.append(('poly', pts, col))
        for k in range(-2, 3):
            out.append(('poly', _seg((x + k * 9 - 3, y - 15), (x + k * 9 + 3, y - 9), 2), dark))
    elif kind == 2:                                   # tin loaf, a domed top
        out.append(('poly', [(x - 16, y), (x - 16, y - 12), (x - 12, y - 20), (x, y - 23), (x + 12, y - 20),
                             (x + 16, y - 12), (x + 16, y)], col))
        out.append(('poly', _rect(x - 16, y - 10, x + 16, y - 7), _mix(col, PAPER, 0.25)))
    else:                                             # little rolls, a pair
        out.append(('poly', _ellp(x - 8, y - 7, 8, 7, 12), col))
        out.append(('poly', _ellp(x + 8, y - 7, 8, 7, 12), _mix(col, dark, 0.3)))
    return out


# ---------------------------------------------------------------- the static set
def _counter_and_sack():
    it = []
    # the workbench / counter: a wooden front, a floury top
    it.append(('poly', _deckle(_rect(-252, -150, 14, -76), 31), WOOD))
    for x in (-200, -140, -80, -20):
        it.append(('poly', _rect(x, -136, x + 3, -76), WOOD_DK))
    it.append(('poly', _deckle(_rect(-258, -156, 18, -144), 32), WOOD_LT))
    it.append(('poly', _rect(-258, -157, 18, -154), FLOURY))
    # flour sack slumped against the counter, tied at the neck
    sack = [(-280, -76), (-284, -110), (-280, -148), (-270, -168), (-262, -176), (-250, -178), (-236, -174),
            (-222, -166), (-212, -150), (-206, -120), (-204, -90), (-208, -76)]
    it.append(('poly', _deckle(sack, 33, 1.0, 12), (206, 190, 158)))
    it.append(('poly', [(-270, -168), (-262, -190), (-256, -198), (-248, -192), (-244, -178), (-252, -176)], (190, 172, 140)))
    it.append(('poly', _rect(-266, -182, -238, -176), (134, 96, 70)))            # the string
    it.append(('poly', [(-282, -118), (-205, -112), (-205, -100), (-283, -106)], (150, 60, 50)))   # printed band
    it.append(('poly', [(-262, -148), (-230, -146), (-232, -138), (-262, -140)], (176, 158, 128)))
    return it


def _set_local():
    it = []
    # --- the building: three storeys of plum-dark brick, chimney with pots
    it.append(('poly', _deckle([(-316, 0), (-316, -700), (316, -700), (316, 0)], 1), FACADE))
    it.append(('poly', _deckle(_rect(190, -772, 252, -700), 2), FACADE_DK))
    it.append(('poly', _rect(184, -778, 258, -768), FACADE_LT))
    it.append(('poly', _rect(198, -800, 214, -778), (120, 70, 60)))
    it.append(('poly', _rect(228, -794, 244, -778), (120, 70, 60)))
    it.append(('poly', _deckle(_rect(-326, -712, 326, -698), 3), FACADE_DK))                 # cornice
    for k in range(-15, 16):                                                              # dentils
        it.append(('poly', _rect(k * 21 - 4, -698, k * 21 + 4, -690), FACADE_DK))
    # upper windows: the baker's flat, dark; one with a lamp left on low
    for i, x in enumerate((-230, -40, 150)):
        lit = (i == 1)
        it.append(('poly', _rect(x - 6, -650, x + 86, -530), FACADE_DK))
        glass = (120, 78, 56) if lit else (34, 32, 60)
        it.append(('poly', _rect(x, -644, x + 80, -538), glass))
        if lit:
            it.append(('poly', [(x, -644), (x + 30, -644), (x + 22, -590), (x + 26, -538), (x, -538)], (166, 104, 70)))
        it.append(('poly', _rect(x, -594, x + 80, -588), FACADE_DK))
        it.append(('poly', _rect(x + 38, -644, x + 42, -538), FACADE_DK))
        it.append(('poly', _rect(x - 10, -532, x + 90, -524), FACADE_LT))                 # sill
    it.append(('poly', _rect(-316, -502, 316, -492), FACADE_DK))                          # string course
    # --- fascia with the name, and the hanging sign
    it.append(('poly', _deckle(_rect(-308, -488, 308, -424), 5), FASCIA))
    it.append(('poly', _rect(-300, -482, 300, -478), (196, 150, 96)))
    it.append(('poly', _rect(-300, -434, 300, -430), (196, 150, 96)))
    it += _text('BAKERY', -118, -441, 30, 5, (236, 214, 170))
    it.append(('poly', _rect(-316, -424, 316, -414), FACADE_DK))                          # ledge
    # bracket and swinging board (a loaf on a disc)
    it.append(('poly', _rect(290, -478, 352, -472), (40, 30, 40)))
    it.append(('poly', [(292, -472), (300, -472), (340, -446), (336, -442)], (40, 30, 40)))
    it.append(('poly', _rect(306, -472, 308, -456), (40, 30, 40)))
    it.append(('poly', _rect(334, -472, 336, -456), (40, 30, 40)))
    it.append(('poly', _ellp(321, -428, 28, 28, 22), (40, 30, 40)))
    it.append(('poly', _ellp(321, -428, 24, 24, 22), (196, 150, 96)))
    it += _loaf(321, -418, 1, (150, 52, 46), None)
    # --- the shop window: interior first (the facade pieces are cut over it)
    it.append(('poly', _rect(-290, -416, 126, -74), WALL))
    for r, c in zip((150, 118, 88, 58), POOL):                                            # the lamp's pool
        it.append(('poly', _clip(_ellp(-80, -300, r * 1.35, r, 28), -290, -416, 126, -74), c))
    # left shelves with loaves
    g = np.random.default_rng(7)
    for j, sy in enumerate((-356, -300, -244)):
        it.append(('poly', _rect(-284, sy, -180, sy + 7), WOOD_DK))
        it.append(('poly', [(-270, sy + 7), (-262, sy + 7), (-270, sy + 20)], WOOD_DK))
        it.append(('poly', [(-198, sy + 7), (-190, sy + 7), (-190, sy + 20)], WOOD_DK))
        x = -272
        lim = -214 if j == 0 else -178
        while True:
            kind = int(g.integers(0, 4))
            wdt = {0: 32, 1: 54, 2: 34, 3: 34}[kind]
            if x + wdt > lim:
                break
            it += _loaf(x + wdt / 2, sy, kind, CRUST[int(g.integers(0, 4))], g)
            x += wdt + 3
    # a basket of baguettes at the end of the top shelf
    for k in range(5):
        a = -0.3 + k * 0.15
        bx = -204 + k * 4
        it.append(('poly', _limb((bx, -366), (bx + 44 * math.sin(a), -366 - 44 * math.cos(a)), 7, 6), CRUST[k % 4]))
    it.append(('poly', [(-212, -378), (-180, -378), (-184, -356), (-208, -356)], (150, 110, 70)))
    it.append(('poly', _rect(-212, -371, -180, -368), (120, 84, 56)))
    # the clock says four
    it.append(('poly', _ellp(102, -362, 15, 15, 20), (60, 44, 46)))
    it.append(('poly', _ellp(102, -362, 12, 12, 20), (236, 222, 196)))
    it.append(('poly', _seg((102, -362), (102, -372), 2), (60, 44, 46)))
    it.append(('poly', _seg((102, -362), (108, -359), 2.5), (60, 44, 46)))
    # utensil rail with hanging tools
    it.append(('poly', _rect(-124, -398, -30, -394), (70, 50, 50)))
    tools = [(-112, 'ladle'), (-90, 'whisk'), (-66, 'sieve'), (-44, 'scraper')]
    tc = (86, 70, 76)
    for x, kind in tools:
        it.append(('poly', _rect(x - 1, -396, x + 1, -388), tc))
        if kind == 'ladle':
            it.append(('poly', _rect(x - 1.5, -390, x + 1.5, -352), tc))
            it.append(('poly', _ellp(x, -350, 8, 6, 12), tc))
        elif kind == 'whisk':
            it.append(('poly', _rect(x - 2, -390, x + 2, -372), tc))
            it.append(('poly', [(x - 2, -372), (x + 2, -372), (x + 8, -356), (x, -344), (x - 8, -356)], tc))
            it.append(('poly', [(x - 1, -368), (x + 1, -368), (x + 3, -354), (x, -348), (x - 3, -354)], WALL))
        elif kind == 'sieve':
            it.append(('poly', _rect(x - 1.5, -390, x + 1.5, -376), tc))
            it.append(('poly', _ellp(x, -362, 13, 13, 16), tc))
            it.append(('poly', _ellp(x, -362, 9, 9, 16), (150, 118, 96)))
        else:
            it.append(('poly', _rect(x - 1.5, -390, x + 1.5, -374), tc))
            it.append(('poly', [(x - 9, -374), (x + 9, -374), (x + 10, -356), (x - 10, -356)], tc))
    # pendant lamp
    it.append(('poly', _rect(-11, -416, -9, -372), (60, 44, 46)))
    it.append(('poly', [(-26, -358), (-18, -374), (-2, -374), (6, -358)], (60, 44, 46)))
    it.append(('poly', _ellp(-10, -356, 9, 5, 12), (255, 244, 214)))
    # the brick oven: a dome on a base, flue up through the ceiling
    it.append(('poly', _rect(62, -416, 78, -330), (58, 40, 44)))
    dome = [(8, -76), (8, -214), (16, -262), (40, -300), (70, -314), (100, -300), (122, -262), (126, -214), (126, -76)]
    it.append(('poly', _deckle(dome, 8, 1.0, 14), BRICK))
    for k, yy in enumerate(range(-100, -300, -22)):
        off = 12 if k % 2 else 0
        it.append(('poly', _rect(10, yy, 124, yy + 2), BRICK_DK))
        for xx in range(14 + off, 124, 24):
            it.append(('poly', _rect(xx, yy + 2, xx + 2, yy + 20), BRICK_DK))
    it.append(('poly', _rect(4, -216, 130, -206), (140, 82, 66)))                         # a lintel shelf
    mouth = [(36, -126), (36, -170), (44, -186), (66, -194), (88, -186), (96, -170), (96, -126)]
    it.append(('poly', mouth, (58, 26, 28)))
    inner = [(42, -128), (42, -168), (48, -180), (66, -187), (84, -180), (90, -168), (90, -128)]
    it.append(('poly', inner, (236, 122, 60)))
    it.append(('poly', _rect(30, -128, 102, -118), (140, 82, 66)))                        # hearth ledge
    # the peel, leaning on the oven
    it.append(('poly', _limb((120, -80), (104, -250), 5, 5), (150, 110, 74)))
    it.append(('poly', [(96, -252), (112, -250), (116, -290), (106, -300), (94, -290)], (176, 130, 86)))
    it += _counter_and_sack()
    # --- the facade cut over the interior: piers, transom, riser, door
    it.append(('poly', _deckle(_rect(-316, -416, -290, 0), 11), FACADE))
    it.append(('poly', _deckle(_rect(126, -416, 152, 0), 12), FACADE))
    it.append(('poly', _deckle(_rect(-316, -74, 152, 0), 13), FACADE_DK))                 # stall riser
    it.append(('poly', _rect(-300, -62, -30, -14), (48, 28, 42)))
    it.append(('poly', _rect(-10, -62, 140, -14), (48, 28, 42)))
    it.append(('poly', _deckle(_rect(-298, -80, 134, -70), 14), FACADE_LT))               # sill
    it.append(('poly', _rect(-290, -392, 126, -386), FACADE_DK))                          # transom bar
    it.append(('poly', _rect(-290, -416, 126, -408), FACADE_DK))                          # window head
    it.append(('poly', _rect(-294, -416, -286, -74), FACADE_DK))                          # glazing beads
    it.append(('poly', _rect(122, -416, 130, -74), FACADE_DK))
    it.append(('poly', _rect(1, -386, 7, -74), FACADE_DK))                                # mullion
    # door with a lit glass panel and fanlight
    it.append(('poly', _deckle(_rect(152, -416, 316, 0), 15), FACADE))
    it.append(('poly', _rect(162, -408, 284, 0), FACADE_DK))
    it.append(('poly', _rect(170, -400, 276, -372), (214, 158, 104)))                     # fanlight
    for x in (196, 222, 248):
        it.append(('poly', _rect(x, -400, x + 3, -372), FACADE_DK))
    it.append(('poly', [(199, -400), (222, -400), (228, -414), (205, -414)], (150, 110, 80)))   # hopper propped open
    it.append(('poly', [(199, -400), (222, -400), (222, -397), (199, -397)], (40, 30, 40)))
    it.append(('poly', _rect(172, -364, 274, 0), (74, 44, 50)))                           # the door
    it.append(('poly', _rect(184, -350, 262, -176), (206, 150, 98)))                      # glass, the interior beyond
    it.append(('poly', _clip(_ellp(223, -262, 50, 70, 20), 184, -350, 262, -176), (224, 168, 110)))
    it.append(('poly', _rect(221, -350, 225, -176), (74, 44, 50)))
    it.append(('poly', _rect(184, -266, 262, -262), (74, 44, 50)))
    it.append(('poly', _rect(186, -150, 260, -40), (64, 38, 46)))                          # lower panel
    it.append(('poly', _rect(196, -140, 250, -50), (74, 44, 50)))
    it.append(('poly', _rect(194, -236, 196, -210), (40, 30, 40)))                        # CLOSED card string
    it.append(('poly', [(200, -232), (242, -232), (252, -212), (210, -212)], (236, 222, 196)))
    it.append(('poly', _rect(206, -224, 240, -221), (150, 52, 46)))
    it.append(('poly', _ellp(182, -170, 4, 4, 8), (196, 150, 96)))                        # knob
    it.append(('poly', _rect(162, -8, 284, 0), (100, 66, 78)))                            # step
    return it


def _place(items, cx, ground):
    out = []
    for kind, pts, col in items:
        out.append((kind, [(cx + x, ground + y) for x, y in pts], col))
    return out


def set_items(cx, ground):
    return _place(_set_local(), cx, ground)


# ---------------------------------------------------------------- the baker, kneading
def _push(tl):
    """0 = gathered back, 1 = fully leaned into the push. Fast, heavy push; slower fold back."""
    p = (tl % KNEAD_T) / KNEAD_T
    if p < 0.42:
        u = p / 0.42
        return u * u * (3 - 2 * u), p
    u = (p - 0.42) / 0.58
    return 1 - u * u * (3 - 2 * u), p


def _ik(S, T, L1, L2):
    dx, dy = T[0] - S[0], T[1] - S[1]
    d = math.hypot(dx, dy)
    d = min(max(d, abs(L1 - L2) + 1), L1 + L2 - 0.5)
    th = math.atan2(dy, dx)
    ca = (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)
    al = math.acos(min(max(ca, -1), 1))
    E = (S[0] + L1 * math.cos(th + al), S[1] + L1 * math.sin(th + al))
    ang2 = math.atan2(T[1] - E[1], T[0] - E[0])
    H = (E[0] + L2 * math.cos(ang2), E[1] + L2 * math.sin(ang2))
    return E, H


def _arm(S, T, shirt, skin, s):
    it = []
    E, Hn = _ik(S, T, 64, 60)
    it.append(('poly', _ellp(S[0], S[1], 15, 15, 12), shirt))                             # shoulder cap
    it.append(('poly', _limb(S, E, 27, 21), shirt))
    fa = math.atan2(Hn[1] - E[1], Hn[0] - E[0])
    # forearm: thick at the elbow, taper to the wrist
    it.append(('poly', _limb(E, Hn, 19, 12), skin))
    it.append(('poly', _ellp(E[0], E[1], 10, 10, 10), skin))
    # rolled sleeve: a fat cuff just above the elbow
    cu = (S[0] + (E[0] - S[0]) * 0.78, S[1] + (E[1] - S[1]) * 0.78)
    cv = (S[0] + (E[0] - S[0]) * 0.98, S[1] + (E[1] - S[1]) * 0.98)
    it.append(('poly', _limb(cu, cv, 27, 25), CUFF if shirt == SHIRT else _mix(CUFF, SHIRT_FAR, 0.5)))
    # hand: heel on the dough, fingers curled over its far side
    ha = fa * 0.35 + 0.18
    c, sn = math.cos(ha), math.sin(ha)
    hand = [(-2, -7), (8, -9), (20, -8), (28, -4), (31, 2), (27, 8), (14, 9), (2, 8), (-3, 3)]
    hp = ('poly', [(Hn[0] + x * c - y * sn, Hn[1] + x * sn + y * c) for x, y in hand], skin)
    it.append(hp)
    return it, Hn, hp


def _baker(tl):
    s, p = _push(tl)
    breathe = math.sin(tl * 2 * math.pi / 4.0) * 1.2
    hip = (-162 + 4 * s, -176 + 5 * s)
    a = 0.16 + 0.26 * s                                                                  # the lean
    up = (math.sin(a), -math.cos(a))
    fw = (math.cos(a), math.sin(a))

    def T(u, w):
        return (hip[0] + u * fw[0] + w * up[0], hip[1] + u * fw[1] + w * up[1])

    # hand targets on the dough
    tgt = (-72 + 44 * s, -176 + 5 * s)
    far_tgt = (tgt[0] + 10, tgt[1] - 3)
    it = []
    # far arm (behind the body)
    far, _, far_hand = _arm(T(10, 94 + breathe), far_tgt, SHIRT_FAR, SKIN_FAR, s)
    it += far
    # seat and trousers, down behind the counter (v4: the torso used to stop above the bench, with wall under it)
    it.append(('poly', [T(-26, -6), T(30, -6), (hip[0] + 28, -138), (hip[0] - 26, -138), (hip[0] - 31, hip[1] + 8)],
               TROUSERS))
    # torso: back contour, chest, belly
    torso = [(-26, -8), (-27, 38), (-25, 72), (-18, 96), (-6, 108), (8, 108), (22, 94), (27, 66), (30, 36),
             (30, -8)]
    it.append(('poly', [T(u, w + (breathe if w > 60 else 0)) for u, w in torso], SHIRT))
    # apron: bib and skirt, with a neck strap and a bow at the back
    apron = [(4, 90), (20, 90), (28, 64), (31, 36), (33, 0), (31, -30), (0, -30), (-4, 20), (2, 60)]
    it.append(('poly', [T(u, w) for u, w in apron], APRON))
    it.append(('poly', [T(u, w) for u, w in [(4, 90), (8, 90), (2, 108), (-2, 106)]], APRON))
    it.append(('poly', [T(u, w) for u, w in [(-27, 30), (4, 32), (4, 26), (-27, 24)]], APRON))
    it.append(('poly', [T(u, w) for u, w in [(-26, 28), (-38, 36), (-40, 28), (-34, 22)]], APRON))
    it.append(('poly', [T(u, w) for u, w in [(-26, 26), (-36, 14), (-31, 10), (-24, 22)]], APRON))
    it.append(('poly', [T(u, w) for u, w in [(-12, 60), (-4, 58), (-6, 70)]], _mix(SHIRT, INK, 0.3)))  # a fold
    # neck and head, the head tipping down to watch the dough
    nb = T(2, 104)
    h = 0.30 + a * 0.5 + 0.06 * s
    hu, hf = (math.sin(h), -math.cos(h)), (math.cos(h), math.sin(h))
    hoff = T(4, 112)

    def Hh(x, y):
        return (hoff[0] + x * hf[0] + y * hu[0], hoff[1] + x * hf[1] + y * hu[1])

    it.append(('poly', [T(-8, 98), T(12, 98), Hh(8, 4), Hh(-10, 6)], SKIN))
    head = [(-17, 8), (-25, 24), (-26, 42), (-19, 57), (-3, 64), (12, 60), (20, 48), (22, 40), (20, 35), (23, 32),
            (33, 22), (32, 19), (24, 18), (25, 14), (23, 12), (24, 9), (21, 2), (12, -2), (2, -2)]
    it.append(('poly', [Hh(x, y) for x, y in head], SKIN))
    it.append(('poly', [Hh(x, y) for x, y in [(12, 18), (26, 19), (24, 15), (14, 15)]], HAIR))          # moustache
    it.append(('poly', [Hh(x, y) for x, y in [(10, 38), (18, 36), (18, 34), (11, 35)]], _mix(SKIN, INK, 0.6)))  # eye
    it.append(('poly', [Hh(x, y) for x, y in [(8, 44), (20, 43), (20, 41), (9, 42)]], HAIR))            # brow
    it.append(('poly', [Hh(x, y) for x, y in [(-4, 36), (-1, 32), (-2, 25), (-6, 22), (-10, 26), (-10, 33)]],
               _mix(SKIN, INK, 0.18)))                                                                # ear
    it.append(('poly', [Hh(x, y) for x, y in [(-27, 44), (-26, 24), (-18, 10), (-13, 14), (-15, 30), (-11, 44)]],
               HAIR))
    cap = [(-28, 41), (-27, 60), (-20, 72), (-4, 78), (14, 74), (24, 62), (21, 47), (4, 46), (-12, 45)]   # v4: well under the band
    it.append(('poly', [Hh(x, y) for x, y in cap], CAP))
    it.append(('poly', [Hh(x, y) for x, y in [(-28, 47), (21, 54), (21, 50), (-28, 43)]], _mix(CAP, WOOD, 0.25)))
    # near arm
    near, hand, near_hand = _arm(T(12, 92 + breathe), tgt, SHIRT, SKIN, s)
    it += near
    it = [(k, _boil(pts, tl, i + 3), col) for i, (k, pts, col) in enumerate(it)]
    hands = [(k, _boil(pts, tl, 90 + i), col) for i, (k, pts, col) in enumerate((far_hand, near_hand))]
    return it, hands, s, p, hand


def _dough(s, hand_x):
    w = 78 + 32 * s
    hgt = 34 - 11 * s
    x0 = -96 + 4 * s
    top = []
    n = 14
    for k in range(n + 1):
        u = k / n
        x = x0 + w * u
        bump = math.sin(math.pi * u) ** 0.7
        dip = 7 * math.exp(-((x - hand_x) / 16) ** 2) * (0.4 + 0.6 * s)
        top.append((x, -156 - hgt * bump + dip))
    base = [(x0 + w + 3, -156), (x0 - 3, -156)]
    pts = top + base
    sh = [(x, y + 6) for x, y in top[3:-3]] + [(x0 + w * 0.8, -156), (x0 + w * 0.2, -156)]
    return [('poly', _ellp(x0 + w * 0.45, -156, w * 0.6, 3, 16), FLOURY), ('poly', pts, DOUGH), ('poly', sh, DOUGH_SH),
            ]


def _flour(tl, hx):
    """A puff of flour off the bench at each push's impact; the puffs thin into the lamp light."""
    it = []
    k = int(math.floor(tl / KNEAD_T))
    age = tl - k * KNEAD_T - 0.30 * KNEAD_T
    if age < 0:
        k -= 1
        age += KNEAD_T
    if age > 1.1:
        return it
    g = np.random.default_rng(1000 + (k % 6))
    for i in range(9):
        vx, vy = g.uniform(-50, 60), g.uniform(40, 120)
        r0 = g.uniform(3.5, 7)
        x = hx + g.uniform(-24, 34) + vx * age
        y = -160 - vy * age + 40 * age * age
        r = r0 + 14 * age
        bg = WALL
        for rr, c in zip((150, 118, 88, 58), POOL):                    # the wall colour behind this puff
            if ((x + 80) / (rr * 1.35)) ** 2 + ((y + 300) / rr) ** 2 < 1:
                bg = c
        it.append(('poly', _ellp(x, y, r, r * 0.8, 10), _mix((246, 238, 220), bg, (age / 1.1) ** 0.8)))
    return it


def _oven_fire(tl):
    f = 0.55 + 0.22 * math.sin(tl * 7.3) + 0.14 * math.sin(tl * 13.1 + 1.0) + 0.09 * math.sin(tl * 3.1 + 2.0)
    it = []
    # the glow the oven casts on the brick around its mouth
    it.append(('poly', _ellp(66, -152, 44 + 6 * f, 36 + 5 * f, 20), _mix(BRICK, (214, 112, 70), 0.35 + 0.3 * f)))
    it.append(('poly', [(36, -126), (36, -170), (44, -186), (66, -194), (88, -186), (96, -170), (96, -126)],
               (58, 26, 28)))
    inner = [(42, -128), (42, -168), (48, -180), (66, -187), (84, -180), (90, -168), (90, -128)]
    it.append(('poly', inner, _mix((196, 76, 44), (255, 170, 84), f)))
    # flame tongues
    for i, (fx, hh) in enumerate(((52, 30), (64, 44), (76, 36), (84, 24))):
        sway = 3 * math.sin(tl * (9 + i * 2.3) + i)
        ht = hh * (0.75 + 0.35 * math.sin(tl * (11 + i * 3.7) + i * 2) ** 2)
        it.append(('poly', [(fx - 7, -130), (fx + 7, -130), (fx + 3 + sway, -130 - ht * 0.6), (fx + sway * 1.6, -130 - ht),
                            (fx - 4 + sway, -130 - ht * 0.55)], _mix((255, 176, 86), (255, 236, 176), 0.5 + 0.5 * f)))
    # loaves baking in the mouth, dark against the fire
    it.append(('poly', [(46, -128), (48, -138), (58, -142), (68, -138), (70, -128)], (120, 60, 40)))
    it.append(('poly', [(68, -128), (70, -136), (78, -139), (86, -135), (88, -128)], (104, 52, 36)))
    it.append(('poly', _rect(30, -128, 102, -118), (140, 82, 66)))
    return it


def _steam(tl):
    it = []
    """Bread-steam curling out of the propped fanlight, up past the sign. Opaque paper curls that fade by
    taking on the colour of whatever they drift over (translucent shapes would punch holes in the layer)."""
    for j, (bx, L, col) in enumerate(((206, 210, (196, 178, 190)), (216, 170, (226, 212, 206)))):
        left, right = [], []
        n = 22
        pts = []
        for k in range(n + 1):
            u = k / n
            x = bx + 46 * u + (4 + 24 * u) * math.sin(u * 5.5 - tl * math.pi + j * 2.1)
            y = -412 - L * u
            pts.append((x, y))
        for k, (x, y) in enumerate(pts):
            u = k / n
            q = pts[min(k + 1, n)] if k < n else pts[k]
            pp = pts[k - 1] if k > 0 else pts[k]
            dx, dy = q[0] - pp[0], q[1] - pp[1]
            d = math.hypot(dx, dy) or 1
            w = (3 + 9 * math.sin(math.pi * min(u * 1.6, 1) * 0.5)) * (1 - u) ** 0.6   # swells, then thins away
            left.append((x - dy / d * w, y + dx / d * w))
            right.append((x + dy / d * w, y - dx / d * w))
        it.append(('poly', left + right[::-1], col))
        # a few crumbs of steam breaking off the top
        for i in range(3):
            age = ((tl / 2.0) + i / 3.0 + j * 0.17) % 1.0
            r = 5 * (1 - age) + 1
            x = pts[-1][0] + 10 * math.sin(i * 2 + age * 3) + 20 * age
            y = pts[-1][1] - 50 * age + 10
            it.append(('poly', _ellp(x, y, r, r * 0.8, 10), col))
    return it


def action_items(tl, cx, ground):
    it = []
    it += _oven_fire(tl)
    figure, hands, s, p, hand = _baker(tl)
    it += figure
    it += _counter_and_sack()
    it += _dough(s, hand[0] + 12)
    it += hands
    it += _flour(tl, hand[0])
    it.append(('poly', _rect(1, -386, 7, -74), FACADE_DK))                                 # mullion stays in front
    it += _steam(tl)
    return _place(it, cx, ground)
