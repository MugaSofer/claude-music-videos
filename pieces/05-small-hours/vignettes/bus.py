"""The night bus: "The night bus hums its empty rooms along the long way round."

A double-decker N29 sweeps in from the right (screen), brakes (nose dips, then rocks back), stops at an empty stop, opens
its doors to nobody, closes them, and pulls away along the long way round. Upstairs one passenger sleeps with
their head against the glass; downstairs one sits with a hood up and a phone lighting their face; the driver
has both hands on the big flat wheel. Wheels turn by the distance travelled, the body rides bumps in the road
on its own suspension (front and rear axles lift separately), idles with a small shiver, one fluorescent tube
stutters, headlights throw a cone ahead.

Set: a low terrace of shuttered shops (one upstairs telly still on), a street lamp, a bin and the bus stop.

Local coordinates: x from the vignette centre, y up from the pavement top as negative numbers.
"""
import math

import numpy as np

PAPER = (239, 230, 210)
GOLD = (255, 201, 120)
WARMWIN = (255, 216, 154)
INK = (21, 26, 51)

TERR = (50, 52, 96)
TERR_LT = (64, 66, 112)
TERR_DK = (36, 38, 74)
SHUTTER = (58, 60, 102)
SHUTTER_LN = (44, 46, 84)
RISER = (32, 34, 64)
POST = (28, 30, 56)

RED = (178, 54, 44)
RED_DK = (132, 38, 36)
RED_LT = (204, 84, 64)
ARCH = (52, 24, 34)
TYRE = (34, 30, 46)
HUB = (140, 136, 154)
LIT = (246, 222, 164)
LIT_TOP = (255, 238, 200)
SEAT = (126, 74, 62)
SEAT_DK = (98, 56, 52)
POLE = (226, 178, 70)
FIG = (46, 38, 62)
GLASS_DK = (44, 44, 76)

HALF = 360            # half length of the bus
ROOF = -402
WHEEL_R = 40
AXLES = (-236, 232)

# Timing is fitted to the film's camera (film.py): at tl=0 the camera arrives wide (zoom 1.0), pushes in to 2.1
# by tl=1.2, holds until about tl=5.2, then drifts on to the nurse. So: the bus sweeps in during the wide
# arrival, is settled at the stop as the push-in lands, doors open to nobody, and it is gone by 5.2.
# Everything below is painted left-to-right and mirrored at the very end, so on screen the bus comes in from
# the right (from where the nurse's hospital is, never crossing the baker's shot) and leaves to the left.
T_ARR0, T_STOP, T_GO, T_END = -1.0, 1.4, 3.2, 5.4
STOP_X = -50
D_ARR, D_GO = 1500.0, 950.0
MIRROR = True
LX = 175              # street lamp offset (keeps its head clear of where the moon sits in the close-up)
BUMPS = (-820, -420, 60, 540, 980, 1500)


# ---------------------------------------------------------------- helpers
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


def _deckle(pts, seed, amp=0.9, step=26.0):
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


def _boil(pts, tl, seed, amp=0.6):
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


def _hash(*ints):
    h = 2166136261
    for v in ints:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    return (h & 0xFFFF) / 65535.0


def _clip_x(pts, xc, keep_left):
    """Sutherland-Hodgman against one vertical line."""
    def inside(p):
        return p[0] <= xc if keep_left else p[0] >= xc
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ia, ib = inside(a), inside(b)
        if ia:
            out.append(a)
        if ia != ib:
            t = (xc - a[0]) / (b[0] - a[0])
            out.append((xc, a[1] + (b[1] - a[1]) * t))
    return out


_FONT = {
    'N': [[(0, 0), (0, 3), (2, 0), (2, 3)]],
    '2': [[(0, 2.5), (0.5, 3), (1.5, 3), (2, 2.5), (2, 1.9), (0, 0), (2, 0)]],
    '9': [[(2, 1.5), (0.5, 1.5), (0, 2), (0, 2.5), (0.5, 3), (1.5, 3), (2, 2.5), (2, 0.5), (1.5, 0), (0.3, 0)]],
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


def _place(items, cx, ground):
    m = -1 if MIRROR else 1
    return [(k, [(cx + m * x, ground + y) for x, y in pts], col) for k, pts, col in items]


# ---------------------------------------------------------------- the set
def _stop_pole():
    it = [('poly', _rect(330, -330, 336, 0), POST),
          ('poly', _deckle(_rect(312, -372, 356, -326), 41, 0.6, 10), (222, 214, 198)),         # the flag
          ('poly', _rect(312, -372, 356, -362), RED),                                         # a generic bus flag
          ('poly', [(320, -356), (346, -356), (348, -352), (348, -338), (320, -338)], RED),
          ('poly', _rect(323, -353, 345, -347), (222, 214, 198)),
          ('poly', _ellp(326, -337, 3.2, 3.2, 8), POST),
          ('poly', _ellp(342, -337, 3.2, 3.2, 8), POST),
          ('poly', _rect(322, -200, 344, -140), POST),                                          # timetable
          ('poly', _rect(325, -196, 341, -144), (200, 184, 140))]
    for k in range(5):
        it.append(('poly', _rect(327, -190 + k * 9, 339, -187 + k * 9), (150, 136, 110)))
    return it


def _lamp_post():
    pts = [(-292, -560), (-280, -578), (-252, -584), (-236, -580), (-236, -574), (-252, -578), (-278, -572),
           (-288, -556)]
    return [('poly', _rect(LX - 296, -560, LX - 288, 0), POST),
            ('poly', _rect(LX - 300, -40, LX - 284, 0), POST),
            ('poly', [(LX + x, y) for x, y in pts], POST)]


def _set_local():
    it = []
    # street lamp halo: over open sky, so real translucency is safe here
    for r, a in ((34, 34), (20, 60)):
        it.append(('poly', _ellp(LX - 243, -564, r * 1.2, r, 24), (255, 226, 170, a)))
    # low terrace of shops
    it.append(('poly', _deckle(_rect(-334, -300, 334, 0), 21), TERR))
    it.append(('poly', _deckle(_rect(-340, -312, 340, -298), 22), TERR_LT))
    for k, x in enumerate((-262, -20, 214)):                                              # chimney stacks
        it.append(('poly', _deckle(_rect(x, -352, x + 44, -310), 60 + k), TERR))
        it.append(('poly', _rect(x - 4, -358, x + 48, -350), TERR_LT))
        it.append(('poly', _rect(x + 6, -372, x + 16, -358), (92, 64, 70)))
        it.append(('poly', _rect(x + 26, -368, x + 36, -358), (92, 64, 70)))
    for k in range(6):                                                                    # upstairs windows
        x = -300 + k * 106
        it.append(('poly', _rect(x - 4, -270, x + 64, -196), TERR_DK))
        col = (84, 104, 160) if k == 3 else ((200, 140, 90) if k == 0 else (30, 32, 62))
        it.append(('poly', _rect(x, -266, x + 60, -200), col))
        if k == 0:                                                                        # another one awake
            it.append(('poly', [(x, -266), (x + 20, -266), (x + 14, -230), (x + 18, -200), (x, -200)], (150, 84, 70)))
            it.append(('poly', [(x + 60, -266), (x + 44, -266), (x + 50, -230), (x + 46, -200), (x + 60, -200)],
                       (150, 84, 70)))
        it.append(('poly', _rect(x + 28, -266, x + 32, -200), TERR_DK))
        it.append(('poly', _rect(x - 6, -198, x + 66, -192), TERR_LT))
    for x0, x1, seed in ((-326, -8, 23), (8, 326, 24)):                                   # two shuttered shops
        it.append(('poly', _deckle(_rect(x0, -178, x1, -150), seed), TERR_DK))
        it.append(('poly', _rect(x0 + 10, -168, x1 - 10, -160), (74, 76, 118)))
        it.append(('poly', _rect(x0 + 6, -150, x1 - 6, -70), SHUTTER))
        for y in range(-144, -72, 8):
            it.append(('poly', _rect(x0 + 6, y, x1 - 6, y + 2), SHUTTER_LN))
        it.append(('poly', _rect((x0 + x1) / 2 - 10, -80, (x0 + x1) / 2 + 10, -74), SHUTTER_LN))
    it.append(('poly', _rect(-334, -70, 334, 0), RISER))
    # a tag on one shutter, somebody else's small hours
    it.append(('poly', _seg((60, -110), (84, -126), 3), (150, 96, 130)))
    it.append(('poly', _seg((84, -126), (96, -106), 3), (150, 96, 130)))
    it.append(('poly', _seg((96, -106), (118, -122), 3), (150, 96, 130)))
    it += _lamp_post()
    it.append(('poly', _ellp(LX - 244, -568, 12, 7, 16), (255, 232, 176)))              # lamp head
    it.append(('poly', [(LX - 258, -576), (LX - 230, -576), (LX - 236, -568), (LX - 252, -568)], POST))
    # bin
    it.append(('poly', _deckle([(-196, 0), (-200, -52), (-160, -52), (-164, 0)], 25, 0.6, 12), (44, 60, 70)))
    it.append(('poly', _rect(-204, -58, -156, -50), (58, 76, 86)))
    it += _stop_pole()
    return it


def set_items(cx, ground):
    return _place(_set_local(), cx, ground)


# ---------------------------------------------------------------- motion
def _bus_x(tl):
    t1 = T_STOP - T_ARR0
    if tl < T_ARR0:
        return STOP_X - D_ARR - 2 * D_ARR / t1 * (T_ARR0 - tl)
    if tl < T_STOP:
        u = (tl - T_ARR0) / t1
        return STOP_X - D_ARR * (1 - u) ** 2
    if tl < T_GO:
        return STOP_X
    t2 = T_END - T_GO
    if tl < T_END:
        u = (tl - T_GO) / t2
        return STOP_X + D_GO * u * u
    return STOP_X + D_GO + 2 * D_GO / t2 * (tl - T_END)


def _smooth(a, b, x):
    u = min(max((x - a) / (b - a), 0), 1)
    return u * u * (3 - 2 * u)


def _pose(tl, bx):
    """Heave (px, up is negative y) and pitch (rad, + = nose down) of the body on its springs."""
    pitch = 0.0
    if tl < T_STOP:
        pitch += 0.016 * _smooth(T_ARR0, T_ARR0 + 1.2, tl)                               # braking dive
    else:
        d = tl - T_STOP
        pitch += 0.016 * math.exp(-d * 2.6) * math.cos(d * 8.0)                          # rocks back, settles
    if tl >= T_GO:
        d = tl - T_GO
        pitch -= 0.014 * (1 - math.exp(-d * 5)) * math.exp(-d * 0.5)                      # squats as it pulls away
    lift = []
    for ax in AXLES:
        x = bx + ax
        lift.append(sum(7 * math.exp(-((x - b) / 22) ** 2) for b in BUMPS))
    rear, front = lift
    heave = -(rear + front) / 2
    pitch += (rear - front) / (AXLES[1] - AXLES[0])
    heave += 1.3 * math.sin(tl * 2.1)                                                    # a slow float
    k = int(math.floor(tl * 12))
    idle = 1.0 if T_STOP <= tl <= T_GO else 0.45
    heave += idle * (_hash(k, 3) - 0.5) * 1.8                                            # engine shiver
    return heave, pitch


# ---------------------------------------------------------------- the bus
def _windows_upper():
    ws = []
    x = -334
    for k in range(6):
        ws.append((x, x + 96))
        x += 106
    return ws                                                  # last ends at 296


def _windows_lower():
    ws = []
    x = -334
    for k in range(5):
        ws.append((x, x + 90))
        x += 100
    return ws                                                  # last ends at 156


def _window(x0, x1, y0, y1, bright, kind, seed):
    """One lit bay: ceiling strip, back wall glow, a row of seat backs."""
    it = []
    base = _mix(GOLD, LIT, 0.6)
    base = _mix((150, 110, 80), base, bright)
    it.append(('poly', _rect(x0, y0, x1, y1), base))
    it.append(('poly', _rect(x0, y0, x1, y0 + 9), _mix(base, LIT_TOP, 0.7)))
    it.append(('poly', _rect(x0 + (x1 - x0) * 0.3, y0 + 2, x0 + (x1 - x0) * 0.7, y0 + 6), _mix(LIT_TOP, PAPER, 0.5)))
    # the lower half of the room a touch dimmer than the ceiling-lit top, and a grab rail
    it.append(('poly', _rect(x0, (y0 + y1) / 2 + 6, x1, y1), _mix(base, (150, 110, 90), 0.18)))
    it.append(('poly', _rect(x0, y0 + 20, x1, y0 + 23), _mix(base, POLE, 0.6)))
    # seat backs
    n = 2
    w = (x1 - x0) / n
    for j in range(n):
        sx = x0 + j * w + 8
        top = y1 - 24
        pts = [(sx, y1), (sx, top + 6), (sx + 4, top), (sx + w - 22, top), (sx + w - 18, top + 6), (sx + w - 18, y1)]
        it.append(('poly', pts, SEAT if (j + seed) % 3 else SEAT_DK))
        it.append(('poly', _rect(sx + 2, top + 2, sx + w - 20, top + 5), (160, 100, 80)))
    if kind == 'pole':
        it.append(('poly', _rect(x1 - 12, y0, x1 - 8, y1), POLE))
    return it


def _sleeper(tl, x, y1, heave):
    """Upstairs, head against the glass, asleep. Nods with the bumps."""
    tilt = 0.5 + 0.04 * math.sin(tl * 1.3) - heave * 0.02
    sink = max(0.0, heave) * 0.6
    it = []
    # slumped shoulders in a puffy jacket, sagging toward the window pillar
    it.append(('poly', [(x - 30, y1), (x - 30, y1 - 22), (x - 22, y1 - 36), (x - 4, y1 - 42), (x + 16, y1 - 44),
                        (x + 30, y1 - 36), (x + 36, y1 - 20), (x + 36, y1)], FIG))
    it.append(('poly', [(x - 8, y1 - 40), (x + 18, y1 - 43), (x + 16, y1 - 30), (x - 4, y1 - 30)], (120, 72, 84)))  # scarf
    it.append(('poly', [(x + 2, y1 - 32), (x + 12, y1 - 32), (x + 10, y1 - 8), (x + 2, y1 - 10)], (120, 72, 84)))
    hx, hy = x + 20, y1 - 60 + sink
    c, s = math.cos(tilt), math.sin(tilt)

    def R(px, py):
        return (hx + px * c - py * s, hy + px * s + py * c)

    it.append(('poly', [R(px, py) for px, py in _ellp(0, 0, 15, 19, 20)], (196, 150, 128)))        # the face
    it.append(('poly', [R(px, py) for px, py in [(-15, -2), (-17, -12), (-12, -22), (0, -27), (12, -22), (17, -12),
                                                (15, -2), (6, -6), (-6, -6)]], (92, 60, 84)))   # beanie
    it.append(('poly', [R(px, py) for px, py in _ellp(0, -28, 5, 5, 10)], (120, 80, 104)))        # bobble
    for ex in (-6, 6):                                                                             # eyes shut
        it.append(('poly', [R(px, py) for px, py in [(ex - 4, 1), (ex, 3), (ex + 4, 1), (ex + 4, 2.5), (ex, 4.5),
                                                    (ex - 4, 2.5)]], (70, 44, 50)))
    it.append(('poly', [R(px, py) for px, py in _ellp(1, 11, 2.5, 2, 8)], (90, 50, 56)))           # mouth, open a bit
    it.append(('poly', [R(px, py) for px, py in _ellp(-9, 7, 3, 2, 8)], (212, 138, 120)))          # warm cheek
    # the cheek pressed against the glass leaves a little breath fog on it
    fog = 0.5 + 0.5 * math.sin(tl * 1.6)
    fx, fy = R(18, 6)
    it.append(('poly', _ellp(fx + 4, fy, 5 + 2 * fog, 4 + 1.5 * fog, 10), _mix(LIT, PAPER, 0.5)))
    return it


def _phone_rider(tl, x, y1):
    """Downstairs, hood up, facing forward, the only cold light on the bus on their face."""
    it = []
    it.append(('poly', [(x - 26, y1), (x - 26, y1 - 30), (x - 16, y1 - 46), (x + 6, y1 - 48), (x + 20, y1 - 38),
                        (x + 26, y1)], FIG))
    hood = [(x - 16, y1 - 44), (x - 18, y1 - 64), (x - 10, y1 - 80), (x + 6, y1 - 84), (x + 18, y1 - 76),
            (x + 22, y1 - 60), (x + 18, y1 - 46)]
    it.append(('poly', hood, FIG))
    glow = 0.8 + 0.2 * math.sin(tl * 5.1) * math.sin(tl * 1.7)
    it.append(('poly', [(x + 10, y1 - 74), (x + 20, y1 - 70), (x + 22, y1 - 56), (x + 12, y1 - 50), (x + 8, y1 - 60)],
               _mix((90, 96, 130), (170, 190, 226), glow)))                                  # face in phone light
    it.append(('poly', [(x + 12, y1 - 44), (x + 30, y1 - 40), (x + 30, y1 - 30), (x + 12, y1 - 34)], FIG))  # arms
    it.append(('poly', [(x + 28, y1 - 50), (x + 34, y1 - 48), (x + 32, y1 - 34), (x + 26, y1 - 36)],
               _mix((150, 176, 226), (226, 236, 250), glow)))                                # the phone
    return it


def _driver(tl, x, y1):
    it = []
    sway = 1.5 * math.sin(tl * 1.9)
    it.append(('poly', [(x - 22, y1), (x - 22, y1 - 34), (x - 12, y1 - 50), (x + 6, y1 - 50), (x + 14, y1 - 38),
                        (x + 16, y1)], FIG))
    hx, hy = x - 4 + sway * 0.3, y1 - 52
    it.append(('poly', [(hx - 10, hy), (hx - 12, hy - 14), (hx - 6, hy - 24), (hx + 6, hy - 24), (hx + 10, hy - 16),
                        (hx + 15, hy - 11), (hx + 10, hy - 8), (hx + 8, hy)], FIG))
    it.append(('poly', [(hx - 13, hy - 18), (hx - 10, hy - 28), (hx + 6, hy - 29), (hx + 11, hy - 22),
                        (hx + 22, hy - 20), (hx + 20, hy - 17)], (30, 28, 48)))                # cap and peak
    it.append(('poly', [(x + 4, y1 - 40), (x + 30, y1 - 26), (x + 28, y1 - 20), (x + 2, y1 - 32)], FIG))  # arm
    it.append(('poly', _ellp(x + 34, y1 - 22, 18, 5, 16, -0.35 + sway * 0.02), (30, 28, 48)))   # the big wheel
    return it


def _bus_local(tl, bx):
    """All the bus shapes in bus-local coords (x along the bus, y up from the road), plus wheel data."""
    heave, pitch = _pose(tl, bx)
    body = []
    # the body shell
    shell = [(-HALF, -34), (-HALF - 2, -300), (-HALF + 4, -372), (-HALF + 18, -394), (-HALF + 40, ROOF),
             (HALF - 44, ROOF), (HALF - 18, -396), (HALF - 4, -378), (HALF, -340), (HALF + 2, -240), (HALF + 6, -120),
             (HALF + 6, -34)]
    body.append(('poly', _deckle(shell, 51, 0.8, 30), RED))
    body.append(('poly', [(-HALF + 40, ROOF), (HALF - 44, ROOF), (HALF - 30, ROOF + 6), (-HALF + 28, ROOF + 6)], RED_LT))
    body.append(('poly', _rect(-HALF - 1, -74, HALF + 6, -34), RED_DK))                 # skirt
    body.append(('poly', _rect(-HALF - 1, -236, HALF + 3, -228), RED_LT))               # between decks
    body.append(('poly', _rect(-HALF - 1, -216, HALF + 3, -212), RED_DK))
    # upper deck bays, the front one wrapping round the nose
    flick_k = int(math.floor(tl * 12))
    uw = _windows_upper()
    for k, (x0, x1) in enumerate(uw):
        b = 0.94 + 0.06 * math.sin(tl * 0.7 + k)
        body += _window(x0, x1, -380, -262, b, None, k)
    body.append(('poly', [(306, -380), (HALF - 22, -380), (HALF - 8, -366), (HALF - 4, -330), (HALF - 2, -262),
                          (306, -262)], _mix(GOLD, LIT, 0.6)))
    body.append(('poly', [(310, -262), (310, -280), (HALF - 3, -284), (HALF - 2, -262)], SEAT_DK))
    # lower deck bays; the rear-most tube stutters
    lw = _windows_lower()
    for k, (x0, x1) in enumerate(lw):
        b = 0.96
        if k == 0:
            h = _hash(flick_k, 17)
            b = 0.35 if h < 0.28 else (0.7 if h < 0.4 else 0.97)
        body += _window(x0, x1, -206, -100, b, 'pole' if k in (1, 3) else None, k + 3)
    # passengers
    body += _sleeper(tl, uw[3][0] + 40, -262, heave)
    body += _phone_rider(tl, lw[2][0] + 36, -100)
    # the front door, folding leaves; open while the bus waits at the stop
    op = _smooth(T_STOP + 0.2, T_STOP + 0.55, tl) * (1 - _smooth(T_GO - 0.7, T_GO - 0.35, tl))
    d0, d1 = 176, 262
    body.append(('poly', _rect(d0, -212, d1, -40), (200, 170, 124)))                      # lit step well
    body.append(('poly', _rect(d0, -60, d1, -40), (150, 120, 90)))
    body.append(('poly', _rect(d0 + 30, -212, d0 + 34, -60), POLE))
    lw_ = (d1 - d0) / 2 * (1 - 0.78 * op)
    for side in (0, 1):
        if side == 0:
            a, b = d0, d0 + lw_
        else:
            a, b = d1 - lw_, d1
        body.append(('poly', _rect(a, -212, b, -40), RED_DK))
        body.append(('poly', _rect(a + 5, -204, b - 5, -120), _mix(LIT, GLASS_DK, 0.25)))
        body.append(('poly', _rect(a + 5, -110, b - 5, -54), _mix(LIT, GLASS_DK, 0.35)))
    # driver's cab and windscreen
    body.append(('poly', [(272, -206), (HALF - 2, -206), (HALF + 4, -120), (272, -120)], _mix(LIT, GLASS_DK, 0.3)))
    body += _driver(tl, 306, -120)
    body.append(('poly', _rect(268, -120, HALF + 5, -112), RED_DK))
    # route number box on the side, N29
    body.append(('poly', _rect(196, -258, 262, -230), (30, 26, 36)))
    txt = _text('N29', 204, -236, 17, 3.2, (255, 190, 90))
    if MIRROR:                                     # pre-flip the lettering so it reads right way round on screen
        txt = [(k, [(458 - x, y) for x, y in pts], c) for k, pts, c in txt]
    body += txt
    # front blind
    body.append(('poly', [(HALF - 26, -396), (HALF - 14, -392), (HALF - 6, -380), (HALF - 22, -380)], (255, 190, 90)))
    # headlight, tail light, indicator
    body.append(('poly', _ellp(HALF + 2, -86, 8, 11, 12), (255, 248, 226)))
    body.append(('poly', _rect(-HALF - 3, -100, -HALF + 3, -80), (230, 60, 50)))
    body.append(('poly', _rect(HALF - 2, -110, HALF + 5, -102), (240, 150, 50)))
    # engine grille at the back
    body.append(('poly', _rect(-HALF + 8, -148, -HALF + 58, -110), RED_DK))
    for k in range(4):
        body.append(('poly', _rect(-HALF + 12, -144 + k * 9, -HALF + 54, -140 + k * 9), (96, 30, 30)))
    # wheel arches (cut into the body)
    for ax in AXLES:
        body.append(('poly', [(ax + 50 * math.cos(a), -40 - 50 * math.sin(a)) for a in np.linspace(0, math.pi, 14)]
                     + [(ax - 50, -34), (ax + 50, -34)], ARCH))
    # transform the body by pitch (about the wheelbase centre) and heave
    pc, ps = math.cos(pitch), math.sin(pitch)
    out = []
    for i, (kind, pts, col) in enumerate(body):
        tp = []
        for x, y in pts:
            yy = y + 40
            tp.append((bx + x * pc - yy * ps, -40 + x * ps + yy * pc + heave))
        out.append((kind, _boil(tp, tl, i, 0.5), col))
    return out, heave, pitch


def _wheels(bx, tl):
    it = []
    for j, ax in enumerate(AXLES):
        x, y = bx + ax, -WHEEL_R
        ang = (bx + ax) / WHEEL_R
        it.append(('poly', _ellp(x, y, WHEEL_R, WHEEL_R, 24), TYRE))
        it.append(('poly', _ellp(x, y, 22, 22, 18), HUB))
        it.append(('poly', _ellp(x, y, 17, 17, 18), (112, 108, 128)))
        for k in range(6):                                                                   # wheel nuts
            a = ang + k * math.pi / 3
            it.append(('poly', _ellp(x + 11 * math.cos(a), y + 11 * math.sin(a), 2.6, 2.6, 6), HUB))
        it.append(('poly', _ellp(x, y, 5, 5, 8), (170, 166, 180)))
        a = ang
        it.append(('poly', _seg((x + 26 * math.cos(a), y + 26 * math.sin(a)),
                                (x + 34 * math.cos(a), y + 34 * math.sin(a)), 3), (58, 54, 72)))  # a tread mark
    return it


def _beam(bx, heave, pitch):
    """Headlight cone. Where it falls on the terrace riser it is painted as lit riser (opaque, so it can't
    punch a hole in the layer); beyond the terrace it is real translucent light on the night."""
    hx, hy = bx + HALF + 4, -86 + heave + (HALF + 4) * pitch
    out = []
    layers = []
    for L, spread, t_lit, alpha in ((300, 1.0, 0.16, 40), (200, 0.7, 0.3, 64), (110, 0.45, 0.5, 100)):
        shape = [(hx, hy - 4), (hx + L, hy - 4 - 16 * spread), (hx + L * 1.08, min(hy + 60 * spread, -1)),
                 (hx, hy + 5)]
        layers.append((shape, _mix(RISER, (255, 214, 140), t_lit), (255, 226, 160, alpha)))
    for shape, lit, air in layers:
        on_riser = _clip_x(_clip_x(shape, 334, True), -334, False)
        # translucent only over open night between this set and the neighbours' (never over their shapes)
        pieces = [(on_riser, lit),
                  (_clip_x(_clip_x(shape, 660, True), 334, False), air),
                  (_clip_x(_clip_x(shape, -334, True), -660, False), air)]
        for pts, col in pieces:
            if len(pts) >= 3:
                out.append(('poly', [(x, min(max(y, -70), 0)) for x, y in pts], col))
    return out


def _exhaust(tl, bx, heave):
    it = []
    rate = 1.0 if tl < T_GO else 2.2
    for i in range(5):
        age = ((tl * rate / 1.6) + i / 5.0) % 1.0
        if tl >= T_GO and tl < T_GO + 1.5:
            age = min(age * 0.8, 1)
        x = bx - HALF - 10 - 50 * age - 10 * i % 3
        y = -46 + heave - 40 * age
        e = _smooth(0.55, 1.0, age)
        r = (4 + 14 * age) * (1 - e)
        if r < 1:
            continue
        it.append(('poly', _ellp(x, y, r * 1.2, r, 12), _mix((120, 118, 146), (70, 72, 110), age)))
    return it


def _telly(tl):
    """Upstairs over the shops: a television still on, flickering blue."""
    f = 0.5 + 0.3 * math.sin(tl * 9.1) * math.sin(tl * 2.3) + 0.2 * (_hash(int(tl * 12), 5) - 0.5)
    x = -300 + 3 * 106
    return [('poly', _rect(x, -266, x + 60, -200), _mix((60, 74, 130), (130, 150, 210), f)),
            ('poly', _rect(x + 28, -266, x + 32, -200), TERR_DK)]


def action_items(tl, cx, ground):
    bx = _bus_x(tl)
    it = _telly(tl)
    if -HALF - 900 < bx < 1000:
        body, heave, pitch = _bus_local(tl, bx)
        it += _beam(bx, heave, pitch)
        it += [('poly', _rect(330, -70, 336, 0), POST), ('poly', _rect(LX - 296, -70, LX - 288, 0), POST),
               ('poly', _rect(LX - 300, -40, LX - 284, 0), POST)]
        it += _exhaust(tl, bx, heave)
        it += body
        it += _wheels(bx, tl)
    return _place(it, cx, ground)
