"""Dad: "A new dad in a kitchen learns the weight of something new".

A terraced house at 4am, seen from the pavement. Upstairs is dark (someone is finally asleep);
downstairs the kitchen window glows. Inside, a new dad in an old jumper, tea towel over his
shoulder, sways and jiggles a swaddled baby against his chest, chin resting on the little hat.
The kettle has just boiled, the clock says four, the "congratulations" cards are still up.
He glances up at the clock, then back down at the baby, whose tiny hand reaches for his chin.
"""
import math

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

WALL_IN = (244, 194, 126)        # kitchen back wall, lit
BRICK = (92, 54, 62)
MORTAR = (72, 44, 58)
FRAME = (196, 186, 178)
SKIN = (214, 152, 120)
SKIN_SH = (186, 124, 100)
JUMPER = (84, 90, 142)
JUMPER_LT = (102, 108, 160)
JUMPER_DK = (64, 68, 116)
SWADDLE = (234, 224, 206)

# window geometry, relative to cx
WX0, WX1, WY0, WY1 = -200, 200, 392, 716         # outer frame
GX0, GX1, GY0, GY1 = -186, 186, 406, 702         # glass
TRANSOM = (460, 470)


def _p(pts, col):
    return ('poly', [(float(x), float(y)) for x, y in pts], col)


def _e(x, y, rx, ry, col):
    return ('ell', (float(x - rx), float(y - ry), float(x + rx), float(y + ry)), col)


def _r(x0, y0, x1, y1, col):
    return _p([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(x * (1 - t) + y * t)) for x, y in zip(a[:3], b[:3]))


def _rot(pts, ang, px=0.0, py=0.0):
    c, s = math.cos(ang), math.sin(ang)
    return [(px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c) for x, y in pts]


def _bar(x0, y0, x1, y1, w0, w1=None):
    w1 = w0 if w1 is None else w1
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / n, dx / n
    return [(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2),
            (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2)]


def _oval(x, y, rx, ry, ang=0.0, n=18):
    return _rot([(x + rx * math.cos(2 * math.pi * k / n), y + ry * math.sin(2 * math.pi * k / n)) for k in range(n)],
                ang, x, y)


def _hash(k):
    v = math.sin(k * 12.9898 + 78.233) * 43758.5453
    return v - math.floor(v)


def _smooth(a, b, t):
    u = max(0.0, min(1.0, (t - a) / (b - a)))
    return u * u * (3 - 2 * u)


# ----------------------------------------------------------------------------------- outside

def _glow(cx, x, y):
    """How much warm window light falls on the brick at (x, y)."""
    dx = max(0.0, abs(x - cx) - 170) / 150
    dy = max(0.0, 404 - y) / 110 if y < 404 else max(0.0, y - 716) / 120
    return math.exp(-(dx * dx + dy * dy)) * 0.55


def _house(cx, ground):
    it = []
    L, R = cx - 340, cx + 340
    # neighbours' walls (slightly different bricks) and our wall
    it.append(_r(cx - 500, 190, L, ground, (78, 50, 64)))
    it.append(_r(R, 190, cx + 500, ground, (74, 50, 70)))
    it.append(_r(L, 190, R, ground, MORTAR))
    # warm light spill on our wall, stepped (paper layers)
    for k, t in enumerate((0.12, 0.22, 0.34)):
        g = 60 - k * 20
        it.append(_r(cx + WX0 - g * 1.4, WY0 - g, cx + WX1 + g * 1.4, WY1 + g * 1.3, _mix(MORTAR, (200, 120, 90), t)))
    # bricks: a staggered scatter, lit by the window
    for row in range(0, 44):
        y = 196 + row * 16
        if y > ground - 16:
            break
        off = 0 if row % 2 == 0 else 23
        for col in range(-1, 16):
            x = L + off + col * 46
            h = _hash(row * 31 + col * 7 + 3)
            if h > 0.5 or x + 42 > R or x < L:
                continue
            if cx + WX0 - 8 < x + 42 and x < cx + WX1 + 8 and WY0 - 8 < y + 13 and y < WY1 + 26:
                continue                                                  # no bricks behind the window
            if cx - 110 < x + 42 and x < cx + 110 and 238 < y + 13 and y < 362:
                continue                                                  # nor behind the upstairs window
            base = _mix(BRICK, (112, 60, 60), _hash(row * 5 + col * 11))
            it.append(_r(x, y, x + 42, y + 13, _mix(base, (220, 132, 92), _glow(cx, x + 21, y + 6))))
    # neighbour bricks, a few
    for k in range(18):
        side = -1 if k % 2 == 0 else 1
        x = cx + side * (368 + _hash(k * 3) * 84) - 21
        y = 200 + int(_hash(k * 7 + 1) * 40) * 16
        it.append(_r(x, y, x + 42, y + 13, (88, 56, 70) if side < 0 else (84, 56, 76)))
    # gutter, roof and chimney (for wide shots)
    it.append(_p([(cx - 500, 190), (cx + 500, 190), (cx + 460, 120), (cx - 460, 120)], NAVY))
    for x in range(cx - 468, cx + 468, 26):
        it.append(_r(x, 122 + (x // 26 % 2) * 2, x + 2, 188, (36, 40, 84)))
    it.append(_r(cx - 500, 186, cx + 500, 198, (40, 44, 80)))
    for px in (L, R):
        it.append(_r(px - 30, 70, px + 30, 124, (70, 46, 58)))
        it.append(_r(px - 36, 64, px + 36, 72, (86, 58, 70)))
        it.append(_r(px - 18, 50, px - 6, 64, (150, 80, 56)))
        it.append(_r(px + 6, 46, px + 18, 64, (150, 80, 56)))
    # upstairs: dark, curtains drawn, someone asleep
    it.append(_r(cx - 116, 238, cx + 116, 250, (138, 132, 140)))         # lintel
    it.append(_r(cx - 104, 250, cx + 104, 362, (150, 144, 150)))
    it.append(_r(cx - 94, 260, cx + 94, 354, (36, 38, 76)))
    it.append(_p([(cx - 94, 260), (cx - 20, 260), (cx - 34, 354), (cx - 94, 354)], (52, 48, 88)))
    it.append(_p([(cx + 94, 260), (cx + 20, 260), (cx + 30, 354), (cx + 94, 354)], (52, 48, 88)))
    it.append(_r(cx - 104, 304, cx + 104, 310, (150, 144, 150)))
    it.append(_r(cx - 112, 362, cx + 112, 372, (124, 120, 134)))         # its sill
    # our front door on the left (navy, a dim fanlight) and a lintel over the kitchen window
    it.append(_r(cx - 318, 548, cx - 226, ground, (132, 128, 140)))
    it.append(_r(cx - 310, 556, cx - 234, ground, NAVY))
    it.append(_p([(cx - 306, 560), (cx - 238, 560), (cx - 238, 590), (cx - 306, 590)], (96, 80, 90)))
    for k in range(4):
        x = cx - 304 + k * 17
        it.append(_r(x + 14, 560, x + 16, 590, NAVY))
    for yy in (600, 700):
        it.append(_r(cx - 302, yy, cx - 242, yy + 80, (48, 54, 104)))
    it.append(_r(cx - 286, 720, cx - 258, 728, (180, 150, 100)))           # letterbox
    it.append(_e(cx - 244, 660, 4, 4, (180, 150, 100)))                    # knob
    it.append(_r(cx + WX0 - 18, WY0 - 18, cx + WX1 + 18, WY0 - 4, (140, 132, 142)))
    # drainpipe at the party wall
    it.append(_r(cx + 296, 192, cx + 308, ground, (44, 48, 88)))
    for yy in range(260, ground, 150):
        it.append(_r(cx + 292, yy, cx + 312, yy + 6, (56, 60, 100)))
    it.append(_p([(cx + 288, 196), (cx + 316, 196), (cx + 310, 212), (cx + 294, 212)], (44, 48, 88)))
    # the neighbours' dark windows at the frame edges
    it.append(_r(cx - 490, 400, cx - 400, 700, (132, 126, 136)))
    it.append(_r(cx - 482, 410, cx - 410, 690, (34, 36, 72)))
    it.append(_r(cx + 400, 400, cx + 490, 700, (132, 126, 136)))
    it.append(_r(cx + 410, 410, cx + 482, 690, (34, 36, 72)))
    it.append(_p([(cx + 410, 410), (cx + 450, 410), (cx + 436, 690), (cx + 410, 690)], (46, 44, 84)))
    return it


def _interior(cx):
    it = []
    x0, x1, y0, y1 = cx + GX0, cx + GX1, GY0, GY1
    it.append(_r(x0, y0, x1, y1, WALL_IN))
    # pendant glow on the wall, above the dad
    for rx, ry, t in ((70, 46, 0.22), (44, 30, 0.45)):
        it.append(_p(_oval(cx - 40, 446, rx, ry, 0, 28), _mix(WALL_IN, (255, 232, 180), t)))
    # tiled splashback strip
    it.append(_r(x0, 574, x1, 606, (238, 210, 170)))
    for x in range(int(x0) + 22, int(x1), 24):
        it.append(_r(x, 574, x + 1.5, 606, (218, 180, 136)))
    it.append(_r(x0, 589, x1, 590.5, (218, 180, 136)))
    # wall cupboards (left) with a shadow line under them
    it.append(_r(x0, 508, cx - 84, 514, (226, 170, 108)))
    it.append(_r(x0, y0, cx - 86, 508, (206, 140, 98)))
    it.append(_r(cx - 137, y0, cx - 134, 508, (164, 104, 74)))
    it.append(_r(x0, 500, cx - 86, 508, (186, 122, 86)))
    for hx in (cx - 144, cx - 128):
        it.append(_r(hx, 478, hx + 3, 494, (132, 86, 70)))
    # congratulations cards strung under the cupboards
    pts = [(x0 + 4 + k * 6, 526 + 5 * math.sin(math.pi * k / 14)) for k in range(15)]
    it.append(_p(pts + [(x, y + 1.2) for x, y in reversed(pts)], (150, 100, 80)))
    for k, col in enumerate((ROSE, DBLUE, PAPER, (236, 188, 120), DBLUE)):
        x, y = pts[1 + k * 3]
        it.append(_p(_rot([(x - 6, y), (x + 6, y), (x + 6, y + 15), (x - 6, y + 15)], 0.08 * (k % 2 * 2 - 1), x, y), col))
        it.append(_r(x - 3, y + 5, x + 3, y + 7, (200, 120, 110)))
    # back worktop and lower cupboards
    it.append(_r(x0, 606, x1, 616, (150, 96, 78)))
    it.append(_r(x0, 606, x1, 609, (184, 128, 96)))
    it.append(_r(x0, 616, x1, y1, (208, 146, 102)))
    for x in range(int(x0) + 70, int(x1), 74):
        it.append(_r(x, 616, x + 3, y1, (170, 110, 80)))
        it.append(_r(x - 14, 628, x - 4, 632, (132, 86, 70)))
    # mug, baby bottle, kettle
    it.append(_r(cx + 142, 580, cx + 154, 606, (226, 218, 204)))          # bottle
    it.append(_p([(cx + 144, 580), (cx + 152, 580), (cx + 150, 570), (cx + 146, 570)], ROSE))
    it.append(_r(cx + 142, 592, cx + 154, 594, (200, 190, 180)))
    it.append(_r(cx + 160, 588, cx + 178, 606, DBLUE))                     # mug
    it.append(_p(_bar(cx + 178, 592, cx + 183, 600, 3), DBLUE))
    kx = cx + 100
    it.append(_p([(kx - 22, 606), (kx + 22, 606), (kx + 17, 574), (kx - 16, 574)], RED))
    it.append(_p([(kx - 20, 606), (kx - 10, 606), (kx - 7, 574), (kx - 14, 574)], (214, 96, 70)))   # highlight
    it.append(_r(kx - 17, 570, kx + 17, 575, (150, 44, 40)))
    it.append(_r(kx - 4, 564, kx + 4, 570, (150, 44, 40)))
    it.append(_p([(kx - 18, 598), (kx - 30, 580), (kx - 34, 576), (kx - 28, 576), (kx - 16, 588)], RED))  # spout
    it.append(_p([(kx + 16, 578), (kx + 30, 580), (kx + 30, 600), (kx + 20, 602), (kx + 22, 596), (kx + 25, 596),
                  (kx + 25, 584), (kx + 17, 584)], (150, 44, 40)))                                       # handle
    it.append(_r(kx - 22, 603, kx + 22, 607, (70, 60, 80)))
    it.append(_e(kx + 12, 600, 1.8, 1.8, DBLUE))                                                       # on-light
    # the clock
    it += _clock_face(cx)
    # pendant lamp: cord, shade, bulb
    it.append(_r(cx - 41, y0, cx - 39, 434, (120, 80, 70)))
    it.append(_p([(cx - 52, 448), (cx - 28, 448), (cx - 34, 434), (cx - 46, 434)], (60, 90, 110)))
    it.append(_e(cx - 40, 450, 6, 4, (255, 236, 196)))
    return it


CLK = (128, 520, 24)


def _clock_face(cx):
    x, y, r = cx + CLK[0], CLK[1], CLK[2]
    it = [_e(x, y + 2, r + 1, r + 1, (214, 160, 104)), _e(x, y, r, r, NAVY), _e(x, y, r - 4, r - 4, PAPER)]
    for k in range(12):
        a = k * math.pi / 6
        l = 4 if k % 3 == 0 else 2
        it.append(_p(_bar(x + math.sin(a) * (r - 6), y - math.cos(a) * (r - 6),
                          x + math.sin(a) * (r - 6 - l), y - math.cos(a) * (r - 6 - l), 1.6), NAVY))
    return it


def _clock_hands(cx, sec):
    x, y = cx + CLK[0], CLK[1]
    mins = 2 + sec / 60.0
    ah = (4 + mins / 60.0) * math.pi / 6
    am = mins * math.pi / 30
    asec = sec * math.pi / 30
    it = [_p(_bar(x, y, x + math.sin(ah) * 10, y - math.cos(ah) * 10, 3.2, 2.2), INK),
          _p(_bar(x, y, x + math.sin(am) * 15, y - math.cos(am) * 15, 2.4, 1.6), INK),
          _p(_bar(x - math.sin(asec) * 4, y + math.cos(asec) * 4, x + math.sin(asec) * 17, y - math.cos(asec) * 17, 1.0),
             RED),
          _e(x, y, 2, 2, RED)]
    return it


def _foreground(cx):
    """Things in front of the dad: sink edge and tap, the window frame, the outside sill and plant."""
    it = []
    # the near worktop edge, a tap, washing-up liquid
    it.append(_r(cx + GX0, 686, cx + GX1, GY1, (136, 88, 74)))
    it.append(_r(cx + GX0, 686, cx + GX1, 689, (176, 120, 92)))
    it.append(_p([(cx - 176, 686), (cx - 162, 686), (cx - 163, 654), (cx - 166, 648), (cx - 172, 648),
                  (cx - 175, 654)], (120, 170, 150)))
    it.append(_r(cx - 171, 640, cx - 167, 648, (230, 220, 200)))
    arc = [(cx - 140 + 16 * (1 - math.cos(math.pi * k / 8)), 640 - 20 * math.sin(math.pi * k / 8)) for k in range(9)]
    it.append(_r(cx - 144, 640, cx - 136, 686, (150, 150, 172)))
    for (a, b), (c, d) in zip(arc[:-1], arc[1:]):
        it.append(_p(_bar(a, b, c, d, 7), (150, 150, 172)))
    it.append(_r(cx - 111, 640, cx - 105, 650, (150, 150, 172)))
    it.append(_r(cx - 143, 646, cx - 141, 684, (200, 196, 210)))
    it.append(_r(cx - 150, 680, cx - 130, 686, (130, 130, 150)))
    # frame: outer ring, transom, top mullion, lit inner edges
    it.append(_r(cx + WX0, WY0, cx + WX1, GY0, FRAME))
    it.append(_r(cx + WX0, GY1, cx + WX1, WY1, FRAME))
    it.append(_r(cx + WX0, WY0, cx + GX0, WY1, FRAME))
    it.append(_r(cx + GX1, WY0, cx + WX1, WY1, FRAME))
    it.append(_r(cx + GX0, TRANSOM[0], cx + GX1, TRANSOM[1], FRAME))
    it.append(_r(cx - 5, GY0, cx + 5, TRANSOM[0], FRAME))
    it.append(_r(cx + GX0, TRANSOM[1], cx + GX1, TRANSOM[1] + 2, (226, 212, 190)))
    it.append(_r(cx + GX0 - 2, GY0, cx + GX0, GY1, (226, 212, 190)))
    it.append(_r(cx + WX0 - 4, WY0 - 4, cx + WX1 + 4, WY0, (150, 142, 150)))
    # outside sill, lit on top, a shadow under it
    it.append(_r(cx + WX0 - 20, WY1 + 14, cx + WX1 + 20, WY1 + 22, (58, 36, 50)))
    it.append(_p([(cx + WX0 - 22, WY1), (cx + WX1 + 22, WY1), (cx + WX1 + 20, WY1 + 16), (cx + WX0 - 20, WY1 + 16)],
                 (134, 128, 146)))
    it.append(_r(cx + WX0 - 22, WY1, cx + WX1 + 22, WY1 + 4, (214, 180, 146)))
    # a geranium on the sill
    px = cx + 140
    for k in range(9):
        a = -2.6 + k * 0.33
        lx, ly = px + math.cos(a) * 26, WY1 - 34 + math.sin(a) * 18
        it.append(_p(_oval(lx, ly, 12, 8, a), _mix((58, 84, 80), (96, 116, 92), _hash(k))))
    for k, (fx, fy) in enumerate(((-12, -66), (8, -72), (22, -58))):
        it.append(_p(_bar(px + fx * 0.3, WY1 - 34, px + fx, WY1 + fy + 6, 2), (70, 94, 84)))
        for j in range(5):
            a = j * 2 * math.pi / 5 + k
            it.append(_e(px + fx + math.cos(a) * 5, WY1 + fy + math.sin(a) * 5, 5, 5, (196, 62, 52)))
        it.append(_e(px + fx, WY1 + fy, 3, 3, (226, 96, 70)))
    it.append(_p([(px - 22, WY1 - 26), (px + 22, WY1 - 26), (px + 17, WY1), (px - 17, WY1)], (156, 82, 54)))
    it.append(_r(px - 24, WY1 - 30, px + 24, WY1 - 22, (176, 96, 62)))
    it.append(_p([(px - 22, WY1 - 22), (px - 12, WY1 - 22), (px - 9, WY1), (px - 17, WY1)], (188, 110, 72)))
    # a little succulent in a tin, left
    sx = cx - 150
    it.append(_r(sx - 12, WY1 - 18, sx + 12, WY1, (120, 126, 150)))
    for k in range(5):
        a = -math.pi / 2 + (k - 2) * 0.5
        it.append(_p(_oval(sx + math.cos(a) * 8, WY1 - 20 + math.sin(a) * 8, 8, 3.5, a), (84, 112, 100)))
    return it


def set_items(cx, ground):
    return _house(cx, ground) + _interior(cx) + _foreground(cx)


# ----------------------------------------------------------------------------------- the dad

def _dad(cx, tl):
    it = []
    T = 2 * math.pi
    sway = math.sin(T * tl / 2.8)
    X0 = cx - 44 + 9 * sway
    Y0 = 606 - 1.5 - 2.0 * math.sin(T * tl / 0.7) + 0.8 * math.sin(T * tl / 4.1)   # little knee-bounces + breath
    lean = 0.035 * math.sin(T * tl / 2.8 + 0.6)
    glance = _smooth(3.4, 3.9, tl) * (1 - _smooth(4.9, 5.5, tl))
    hr = (0.36 + 0.05 * math.sin(T * tl / 2.8 + 1.2)) * (1 - glance) + (-0.16) * glance

    def B(pts):
        return [(X0 + x, Y0 + y) for x, y in _rot(pts, lean, 0, 220)]

    def H(pts):
        return B(_rot([(x + 4, y - 98) for x, y in pts], hr, 0, -72))

    # torso, tea towel
    torso = [(-14, -58), (-34, -50), (-42, -30), (-45, 10), (-43, 60), (-41, 130), (40, 130), (37, 60), (34, 10),
             (30, -24), (24, -46), (8, -58)]
    it.append(_p(B(torso), JUMPER))
    it.append(_p(B([(-42, -30), (-45, 10), (-43, 60), (-41, 130), (-34, 130), (-36, 20), (-36, -30)]), JUMPER_DK))
    towel = [(-2, -60), (-26, -57), (-44, -45), (-51, -4), (-39, -1), (-34, -38), (-14, -50), (0, -53)]
    it.append(_p(B(towel), (232, 224, 206)))
    for v in (-30, -14):
        it.append(_p(B([(-47.5, v), (-36.5, v + 1), (-36.2, v + 6), (-48.2, v + 5)]), RED))
    # neck and head
    it.append(_p(B([(-12, -56), (6, -56), (5, -76), (-11, -78)]), SKIN_SH))
    skull = [(-24, 4), (-25, -10), (-19, -22), (-6, -28), (8, -27), (18, -20), (23, -9), (24, -2), (23, 3), (30, 11),
             (29, 14), (24, 15), (25, 19), (23, 21), (24, 24), (21, 29), (12, 33), (4, 32), (-4, 26), (-14, 22),
             (-22, 14)]
    it.append(_p(H(skull), SKIN))
    it.append(_p(H([(4, 22), (12, 24), (20, 22), (24, 24), (21, 29), (12, 33), (4, 32)]), (196, 138, 112)))
    it.append(_p(H(_oval(-4, 3, 5, 7)), SKIN_SH))
    it.append(_p(H([(21, 19.5), (25, 19), (25, 20.4), (21, 20.8)]), (150, 90, 80)))              # mouth
    it.append(_p(H([(13, 2.5), (19, 3), (19, 4), (13, 3.8)]), (196, 132, 108)))                # tired under-eye
    if glance > 0.5:
        it.append(_p(H(_oval(17, -4, 1.8, 2.2)), (50, 36, 48)))                             # eyes open, up
        it.append(_p(H([(11, -11), (21, -12), (21, -10.4), (11, -9.4)]), (66, 46, 54)))
    else:
        it.append(_p(H([(12, -2.4), (15, -1.2), (19, -2), (19, -0.8), (15, 0.2), (12, -1)]), (60, 40, 50)))
        it.append(_p(H([(11, -9), (21, -9), (21, -7.6), (11, -7.6)]), (66, 46, 54)))
    w = [1.6 * math.sin(tl * 3.1 + k) for k in range(6)]                                    # hair, messily alive
    hair = [(-26, 8), (-29, -4), (-34 + w[0], -10), (-27, -16), (-32 + w[1], -27), (-19, -27), (-18 + w[2], -39),
            (-6, -31), (0 + w[3], -42), (6, -31), (15 + w[4], -38), (15, -27), (27 + w[5], -28), (21, -19),
            (26, -13), (17, -15), (10, -20), (0, -19), (-8, -16), (-14, -10), (-17, -2), (-18, 8)]
    it.append(_p(H(hair), (66, 46, 54)))
    it.append(_p(H([(-18, -27), (-6, -31), (0, -24), (-10, -22)]), (84, 60, 66)))
    # far forearm (behind the baby), the baby, her tiny hand, his far hand patting
    it.append(_p(B(_bar(10, 34, 62, -2, 16, 13)), JUMPER_DK))
    it.append(_p(B(_oval(44, -6, 23, 45, -0.14)), SWADDLE))
    it.append(_p(B([(24, -30), (58, -52), (66, -40), (60, -34), (30, -16)]), (218, 206, 188)))  # swaddle fold
    it.append(_p(B([(28, 20), (64, 4), (66, 12), (34, 32)]), (218, 206, 188)))
    bx, by = 40, -54
    it.append(_p(B(_oval(bx, by, 15, 14.5)), (240, 196, 170)))
    it.append(_p(B([(bx - 15, by - 1), (bx - 13, by - 10), (bx - 5, by - 16), (bx + 6, by - 16), (bx + 13, by - 10),
                    (bx + 15, by - 2), (bx + 8, by - 5), (bx - 6, by - 5)]), DBLUE))                  # knitted hat
    it.append(_p(B([(bx - 13, by - 3), (bx + 14, by - 3), (bx + 14, by - 0.5), (bx - 13, by - 0.5)]), (140, 164, 204)))
    it.append(_p(B(_oval(bx + 1, by - 17, 3.5, 3)), (140, 164, 204)))
    it.append(_p(B([(bx - 1, by + 3), (bx + 4, by + 4.2), (bx + 4, by + 5), (bx - 1, by + 4)]), (150, 96, 90)))   # closed eye
    it.append(_p(B([(bx + 8, by + 3), (bx + 12, by + 3.6), (bx + 12, by + 4.4), (bx + 8, by + 4)]), (150, 96, 90)))
    it.append(_p(B(_oval(bx + 9, by + 8, 3.2, 2.2)), (236, 160, 150)))                       # rosy cheek
    it.append(_p(B(_oval(bx + 6, by + 6.5, 1.2, 1)), (200, 130, 116)))
    reach = _smooth(1.8, 2.6, tl) * (1 - _smooth(3.6, 4.4, tl)) + 0.7 * _smooth(6.0, 6.6, tl)
    curl = 0.5 + 0.5 * math.sin(tl * 2.3)
    hx, hy = 30 - 6 * reach, -33 - 9 * reach + 0.8 * math.sin(tl * 4)
    it.append(_p(B(_oval(hx, hy, 5, 4.2, -0.4 - reach)), ROSE))
    for j in range(3):
        a = -1.6 - reach + j * 0.45
        fl = 4.5 + 2 * (1 - curl)
        it.append(_p(B(_oval(hx + math.cos(a) * fl, hy + math.sin(a) * fl, 1.9, 1.5)), ROSE))
    it.append(_p(B(_oval(hx + 4, hy + 4, 5, 3.5, 0.5)), SWADDLE))                            # cuff of blanket
    pat = max(0.0, math.sin(T * tl / 0.7)) ** 2
    fh = [(56, -4), (66, -6), (72, -20), (70, -30), (65, -31), (63, -20), (56, -12)]
    it.append(_p(B([(x + 2 * pat, y - 3 * pat) for x, y in fh]), SKIN_SH))
    for j in range(3):
        it.append(_p(B(_bar(66 + j * 2.5 + 2 * pat, -22 - 3 * pat, 62 + j * 3 + 2 * pat, -33 + j * 1.5 - 3 * pat, 3)),
                     SKIN_SH))
    # near arm: upper arm down, forearm cradling under the bundle, hand curled round
    it.append(_p(B(_bar(-8, -44, -4, 40, 25, 21)), JUMPER_LT))
    it.append(_p(B(_oval(-5, 40, 11, 11)), JUMPER_LT))
    it.append(_p(B(_bar(-4, 40, 50, 38, 20, 17)), JUMPER_LT))
    it.append(_p(B(_bar(-2, 47, 48, 45, 5, 4)), JUMPER))                                     # sleeve crease
    it.append(_p(B(_bar(46, 38, 54, 37, 18, 17)), JUMPER))                                   # cuff
    it.append(_p(B([(54, 30), (66, 28), (72, 22), (74, 30), (68, 42), (54, 46)]), SKIN))
    it.append(_p(B([(62, 30), (70, 22), (73, 24), (66, 33)]), SKIN_SH))
    return it


def _steam(cx, tl):
    it = []
    sx, sy = cx + 66, 574
    n = 13
    puffs = []
    for i in range(n):
        a = (tl * 0.3 + i / n) % 1.0
        puffs.append((a, i))
    for a, i in sorted(puffs, reverse=True):                   # oldest first, youngest on top
        x = sx - 34 * a + 10 * math.sin(a * 6 + tl * 0.8) * a + 4 * math.sin(i * 2.1) * a
        y = sy - 4 - 96 * a
        r = 5 + 15 * a
        col = _mix((252, 242, 222), WALL_IN, 0.12 + 0.88 * a ** 1.4)
        it.append(_p(_oval(x, y, r, r * 0.8, a * 2 + i), col))
    return it


def action_items(tl, cx, ground):
    it = []
    it += _clock_face(cx)
    it += _clock_hands(cx, 14 + math.floor(tl))
    it += _steam(cx, tl)
    it += _dad(cx, tl)
    it += _foreground(cx)
    return it
