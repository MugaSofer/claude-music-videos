"""Lorry: "A lorry driver sings along to a station turning into hiss".

An elevated motorway on concrete pillars crosses the frame, sodium lamps along it. A red
cab-over articulated lorry rolls left to right; through the lit side window we see the driver
in profile (hi-vis vest, ponytail), one hand on the wheel, singing, an air freshener swinging
from the windscreen. The radio's notes drift up out of the cab and slowly break into hiss.
"""
import math

D_OFF = 190          # deck top sits this far above ground
SPEED = 50.0         # world px per second (v3: 50, parked at cx+40, so it stays on the flat deck while in shot)
LAMPS = (-600, -330, -60, 210, 470)
FLICKER = -60        # the lamp that stutters
PILLARS = (-520, -190, 150, 400)
FLAT_L, FLAT_R = -640, 480
RAMP_L, RAMP_R = -940, 680

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


def _p(pts, col):
    return ('poly', [(float(x), float(y)) for x, y in pts], col)


def _e(x, y, rx, ry, col):
    return ('ell', (float(x - rx), float(y - ry), float(x + rx), float(y + ry)), col)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(x * (1 - t) + y * t)) for x, y in zip(a[:3], b[:3]))


def _xf(pts, ox, oy, ang=0.0, s=1.0, px=0.0, py=0.0):
    """Rotate local pts by ang around (px, py), scale by s, then translate to (ox, oy)."""
    c, sn = math.cos(ang), math.sin(ang)
    out = []
    for x, y in pts:
        x, y = x - px, y - py
        out.append((ox + s * (x * c - y * sn + px), oy + s * (x * sn + y * c + py)))
    return out


def _bar(x0, y0, x1, y1, w0, w1=None):
    """A tapered strip from (x0,y0) to (x1,y1)."""
    w1 = w0 if w1 is None else w1
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / n, dx / n
    return [(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2),
            (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2)]


def _hash(k):
    v = math.sin(k * 12.9898 + 78.233) * 43758.5453
    return v - math.floor(v)


def _deck_y(x, cx, D, ground):
    """Road surface height along the flyover, with smooth ramps down at both ends."""
    u = x - cx
    if FLAT_L <= u <= FLAT_R:
        return D
    if u < FLAT_L:
        t = min(1.0, (FLAT_L - u) / (FLAT_L - RAMP_L))
    else:
        t = min(1.0, (u - FLAT_R) / (RAMP_R - FLAT_R))
    t = 0.5 - 0.5 * math.cos(math.pi * t)
    return D + (ground - 8 - D) * t


# ----------------------------------------------------------------------------------- the set

def _lamp(cx, D, lx, bright=1.0, cone=True):
    """A sodium lamp: post rising behind the far barrier, arm reaching right, a glowing head."""
    it = []
    x = cx + lx
    hx, hy = x + 44, D - 318
    if cone:
        for w, a in ((112, 16), (84, 26), (56, 38), (30, 52)):
            it.append(_p([(hx - 8, hy + 6), (hx + 8, hy + 6), (hx + w, D - 34), (hx - w, D - 34)],
                         (255, 208, 130, int(a * bright))))
    it.append(_p([(x - 4, D - 20), (x + 4, D - 20), (x + 3, hy + 6), (x - 3, hy + 6)], (70, 72, 112)))
    arm = [(x - 3, hy + 8)]
    for k in range(7):                                        # a gently curved arm
        a = k / 6
        arm.append((x + 44 * a, hy - 12 * math.sin(math.pi * a * 0.9) + 2 * a))
    arm += [(x + 44, hy + 3)] + [(x + 44 * (1 - k / 6), hy - 12 * math.sin(math.pi * (1 - k / 6) * 0.9)
                                  + 2 * (1 - k / 6) + 5) for k in range(7)]
    it.append(_p(arm, (70, 72, 112)))
    it.append(_p([(hx - 16, hy - 2), (hx + 14, hy - 4), (hx + 12, hy + 4), (hx - 14, hy + 5)], (60, 62, 100)))
    it.append(_e(hx, hy + 5, 11, 4.5, _mix(MID, WARM, 0.3 + 0.7 * bright)))
    return it


def set_items(cx, ground):
    D = ground - D_OFF
    it = []
    # lamp cones first: translucent, so they must only lie over the (empty) sky
    for lx in LAMPS:
        it += _lamp(cx, D, lx)[:4]
    # pillars and pier caps (behind the deck)
    for px in PILLARS:
        x = cx + px
        it.append(_p([(x - 30, D + 50), (x + 30, D + 50), (x + 34, ground), (x - 34, ground)], INDIGO))
        it.append(_p([(x + 14, D + 50), (x + 30, D + 50), (x + 34, ground), (x + 18, ground)], (40, 46, 92)))
        it.append(_p([(x - 62, D + 38), (x + 62, D + 38), (x + 40, D + 58), (x - 40, D + 58)], (48, 52, 98)))
        for k in range(3):                                    # graffiti-free shutter lines, a little texture
            yy = D + 120 + k * 36
            it.append(_p([(x - 26, yy), (x + 26, yy), (x + 26, yy + 2), (x - 26, yy + 2)], (27, 32, 70)))
    # the deck: underside band, fascia, road edge, sampled along x so the ramps curve
    xs = list(range(cx + RAMP_L - 40, cx + RAMP_R + 41, 20))
    top = [(x, _deck_y(x, cx, D, ground)) for x in xs]
    it.append(_p(top + [(x, y + 52) for x, y in reversed(top)], (34, 38, 78)))           # underside shadow
    it.append(_p(top + [(x, y + 40) for x, y in reversed(top)], MID))                    # fascia
    it.append(_p([(x, y + 30) for x, y in top] + [(x, y + 40) for x, y in reversed(top)], (50, 54, 104)))
    it.append(_p([(x, y - 3) for x, y in top] + [(x, y + 5) for x, y in reversed(top)], (92, 92, 132)))
    # expansion joints on the fascia
    for u in (-440, -120, 220):
        it.append(_p([(cx + u, D + 5), (cx + u + 3, D + 5), (cx + u + 3, D + 40), (cx + u, D + 40)], (44, 48, 94)))
    # warm sodium pools along the road edge and the fascia top, under each lamp
    for lx in LAMPS:
        hx = cx + lx + 44
        for w, col in ((110, (126, 108, 124)), (70, (170, 132, 118)), (34, (214, 160, 118))):
            it.append(_p([(hx - w, D - 3), (hx + w, D - 3), (hx + w * 0.8, D + 6), (hx - w * 0.8, D + 6)], col))
    # far crash barrier (behind the lorry): posts and two rails
    for x in range(cx + FLAT_L, cx + FLAT_R, 34):
        it.append(_p([(x, D - 30), (x + 4, D - 30), (x + 4, D - 2), (x, D - 2)], (64, 66, 108)))
    for y0, y1 in ((D - 32, D - 24), (D - 17, D - 12)):
        it.append(_p([(cx + FLAT_L, y0), (cx + FLAT_R, y0), (cx + FLAT_R, y1), (cx + FLAT_L, y1)], (84, 86, 126)))
    # lamp posts and heads
    for lx in LAMPS:
        it += _lamp(cx, D, lx, cone=False)
    # a blue motorway sign on its own post, far left
    sx = cx - 470
    it.append(_p([(sx - 3, D - 30), (sx + 3, D - 30), (sx + 3, D - 150), (sx - 3, D - 150)], (70, 72, 112)))
    it.append(_p([(sx + 60, D - 30), (sx + 66, D - 30), (sx + 66, D - 150), (sx + 60, D - 150)], (70, 72, 112)))
    it.append(_p([(sx - 12, D - 222), (sx + 78, D - 222), (sx + 78, D - 142), (sx - 12, D - 142)], (52, 74, 140)))
    it.append(_p([(sx - 8, D - 218), (sx + 74, D - 218), (sx + 74, D - 146), (sx - 8, D - 146)], (58, 84, 156)))
    it.append(_p([(sx + 44, D - 206), (sx + 50, D - 206), (sx + 50, D - 158), (sx + 44, D - 158)], (200, 200, 210)))
    it.append(_p([(sx + 38, D - 206), (sx + 47, D - 214), (sx + 56, D - 206)], (200, 200, 210)))   # arrow
    for k, w in enumerate((30, 22, 26)):                    # "THE NORTH" as glyph bars
        y = D - 204 + k * 16
        it.append(_p([(sx + 2, y), (sx + 2 + w, y), (sx + 2 + w, y + 7), (sx + 2, y + 7)], (196, 196, 206)))
    return it


# ----------------------------------------------------------------------------------- the lorry

def _wheel(x, y, r, ang, it):
    it.append(_e(x, y, r, r, (32, 32, 52)))
    it.append(_e(x, y, r * 0.64, r * 0.64, (116, 116, 142)))
    it.append(_e(x, y, r * 0.5, r * 0.5, (96, 96, 124)))
    for k in range(6):                                          # lug holes: they make the turn readable
        a = ang + k * math.pi / 3
        it.append(_e(x + math.cos(a) * r * 0.42, y + math.sin(a) * r * 0.42, 2.6, 2.6, (46, 46, 70)))
    it.append(_e(x, y, r * 0.2, r * 0.2, (150, 150, 170)))
    a = ang * 0.5                                               # a tread notch on the tyre
    it.append(_e(x + math.cos(a) * r * 0.86, y + math.sin(a) * r * 0.86, 2.4, 2.4, (54, 54, 78)))


def _head(tl, m, nod):
    """Driver's head, facing +x, local coords centred on the head, returned as (pts, col) pairs."""
    jaw = 5 * m
    skull = [(-14, -2), (-14, -12), (-9, -19), (0, -22), (8, -20), (13, -13), (14, -6), (14, -2), (18, 4),
             (14, 6), (15, 8), (13, 9 + jaw * 0.3), (15, 10 + jaw), (13, 15 + jaw), (6, 18 + jaw * 0.7),
             (0, 16), (-2, 26), (-11, 26), (-10, 14)]
    hair = [(-16, 2), (-16, -12), (-10, -21), (0, -24), (9, -21), (14, -12), (10, -15), (3, -15), (-4, -12),
            (-8, -4), (-9, 6), (-13, 8)]
    swing = 3 * math.sin(tl * 5.2)
    tail = [(-14, -12), (-20, -8 + swing * 0.2), (-24 + swing * 0.5, 4), (-23 + swing, 16), (-19 + swing, 20),
            (-18 + swing * 0.6, 8), (-14, -2)]
    parts = [(tail, (98, 44, 40)), (skull, (206, 140, 108)),
             (hair, (112, 50, 44)),
             ([(-15, -11), (-12, -14), (-11, -9), (-14, -7)], (230, 196, 120))]         # hair band
    mouth = [(15, 8.5), (11, 9 + jaw * 0.4), (14.5, 9.6 + jaw)]
    parts.append((mouth, (86, 34, 40)))
    ear = [(-4 + 3 * math.cos(a), 1 + 4 * math.sin(a)) for a in [k * math.pi / 5 for k in range(10)]]
    parts.append((ear, (186, 118, 92)))
    blink = (tl % 3.3) < 0.18
    if blink or m > 0.8:                                        # eyes shut on the big notes
        parts.append(([(6, -5), (11, -4.6), (11, -3.6), (6, -4)], (70, 36, 40)))
    else:
        parts.append(([(8, -6), (10.5, -6), (10.5, -3.5), (8, -3.5)], (54, 30, 40)))
    parts.append(([(5, -9), (12, -10), (12, -8.6), (5, -7.8)], (96, 44, 40)))           # brow
    return parts


def _lorry(F, D, tl, dist, dy, light):
    """Articulated lorry, cab front at x=F, road surface at y=D."""
    it = []
    R = 30
    rot = dist / R
    cab = _mix((158, 48, 44), (224, 104, 66), 0.35 * light)
    cab_dk = _mix((112, 36, 42), (160, 64, 52), 0.35 * light)
    cab_lt = _mix((196, 74, 58), (240, 134, 84), 0.35 * light)
    trl = _mix((68, 74, 124), (120, 102, 118), 0.3 * light)
    trl_dk = _mix((50, 55, 100), (84, 72, 96), 0.3 * light)
    y = lambda v: D + v + dy                                     # body-space y (bounces)

    # ---- trailer
    Tf, Tr = F - 200, F - 672
    it.append(_p([(Tr, y(-290)), (Tf, y(-290)), (Tf, y(-80)), (Tr, y(-80))], trl))
    it.append(_p([(Tr, y(-290)), (Tf, y(-290)), (Tf, y(-282)), (Tr, y(-282))], _mix(trl, PAPER, 0.25)))
    for x in range(int(Tr) + 28, int(Tf), 40):                    # panel ribs
        it.append(_p([(x, y(-282)), (x + 3, y(-282)), (x + 3, y(-86)), (x, y(-86))], trl_dk))
    it.append(_p([(Tr, y(-150)), (Tf, y(-150)), (Tf, y(-126)), (Tr, y(-126))], _mix((170, 164, 170), GOLD, 0.25 * light)))
    it.append(_p([(Tr + 150, y(-236)), (Tr + 170, y(-236)), (Tr + 170, y(-172)), (Tr + 150, y(-172))], (184, 57, 46)))
    it.append(_p([(Tr + 176, y(-236)), (Tr + 290, y(-236)), (Tr + 290, y(-218)), (Tr + 176, y(-218))], (170, 164, 170)))
    it.append(_p([(Tr + 176, y(-208)), (Tr + 250, y(-208)), (Tr + 250, y(-194)), (Tr + 176, y(-194))], (150, 146, 156)))
    it.append(_p([(Tr, y(-80)), (Tf, y(-80)), (Tf, y(-68)), (Tr, y(-68))], trl_dk))                 # bottom rail
    it.append(_p([(Tr + 230, y(-54)), (Tf - 150, y(-54)), (Tf - 150, y(-46)), (Tr + 230, y(-46))], (120, 120, 140)))
    it.append(_p([(Tf - 96, y(-68)), (Tf - 88, y(-68)), (Tf - 88, D - 12), (Tf - 96, D - 12)], (70, 72, 100)))  # landing leg
    it.append(_p([(Tf - 104, D - 12), (Tf - 80, D - 12), (Tf - 80, D - 6), (Tf - 104, D - 6)], (70, 72, 100)))
    for x in range(int(Tr) + 40, int(Tf), 110):                   # amber side markers
        it.append(_e(x, y(-74), 3.4, 3, (255, 172, 80)))
    it.append(_p([(Tr - 3, y(-110)), (Tr + 3, y(-110)), (Tr + 3, y(-86)), (Tr - 3, y(-86))], (236, 84, 60)))
    for wx in (Tr + 70, Tr + 134, Tr + 198):
        it.append(_e(wx, y(-40), 36, 30, (40, 36, 60)))
        _wheel(wx, D - R + 2, R, rot, it)

    # ---- tractor chassis, tank, drive wheels
    it.append(_p([(F - 350, y(-84)), (F - 10, y(-84)), (F - 10, y(-64)), (F - 350, y(-64))], (46, 44, 66)))
    it.append(_p([(F - 196, y(-72)), (F - 128, y(-72)), (F - 126, y(-40)), (F - 194, y(-40))], (132, 134, 158)))
    it.append(_p([(F - 196, y(-72)), (F - 128, y(-72)), (F - 128, y(-66)), (F - 196, y(-66))], (170, 172, 190)))
    for wx in (F - 246, F - 306):
        it.append(_e(wx, y(-40), 36, 30, (40, 36, 60)))
        _wheel(wx, D - R + 2, R, rot, it)

    # ---- cab body
    body = [(F - 196, y(-62)), (F - 196, y(-252)), (F - 34, y(-258)), (F - 14, y(-248)), (F - 3, y(-150)),
            (F, y(-74)), (F - 4, y(-62))]
    it.append(_p([(F - 194, y(-252)), (F - 184, y(-288)), (F - 70, y(-284)), (F - 34, y(-258))], cab_dk))  # roof fairing
    it.append(_p([(F - 190, y(-284)), (F - 70, y(-282)), (F - 60, y(-276)), (F - 186, y(-278))], cab_lt))
    it.append(_p(body, cab))
    it.append(_p([(F - 196, y(-252)), (F - 34, y(-258)), (F - 14, y(-248)), (F - 16, y(-242)), (F - 196, y(-244))], cab_lt))
    it.append(_p([(F - 190, y(-120)), (F - 2, y(-120)), (F - 1, y(-112)), (F - 190, y(-112))], cab_dk))  # trim line
    # grille, bumper, lamps
    it.append(_p([(F - 6, y(-112)), (F + 2, y(-112)), (F + 3, y(-62)), (F - 6, y(-62))], (70, 50, 70)))
    it.append(_p([(F - 60, y(-70)), (F + 5, y(-70)), (F + 5, y(-52)), (F - 60, y(-52))], (82, 80, 104)))
    it.append(_e(F - 1, y(-94), 6, 7, WARM))
    it.append(_e(F - 3, y(-80), 3, 3, (255, 170, 70)))
    # wheel arch + front wheel
    it.append(_e(F - 64, y(-34), 38, 36, (40, 30, 46)))
    _wheel(F - 64, D - R + 2, R, rot, it)
    # step, door seam, handle
    it.append(_p([(F - 134, y(-80)), (F - 104, y(-80)), (F - 104, y(-72)), (F - 134, y(-72))], (70, 60, 84)))
    it.append(_p([(F - 142, y(-238)), (F - 139, y(-238)), (F - 139, y(-76)), (F - 142, y(-76))], cab_dk))
    it.append(_p([(F - 132, y(-138)), (F - 116, y(-138)), (F - 116, y(-133)), (F - 132, y(-133))], (70, 40, 44)))
    # a little name plate stripe
    it.append(_p([(F - 136, y(-104)), (F - 30, y(-104)), (F - 30, y(-98)), (F - 136, y(-98))], _mix(GOLD, cab, 0.4)))

    # ---- side window: the lit cab interior
    wx0, wx1, wt, wb = F - 134, F - 16, y(-240), y(-146)
    it.append(_p([(wx0 - 5, wt - 5), (F - 14, wt - 7), (F - 3, wb + 4), (wx0 - 5, wb + 4)], cab_dk))
    n = 8
    for k in range(n):                                            # warm gradient: dim at the back, glowing at the dash
        a0, a1 = k / n, (k + 1) / n
        col = _mix((150, 94, 70), (240, 176, 106), a1 ** 1.3)
        it.append(_p([(wx0 + (wx1 - wx0) * a0, wt), (wx0 + (wx1 - wx0) * a1 + 0.5, wt),
                      (wx0 + (wx1 - wx0) * a1 + 0.5, wb), (wx0 + (wx1 - wx0) * a0, wb)], col))
    it.append(_p([(wx0, wt), (wx0 + 16, wt), (wx0 + 16, wb), (wx0, wb)], (122, 44, 48)))            # sleeper curtain
    for k in range(3):
        xx = wx0 + 3 + k * 5
        it.append(_p([(xx, wt), (xx + 1.6, wt), (xx + 1.6, wb), (xx, wb)], (100, 34, 42)))
    it.append(_p([(F - 106, y(-228)), (F - 94, y(-228)), (F - 92, y(-146)), (F - 110, y(-146))], (80, 56, 70)))  # seat back
    it.append(_e(F - 99, y(-220), 9, 12, (86, 60, 74)))                                          # headrest
    # dash + radio glow
    glow = 0.55 + 0.45 * max(0.0, 1 - max(0.0, tl - 1.5) / 5.0)
    glow *= 0.85 + 0.15 * math.sin(tl * 23.0)
    it.append(_e(F - 26, y(-158), 11, 5, _mix((240, 176, 106), (252, 214, 150), glow)))
    it.append(_p([(F - 48, wb), (F - 12, wb), (F - 12, y(-154)), (F - 44, y(-152))], (78, 52, 62)))
    it.append(_p([(F - 31, y(-157)), (F - 20, y(-157)), (F - 20, y(-153)), (F - 31, y(-153))],
                 _mix((200, 140, 90), (255, 232, 176), glow)))
    for k in range(4):                                            # tiny equaliser bars, dying with the signal
        h = 1 + 3.5 * glow * abs(math.sin(tl * (7 + k * 3) + k))
        xx = F - 30 + k * 2.6
        it.append(_p([(xx, y(-157) - h), (xx + 1.5, y(-157) - h), (xx + 1.5, y(-157)), (xx, y(-157))],
                     _mix((200, 140, 90), (255, 236, 186), glow)))

    # ---- the driver
    beat = 2 * math.pi * tl / 0.72
    phrase = tl % 4.0
    sing = phrase < 3.3
    syl = abs(math.sin(2 * math.pi * 2.1 * tl + 0.7 * math.sin(tl * 1.3)))
    m = (0.25 + 0.75 * syl) * (0.7 + 0.3 * math.sin(tl * 0.9)) if sing else 0.05
    if sing and 1.9 < phrase < 2.8:                              # a held note: mouth wide, chin up
        m = 0.95
    nod = 0.05 * math.sin(beat) - (0.08 if m > 0.9 else 0.0)
    hx, hy = F - 80, y(-200) + 1.5 * math.sin(beat)
    # torso: navy jumper under a hi-vis vest with a reflective band
    it.append(_p([(F - 112, wb), (F - 110, y(-168)), (F - 96, y(-178)), (F - 78, y(-176)), (F - 68, y(-164)),
                  (F - 64, wb)], (58, 62, 112)))
    it.append(_p([(F - 108, wb), (F - 106, y(-168)), (F - 98, y(-176)), (F - 90, y(-174)), (F - 86, y(-160)),
                  (F - 78, wb)], _mix(FOX, (255, 170, 80), 0.35)))
    it.append(_p([(F - 109, y(-160)), (F - 79, y(-160)), (F - 79, y(-155)), (F - 109, y(-155))], (236, 226, 204)))
    for pts, col in _head(tl, m, nod):
        it.append(_p(_xf(pts, hx, hy, nod, 1.15, 0, 20), col))
    # steering wheel, edge on, and the hand gripping it (fingers tap the beat)
    it.append(_p(_bar(F - 44, y(-180), F - 26, wb, 6), (54, 44, 60)))                          # wheel rim, edge on
    it.append(_p(_bar(F - 36, y(-164), F - 22, wb, 5), (64, 50, 66)))                         # column
    tap = 1.5 * max(0.0, math.sin(beat))
    it.append(_p(_bar(F - 76, wb + 2, F - 44, y(-170), 11, 9), (66, 70, 122)))               # forearm
    it.append(_p(_bar(F - 50, y(-167), F - 42, y(-172), 7, 6), (230, 222, 206)))             # jumper cuff
    it.append(_e(F - 41, y(-174) - tap, 7, 6, (206, 140, 108)))                              # fist
    it.append(_e(F - 37, y(-176) - tap, 3.5, 2.6, (224, 162, 128)))                          # knuckle light
    # windscreen pillar and air freshener
    it.append(_p([(F - 32, wt - 7), (F - 14, wt - 7), (F - 3, wb + 4), (F - 13, wb + 4), (F - 20, wt + 6),
                  (F - 34, wt)], cab_dk))
    pivot = (F - 36, wt + 2)
    sw = 0.42 * math.sin(tl * 2.7) + 0.25 * math.sin(tl * 6.1 + 1.0) - 0.004 * SPEED * 0.3 + 0.9 * dy / 6
    tree = [(0, 0.6), (0.6, 0.6), (0.6, 18), (0, 18), (-7, 22), (-3, 22), (-9, 29), (-4, 29), (-10, 37),
            (10, 37), (4, 29), (9, 29), (3, 22), (7, 22), (0.6, 18)]
    tree = [(x, y_) for x, y_ in tree]
    it.append(_p(_bar(pivot[0], pivot[1], pivot[0] + 18 * math.sin(sw), pivot[1] + 18 * math.cos(sw), 1.2),
                 (90, 60, 70)))
    it.append(_p(_xf([(x, y_ - 18) for x, y_ in tree[4:14]], pivot[0] + 18 * math.sin(sw),
                     pivot[1] + 18 * math.cos(sw), -sw), DBLUE))
    # mirror on its arm
    it.append(_p(_bar(F - 6, y(-214), F + 14, y(-218), 3), (60, 44, 60)))
    it.append(_p([(F + 10, y(-240)), (F + 21, y(-238)), (F + 21, y(-196)), (F + 10, y(-194))], (60, 44, 60)))
    it.append(_p([(F + 12, y(-236)), (F + 16, y(-236)), (F + 16, y(-198)), (F + 12, y(-198))], (96, 90, 120)))
    return it


ACC = 2.5           # v3: the lorry waits on the flyover (it's there whenever the camera passes, so it never pops
                    # in), then pulls away as its verse starts, easing up to speed over ACC seconds


def _rot(p, o, a, shift=(0.0, 0.0)):
    """Rotate p about o by a (positive lifts points to the right of o, in screen coordinates), then shift."""
    c, sn = math.cos(a), math.sin(a)
    x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * c + y * sn + shift[0], o[1] - x * sn + y * c + shift[1])


def front(tl, cx):
    F0 = cx + 40
    if tl <= 0:
        return F0
    if tl < ACC:
        return F0 + SPEED * tl * tl / (2 * ACC)
    return F0 + SPEED * (tl - ACC / 2)


def reach_time(x, cx):
    """When the cab front reaches world x (the inverse of front()); -inf if it's already past."""
    d = x - (cx + 40)
    if d < 0:
        return -1e9
    if d < SPEED * ACC / 2:
        return math.sqrt(2 * ACC * d / SPEED)
    return d / SPEED + ACC / 2


def action_items(tl, cx, ground):
    D = ground - D_OFF
    F0 = cx + 40
    F = front(tl, cx)
    dist = F - F0
    # bump over expansion joints: each wheel crossing gives a small damped bounce
    dy = 0.0
    for u in (-440, -120, 220):
        for off in (-64, -276, -600):                             # front axle, drive axles, trailer axles
            tc = reach_time(cx + u - off, cx)
            if tl > tc:
                a = tl - tc
                dy += -2.6 * math.exp(-a * 3.2) * math.sin(a * 16)
    light = sum(math.exp(-((F - 90 - (cx + lx + 44)) / 110) ** 2) for lx in LAMPS)
    it = []
    # the stuttering lamp
    fl = 1.0
    ph = (tl * 7.3) % 9.0
    if ph < 1.2:
        fl = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(tl * 61))
    elif 5.0 < ph < 5.4:
        fl = 0.4
    it += _lamp(cx, D, FLICKER, bright=fl)
    # headlight beam (translucent, only over the sky above the barrier)
    by = D - 94 + dy
    reach = max(0.0, min(1.0, (cx + FLAT_R + 120 - F) / 440))     # v3: the beam stops where the flyover ends,
    beam = []                                                     # so it never shines across the next building
    wall = cx + 1000 - 500 - 6                                    # v4: the dad's terrace (VX 6200, its neighbour's
    for L, top, a in ((440, 176, 14), (380, 150, 24), (300, 124, 36), (210, 100, 50), (120, 80, 66)):   # wall from
        L = min(L * reach, wall - F)                              # -500) is drawn before us, so clip the beam to it
        if L < 8:
            continue
        beam.append(_p([(F + 2, by - 5), (F + L, by - top * L / 440), (F + L, D - 36), (F + L * 0.4, D - 36),
                        (F + 2, by + 7)], (255, 214, 140, a)))
    # a warm pool where the beam hits the road edge (opaque, pre-blended)
    for w, col in ((300, (130, 112, 128)), (180, (178, 146, 128)), (80, (222, 184, 140))):
        w = min(w * reach, wall - F - 60)                         # v4: this too stops at the terrace wall
        if w < 8:
            continue
        beam.append(_p([(F + 60, D - 3), (F + 60 + w, D - 3), (F + 60 + w * 0.9, D + 4), (F + 60, D + 4)], col))
    body = _lorry(F, D, tl, dist, dy, min(1.0, light))
    # v3: on the ramps the rig articulates: the tractor pivots on its drive axle to sit on the deck under its
    # front and drive wheels, and the trailer hangs from the kingpin and rests on its own axles
    h = lambda x: _deck_y(x, cx, D, ground) - D
    hf, hd, ht = h(F - 64), h(F - 276), h(F - 600)
    a_trac = math.atan2(hd - hf, 212)                            # screen y is down: a rising front is +
    piv_t = (F - 276, D + hd)
    kx, ky = _rot((F - 200, D), (F - 276, D), a_trac)            # the kingpin, carried by the tractor
    ky += hd
    a_trl = math.atan2(ht - (ky - D), 400)

    def place(item):
        kind, g, col = item
        if kind == 'poly':
            cxm = sum(p[0] for p in g) / len(g)
        else:
            cxm = (g[0] + g[2]) / 2
        if cxm >= F - 200:
            f = lambda p: _rot(p, (F - 276, D), a_trac, (0.0, hd))
        else:
            f = lambda p: _rot(p, (F - 200, D), a_trl, (kx - (F - 200), ky - D))
        if kind == 'poly':
            return (kind, [f(p) for p in g], col)
        x0, y0, x1, y1 = g
        mx, my = f(((x0 + x1) / 2, (y0 + y1) / 2))
        return (kind, (mx - (x1 - x0) / 2, my - (y1 - y0) / 2, mx + (x1 - x0) / 2, my + (y1 - y0) / 2), col)
    it += [place(i) for i in beam] + [place(i) for i in body]
    # the radio drifting out of the cab: notes that break up into hiss as the station fades
    for k in range(5, 24):                                       # v3: the song starts as it pulls away
        te = k * 0.45 - 2.0
        a = tl - te
        if a < 0 or a > 2.6:
            continue
        Fe = front(te, cx)
        x = Fe - 70 - 26 * a + 10 * math.sin(a * 2.5 + k)
        yy = D - 300 - 44 * a
        alpha = int(210 * min(1.0, a * 3) * (1 - a / 2.6))
        clear = max(0.0, min(1.0, 1 - (te - 0.5) / 4.5))
        if _hash(k) < clear:
            col = (255, 220, 160, alpha)
            tilt = 0.3 * math.sin(a * 3 + k)
            head = [(math.cos(t) * 5.4, math.sin(t) * 3.8) for t in [j * math.pi / 5 for j in range(10)]]
            it.append(_p(_xf(head, x, yy, -0.35 + tilt, 1.5), col))
            stem = [(4.2, 0), (5.8, 0), (5.8, -16), (4.2, -16)]
            flag = [(5.8, -16), (12, -10), (11, -8), (5.8, -12)]
            it.append(_p(_xf(stem, x, yy, tilt, 1.5), col))
            it.append(_p(_xf(flag, x, yy, tilt, 1.5), col))
        else:
            col = (226, 220, 212, alpha)                           # static: a fizz of specks, re-scattered every drawing
            fr = math.floor(tl * 12)
            for j in range(9):
                h1, h2, h3 = _hash(k * 7 + j + fr * 0.37), _hash(k * 13 + j * 3 + fr * 0.71), _hash(k + j * 5.3)
                sx = x + (h1 - 0.5) * (16 + 26 * a)
                sy = yy + (h2 - 0.5) * (12 + 18 * a)
                w = 1.6 + 4.5 * h3
                it.append(_p([(sx, sy), (sx + w, sy), (sx + w, sy + 1.8), (sx, sy + 1.8)], col))
    return it
