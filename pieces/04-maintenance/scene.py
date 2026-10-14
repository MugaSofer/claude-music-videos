"""Maintenance: the picture. Vector-drawn in screen space so the camera can push in crisply.

World coordinates are a 1920x1080 view of the whole glasshouse at zoom 1.
usage: python scene.py OUT.mp4 [t0 t1]
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import cues as C
import glove_art as GA
from growth import Growth, sample_mask

W, H, FPS = 1920, 1080, 30
rng = np.random.default_rng(44)

# camera path: (time, centre x, centre y, zoom)
CAMERA = [(0, 960, 540, 1.0), (12, 960, 540, 1.06), (17, 470, 500, 2.6), (26, 445, 505, 3.0), (29, 430, 735, 1.9),
          (34, 430, 740, 1.9), (38, 900, 600, 1.55),
          (54, 1000, 560, 1.5), (60, 1220, 600, 2.4), (86, 1215, 590, 2.9), (104, 1215, 590, 3.1),
          (112, 1250, 640, 2.8), (130, 1260, 650, 2.9), (140, 1260, 650, 2.95)]


def ease(a):
    return a * a * (3 - 2 * a)


def camera(t):
    ts = [k[0] for k in CAMERA]
    i = int(np.clip(np.searchsorted(ts, t, side='right') - 1, 0, len(ts) - 2))
    a = ease(np.clip((t - ts[i]) / (ts[i + 1] - ts[i]), 0, 1))
    k0, k1 = np.array(CAMERA[i][1:]), np.array(CAMERA[i + 1][1:])
    return k0 + (k1 - k0) * a


def ramp(t, a, b):
    return float(ease(np.clip((t - a) / (b - a), 0, 1)))


# ------------------------------------------------------------------ the world
TAP = (420, 470)
POT_TAP = (420, 1000)
BENCH_Y = 760
BENCH_X = (600, 1400)
POTS = [(660 + 62 * k, BENCH_Y - 34) for k in range(5)]
STRAY = (660 + 62 * 5 + 40, BENCH_Y - 34)          # one pot out of line
PANE = (880, 70, 1110, 280)                        # the cracked pane
RAIL_Y = 470
HOOK_REAL, HOOK_REP = (1150, RAIL_Y), (1290, RAIL_Y)
CAN = (1292, BENCH_Y - 4)                          # bottom-centre of the watering can, under the replica's hook
SEEDLING = (1372, BENCH_Y - 34)
GS = 0.42                                          # glove scale


def glove_mask(hx, hy, size=(1920, 1080)):
    """A work glove hanging from a hook by its cuff: cuff at the top, fingers down."""
    im = Image.new('L', size, 0)
    d = ImageDraw.Draw(im)
    s = GS
    x0 = hx - 75 * s
    d.rectangle([x0 + 5 * s, hy + 8 * s, x0 + 145 * s, hy + 75 * s], fill=255)                       # cuff
    d.rounded_rectangle([x0, hy + 70 * s, x0 + 150 * s, hy + 190 * s], radius=int(30 * s), fill=255)   # palm
    for k, L in enumerate([66, 88, 96, 80]):
        fx = x0 + (4 + k * 36) * s
        d.rounded_rectangle([fx, hy + 170 * s, fx + 33 * s, hy + (190 + L) * s], radius=int(16 * s), fill=255)
    d.rounded_rectangle([x0 + 140 * s, hy + 110 * s, x0 + 200 * s, hy + 150 * s], radius=int(20 * s), fill=255)  # thumb
    return np.asarray(im) > 0


def leaf_poly(x, y, r, ang, v):
    k = np.linspace(0, np.pi, 7)
    xs = np.concatenate([np.cos(k) * r, np.cos(k[::-1]) * r])
    ys = np.concatenate([np.sin(k) * r * 0.42, -np.sin(k[::-1]) * r * 0.42])
    c, s_ = np.cos(ang), np.sin(ang)
    return [v.p(x + a * c - b * s_, y + a * s_ + b * c) for a, b in zip(xs, ys)]


def leaf_clusters(n, box, seed, col_lo, col_hi, r=(5, 13)):
    g = np.random.default_rng(seed)
    x = g.uniform(box[0], box[2], n)
    y = g.uniform(box[1], box[3], n) ** 1 + 0
    y = box[3] - (box[3] - box[1]) * g.beta(1.2, 2.6, n)       # denser low down
    rr = g.uniform(*r, n) * g.choice([0.7, 1.0, 1.6], n, p=[0.4, 0.45, 0.15])
    c = g.uniform(0, 1, (n, 1))
    cols = (np.array(col_lo) * (1 - c) + np.array(col_hi) * c).astype(int)
    ang = g.uniform(0, np.pi, n)
    return list(zip(x, y, rr, map(tuple, cols), ang))


BACK_LEAVES = leaf_clusters(3400, (120, 280, 1820, BENCH_Y + 10), 1, (24, 40, 28), (62, 90, 54), r=(6, 15))
FLOOR_LEAVES = leaf_clusters(260, (0, BENCH_Y + 170, 1920, 1080), 2, (70, 52, 30), (110, 82, 44), r=(4, 8))
MOTES = np.random.default_rng(3).uniform([700, 0], [1700, 900], (160, 2))


def build_growths():
    g = {}
    # 1: from the floor pot up the pipe to the tap handle, wrapping it
    at = np.vstack([np.column_stack([np.full(60, TAP[0] + 10) + rng.normal(0, 8, 60), np.linspace(960, 490, 60)]),
                    np.column_stack([TAP[0] + 22 * np.cos(np.linspace(0, 5.5, 50)), TAP[1] - 16 + 16 * np.sin(np.linspace(0, 5.5, 50))])])
    g['tap'] = (Growth([(POT_TAP[0] + 8, POT_TAP[1] - 40)], at, step=4, influence=80, kill=5, seed=1), 12.0, C.TAP_TURN[0])
    # 2: along the bench to the stray pot
    at = np.column_stack([np.linspace(POTS[0][0], STRAY[0] + 16, 90), BENCH_Y - 6 + rng.normal(0, 4, 90)])
    g['pot'] = (Growth([(POTS[0][0] - 30, BENCH_Y - 4)], at, step=4, influence=60, kill=6, seed=2), 32.0, C.POT_NUDGE[0])
    # 3: up the glazing bar to prop the cracked pane
    at = np.column_stack([np.full(90, PANE[0] - 8) + rng.normal(0, 5, 90), np.linspace(BENCH_Y - 40, PANE[3] - 20, 90)])
    g['pane'] = (Growth([(PANE[0] - 10, BENCH_Y - 20)], at, step=4, influence=70, kill=6, seed=3), 38.0, C.PANE_PROP[1])
    # 4: up the bench leg and the post to the rail, curling once round the real gloves' cuff
    real = glove_mask(*HOOK_REAL)
    cuff = real.copy(); cuff[int(HOOK_REAL[1] + 75 * GS):] = False
    at = np.vstack([np.column_stack([np.full(70, 1335) + rng.normal(0, 5, 70), np.linspace(1060, RAIL_Y + 6, 70)]),
                    np.column_stack([np.linspace(1330, HOOK_REAL[0] + 20, 40), np.full(40, RAIL_Y - 6)]),
                    sample_mask(cuff, 50, rng)])
    g['find'] = (Growth([(1335, 1075)], at, step=4, influence=80, kill=6, seed=4), 46.0, C.GLOVE_FIND)
    # 5: from the rail down into the empty hook's glove-shaped space: the replica
    rep = glove_mask(*HOOK_REP)
    at = sample_mask(rep, 2600, rng)
    g['replica'] = (Growth([(HOOK_REP[0], RAIL_Y + 2)], at, step=2.0, influence=50, kill=3.0, seed=5), *C.REPLICA)
    out = {}
    for k, (gr, t0, t1) in g.items():
        while gr.grow():
            pass
        th = gr.thickness(0.5, 0.42)
        born = np.array(gr.born, float)
        out[k] = dict(pos=np.array(gr.pos), parent=np.array(gr.parent), th=th,
                      bt=t0 + (t1 - t0) * born / max(born.max(), 1))
    return out, real, rep


GROWTHS, REAL_MASK, REP_MASK = build_growths()
REAL_IMG = Image.fromarray((REAL_MASK * 255).astype(np.uint8))
REP_IMG = Image.fromarray((REP_MASK * 255).astype(np.uint8))
REAL_SPRITE = GA.real_sprite()                            # v5: painted gloves (glove_art.py)
_sh = Image.new('RGBA', GA.MASK.size, (14, 18, 16, 0))
_sh.putalpha(GA.MASK.point(lambda q: int(q * 0.45)).filter(ImageFilter.GaussianBlur(GA.PX * 3)))
GLOVE_SHADOW = _sh


# ------------------------------------------------------------------ drawing
class View:
    def __init__(self, t):
        self.cx, self.cy, self.z = camera(t)

    def p(self, x, y):
        return (W / 2 + (x - self.cx) * self.z, H / 2 + (y - self.cy) * self.z)

    def box(self, x0, y0, x1, y1):
        a, b = self.p(x0, y0), self.p(x1, y1)
        return [a[0], a[1], b[0], b[1]]

    def w(self, v):
        return max(1, int(round(v * self.z)))


def light(t):
    w = ramp(t, *C.DAWN)
    return np.array([150, 160, 158]) * (1 - w) + np.array([222, 200, 160]) * w, w


def draw_frame(t):
    v = View(t)
    base, dawn = light(t)
    sh = lambda k, a=255: tuple(int(min(255, c * k)) for c in base) + (a,)
    img = Image.new('RGB', (W, H), sh(0.45)[:3])
    d = ImageDraw.Draw(img, 'RGBA')
    # glazing (the grey dawn beyond the glass) and the back wall's dwarf wall
    d.rectangle(v.box(-400, -400, 2320, BENCH_Y + 120), fill=sh(0.82))
    d.rectangle(v.box(-400, 640, 2320, BENCH_Y + 140), fill=(86, 82, 72))
    # background overgrowth: the plants have taken the back of the house
    for (x, y, r, col, ang) in BACK_LEAVES:
        a = v.p(x, y)
        if not (-60 < a[0] < W + 60 and -60 < a[1] < H + 60):
            continue
        d.polygon(leaf_poly(x, y, r, ang, v), fill=col)
    img = img.filter(ImageFilter.GaussianBlur(max(0.5, v.z * 1.9)))       # the back of the house is out of focus
    if v.z > 1.6:                                                         # and recedes as we get close
        img = Image.blend(img, Image.new('RGB', (W, H), sh(0.5)[:3]), min(0.35, (v.z - 1.6) * 0.25))
    d = ImageDraw.Draw(img, 'RGBA')
    # glazing bars over it
    for x in range(160, 1820, 240):
        d.line([v.p(x, 40), v.p(x, 650)], fill=(46, 58, 50), width=v.w(8))
    for y in (60, 280, 500):
        d.line([v.p(140, y), v.p(1820, y)], fill=(46, 58, 50), width=v.w(8))
    x0, y0, x1, y1 = PANE                                  # the cracked pane
    d.line([v.p(x0 + 30, y0 + 10), v.p(x0 + 110, y0 + 110), v.p(x0 + 80, y1 - 10)], fill=(40, 48, 44), width=v.w(2))
    d.line([v.p(x0 + 110, y0 + 110), v.p(x1 - 10, y0 + 80)], fill=(40, 48, 44), width=v.w(2))
    # the pipe and tap; the handle turns a quarter
    d.line([v.p(TAP[0], -200), v.p(TAP[0], TAP[1])], fill=(84, 72, 52), width=v.w(10))
    d.line([v.p(TAP[0], TAP[1]), v.p(TAP[0] + 24, TAP[1] + 14)], fill=(164, 130, 64), width=v.w(9))
    ang = np.pi / 2 * ramp(t, *C.TAP_TURN)
    hx, hy = TAP[0], TAP[1] - 16
    d.line([v.p(hx - 22 * np.cos(ang), hy - 22 * np.sin(ang)), v.p(hx + 22 * np.cos(ang), hy + 22 * np.sin(ang))],
           fill=(180, 144, 72), width=v.w(7))
    s0, s1 = C.STREAM
    if s0 <= t <= s1:
        k = min(1, (t - s0) / 0.4, (s1 - t) / 0.6)
        d.line([v.p(TAP[0] + 25, TAP[1] + 16), v.p(TAP[0] + 25, POT_TAP[1] - 34)], fill=(206, 220, 226, int(210 * k)),
               width=v.w(3))

    def pot(x, y, sc=1.0, seed=0):
        """Terracotta: shaded body (lit from the right, where the dawn comes in), rim lip, soil, moss."""
        g = np.random.default_rng(int(x * 7 + seed))
        for k, col in enumerate(((128, 70, 46), (146, 82, 54), (160, 94, 62), (172, 104, 70))):
            f = k / 4
            xl, xr = -26 + 52 * f, -26 + 52 * (f + 0.25)
            d.polygon([v.p(x + xl * sc, y - 30 * sc), v.p(x + xr * sc, y - 30 * sc),
                       v.p(x + xr * 0.73 * sc, y + 30 * sc), v.p(x + xl * 0.73 * sc, y + 30 * sc)], fill=col)
        d.rectangle(v.box(x - 30 * sc, y - 36 * sc, x + 30 * sc, y - 24 * sc), fill=(168, 98, 64))
        d.rectangle(v.box(x - 30 * sc, y - 26 * sc, x + 30 * sc, y - 24 * sc), fill=(120, 66, 44))      # lip shadow
        d.rectangle(v.box(x - 24 * sc, y - 36 * sc, x + 24 * sc, y - 32 * sc), fill=(62, 46, 32))       # soil
        for _ in range(3):                                                                             # moss/lichen
            mx, my = x + g.uniform(-20, 20) * sc, y + g.uniform(-18, 26) * sc
            mr = g.uniform(3, 7) * sc
            d.ellipse(v.box(mx - mr, my - mr * 0.6, mx + mr, my + mr * 0.6), fill=(96, 112, 70, 200))
        if g.random() < 0.5:                                                                           # a dead stem
            d.line([v.p(x - 4 * sc, y - 34 * sc), v.p(x - 10 * sc, y - 70 * sc), v.p(x - 20 * sc, y - 64 * sc)],
                   fill=(110, 92, 62), width=v.w(2))
    pot(*POT_TAP)
    # the bench, the rail, the post
    for k in range(3):                                                  # planks with gaps, weathered
        y0 = BENCH_Y + k * 7.5
        d.rectangle(v.box(BENCH_X[0], y0, BENCH_X[1], y0 + 6.5), fill=(96 - 6 * k, 74 - 5 * k, 50 - 3 * k))
    for gx in range(BENCH_X[0] + 60, BENCH_X[1], 137):                  # grain streaks
        d.line([v.p(gx, BENCH_Y + 2), v.p(gx + 40, BENCH_Y + 2)], fill=(78, 60, 40), width=v.w(1))
    # old tools left on the bench: a trowel and a ball of twine
    d.polygon([v.p(1180, BENCH_Y - 2), v.p(1218, BENCH_Y - 8), v.p(1222, BENCH_Y - 2)], fill=(120, 126, 124))
    d.line([v.p(1160, BENCH_Y - 3), v.p(1182, BENCH_Y - 3)], fill=(110, 76, 44), width=v.w(4))
    d.ellipse(v.box(1236, BENCH_Y - 14, 1256, BENCH_Y), fill=(176, 150, 104))
    d.line([v.p(1240, BENCH_Y - 10), v.p(1252, BENCH_Y - 4)], fill=(150, 126, 86), width=v.w(1))
    d.line([v.p(BENCH_X[0], BENCH_Y + 3), v.p(BENCH_X[1], BENCH_Y + 3)], fill=(84, 112, 66), width=v.w(4))   # moss
    for lx in (620, 1370):
        d.rectangle(v.box(lx, BENCH_Y + 22, lx + 18, BENCH_Y + 300), fill=(72, 54, 38))
    d.rectangle(v.box(1330, 400, 1346, BENCH_Y), fill=(78, 60, 42))                                      # post
    d.rectangle(v.box(1060, RAIL_Y - 8, 1346, RAIL_Y + 4), fill=(96, 74, 52))                          # rail
    for hx_, hy_ in (HOOK_REAL, HOOK_REP):
        d.arc(v.box(hx_ - 7, hy_ - 2, hx_ + 7, hy_ + 14), 0, 200, fill=(60, 60, 64), width=v.w(3))
    for x, y in POTS:
        pot(x, y)
    nudge = ramp(t, *C.POT_NUDGE)
    pot(STRAY[0] - 40 * nudge, STRAY[1] + 6 * (1 - nudge))
    # the seedling that will be watered
    pot(*SEEDLING, 0.8)
    grow_up = ramp(t, C.POUR[1], C.TOTAL) * 10
    d.line([v.p(SEEDLING[0], SEEDLING[1] - 26), v.p(SEEDLING[0], SEEDLING[1] - 52 - grow_up)], fill=(96, 146, 72), width=v.w(3))
    d.ellipse(v.box(SEEDLING[0] - 12, SEEDLING[1] - 64 - grow_up, SEEDLING[0], SEEDLING[1] - 54 - grow_up), fill=(116, 166, 84))
    d.ellipse(v.box(SEEDLING[0], SEEDLING[1] - 62 - grow_up, SEEDLING[0] + 12, SEEDLING[1] - 52 - grow_up), fill=(116, 166, 84))
    # the real gloves, hanging where they were left: canvas, a darker cuff, seams, creases, soil
    GA.paste(img, v, GLOVE_SHADOW, HOOK_REAL[0] + 4, HOOK_REAL[1] + 6, GS)
    GA.paste(img, v, REAL_SPRITE, *HOOK_REAL, GS)
    # the watering can: lifted a centimetre and tipped by the replica
    reach = ramp(t, C.LIFT[0] - 4, C.LIFT[0])
    lift = ramp(t, *C.LIFT) * 12
    tilt = ramp(t, *C.POUR) * 0.3 * (1 - ramp(t, C.POUR[1], C.POUR[1] + 3))
    cxn, cyn = CAN[0], CAN[1] - lift

    def rot(x, y):
        dx, dy = x - cxn, y - cyn
        return v.p(cxn + dx * np.cos(tilt) - dy * np.sin(tilt), cyn + dx * np.sin(tilt) + dy * np.cos(tilt))
    # a galvanised can: ribbed body shaded round, rim, handle arch, long spout with a rose, a dent and a highlight
    for k, col in enumerate(((84, 96, 94), (100, 116, 112), (118, 134, 130), (134, 150, 146), (112, 128, 124))):
        xl, xr = -38 + 76 * k / 5, -38 + 76 * (k + 1) / 5
        d.polygon([rot(cxn + xl, cyn - 56), rot(cxn + xr, cyn - 56), rot(cxn + xr, cyn), rot(cxn + xl, cyn)], fill=col)
    for yy in (-44, -24):                                                                              # ribs
        d.line([rot(cxn - 38, cyn + yy), rot(cxn + 38, cyn + yy)], fill=(80, 92, 90), width=v.w(2))
    d.polygon([rot(cxn - 40, cyn - 60), rot(cxn + 40, cyn - 60), rot(cxn + 40, cyn - 54), rot(cxn - 40, cyn - 54)],
              fill=(146, 160, 156))                                                                    # rim
    d.ellipse([*rot(cxn - 20, cyn - 38), *rot(cxn - 8, cyn - 26)], fill=(90, 104, 100))                 # dent
    d.line([rot(cxn + 20, cyn - 52), rot(cxn + 20, cyn - 6)], fill=(196, 206, 200, 150), width=v.w(3))  # highlight
    d.line([rot(cxn + 36, cyn - 40), rot(cxn + 92, cyn - 82)], fill=(110, 126, 122), width=v.w(7))      # spout
    rose = [rot(cxn + 88, cyn - 88), rot(cxn + 104, cyn - 94), rot(cxn + 106, cyn - 78), rot(cxn + 92, cyn - 74)]
    d.polygon(rose, fill=(126, 140, 136))                                                              # the rose
    # handle: an arch whose feet sit on the rim, built from rotated points so it tips with the can
    # (v4 fix: the old d.arc box didn't rotate, and its ends floated 12 px above the rim)
    hand = [rot(cxn + 26 * np.cos(a), cyn - 58 - 40 * np.sin(a)) for a in np.linspace(0, np.pi, 24)]
    d.line(hand, fill=(104, 120, 116), width=v.w(6), joint="curve")
    if C.POUR[0] + 0.6 < t < C.POUR[1]:
        a = rot(cxn + 102, cyn - 84)
        for k in range(7):
            yy = a[1] + v.w(10 + 14 * k + 20 * ((t * 3 + k * 0.29) % 1))
            d.ellipse([a[0] - v.w(2), yy - v.w(3), a[0] + v.w(2), yy + v.w(3)], fill=(206, 220, 228, 210))
    # all growth, revealed as it's born
    palm_y = HOOK_REP[1] + 90 * GS
    tip_y = HOOK_REP[1] + 290 * GS
    stretch_amt = 70 * reach

    def stretch(y):
        """Rows below the palm move down progressively (a stretch, not a break); everything below the palm lifts."""
        k = np.clip((np.asarray(y, float) - palm_y) / (tip_y - palm_y), 0, 1)
        return stretch_amt * k - lift * (np.asarray(y, float) > palm_y)

    rep_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for name, G in GROWTHS.items():
        if name == 'replica':
            continue                                          # v5: the replica is painted by glove_art
        vis = G['bt'] <= t
        if not vis.any():
            continue
        dd = ImageDraw.Draw(rep_layer, 'RGBA') if name == 'replica' else d
        pos = G['pos'].copy()
        if name == 'replica':
            pos[:, 1] += stretch(pos[:, 1])                   # the leafy fingers lengthen to the handle, then lift
        for i in np.nonzero(vis)[0]:
            p = G['parent'][i]
            if p < 0:
                continue
            dd.line([v.p(*pos[p]), v.p(*pos[i])], fill=(58, 96, 54, 255), width=v.w(G['th'][i] * 0.9))
        tips = np.nonzero(vis & (G['th'] < 0.9))[0]
        for i in tips[::1 if name == 'replica' else 2]:
            x, y = pos[i]
            age = min(1, (t - G['bt'][i]) / 1.5)
            r = (5 if name == 'replica' else 4) * age
            col = (96, 148, 74, 255) if (i * 7) % 3 else (122, 170, 88, 255)
            dd.polygon(leaf_poly(x, y, r * 1.4, i * 0.7, v), fill=col)
    # v5: the replica, painted leaf by leaf, growing from the cuff down; it stretches to the handle, then lifts
    u = ramp(t, *C.REPLICA)
    if u > 0:
        spr = GA.replica_sprite(u, t)
        rows = np.arange(GA.SH, dtype=float)
        world_y = HOOK_REP[1] + (GA.Y0 + rows / GA.PX) * GS
        dy = stretch(world_y) / GS * GA.PX
        GA.paste(img, v, GLOVE_SHADOW, HOOK_REP[0] + 4, HOOK_REP[1] + 6, GS, dy_rows=dy) if u > 0.6 else None
        GA.paste(img, v, spr, *HOOK_REP, GS, dy_rows=dy)
        d = ImageDraw.Draw(img, 'RGBA')
    # floor: fallen leaves
    d.rectangle(v.box(-400, BENCH_Y + 300, 2320, 1500), fill=(56, 50, 42))
    for (x, y, r, col, ang) in FLOOR_LEAVES:
        d.polygon(leaf_poly(x, y, r, ang * 0.3, v), fill=col)
    pot(*POT_TAP)                                           # (in front of the floor)
    # light shafts from the upper right, stronger at dawn; dust in them
    shafts = Image.new('L', (W, H), 0)
    sd = ImageDraw.Draw(shafts)
    for k, off in enumerate((0, 260, 470)):
        sd.polygon([v.p(1500 + off, -100), v.p(1640 + off, -100), v.p(900 + off, 1100), v.p(760 + off, 1100)],
                   fill=int(40 + 50 * dawn + 10 * np.sin(t * 0.3 + k)))
    shafts = shafts.filter(ImageFilter.GaussianBlur(v.w(30)))
    warm = Image.new('RGB', (W, H), (255, 236, 196))
    img = Image.composite(warm, img, shafts.point(lambda q: int(q * 0.55)))
    d = ImageDraw.Draw(img, 'RGBA')
    for i, (mx, my) in enumerate(MOTES):
        x = mx + 30 * np.sin(t * 0.21 + i)
        y = (my + t * (4 + i % 5)) % 900
        a, b = v.p(x, y), v.p(x + 2, y + 2)
        d.ellipse([a[0], a[1], b[0], b[1]], fill=(255, 245, 225, 90))
    arr = np.asarray(img).astype(np.float32)
    Y, X = np.ogrid[:H, :W]
    vig = 1 - 0.38 * (((X - W / 2) / (W / 2)) ** 2 + ((Y - H / 2) / (H / 2)) ** 2)
    arr *= np.clip(vig, 0.4, 1)[..., None]
    arr += np.random.default_rng(int(t * FPS)).normal(0, 3, (H, W, 1))
    fade = min(1, t / 2.5, (C.TOTAL - t) / 3)
    return np.clip(arr * max(fade, 0), 0, 255).astype(np.uint8)


def glove_details(d, v, hx, hy):
    """Detail over the flat glove mask (same geometry as glove_mask): cuff band, stitched seams, knuckle
    creases, soil stains on the fingertips and palm."""
    s = GS
    x0 = hx - 75 * s
    d.rectangle(v.box(x0 + 5 * s, hy + 8 * s, x0 + 145 * s, hy + 72 * s), fill=(150, 132, 98, 235))     # cuff band
    for yy in (hy + 20 * s, hy + 60 * s):                                                           # cuff stitching
        pts = np.linspace(x0 + 10 * s, x0 + 140 * s, 14)
        for a, b in zip(pts[::2], pts[1::2]):
            d.line([v.p(a, yy), v.p(b, yy)], fill=(108, 92, 66), width=v.w(1))
    d.line([v.p(x0 + 5 * s, hy + 74 * s), v.p(x0 + 145 * s, hy + 74 * s)], fill=(120, 104, 76), width=v.w(2))
    for k, L in enumerate([66, 88, 96, 80]):
        fx = x0 + (4 + k * 36) * s
        cx = fx + 16.5 * s
        top, bot = hy + 172 * s, hy + (190 + L) * s
        d.line([v.p(cx, top), v.p(cx, bot - 8 * s)], fill=(160, 142, 108), width=v.w(1))              # finger seam
        for kn in (0.35, 0.65):                                                                      # knuckle creases
            yk = top + (bot - top) * kn
            d.arc(v.box(fx + 6 * s, yk - 3 * s, fx + 27 * s, yk + 5 * s), 200, 340, fill=(150, 132, 100), width=v.w(1))
        d.ellipse(v.box(fx + 4 * s, bot - 20 * s, fx + 29 * s, bot - 1 * s), fill=(110, 86, 58, 170))  # soil on the tip
    d.ellipse(v.box(x0 + 40 * s, hy + 120 * s, x0 + 100 * s, hy + 168 * s), fill=(128, 104, 72, 110))   # worn palm
    d.line([v.p(x0 + 140 * s, hy + 112 * s), v.p(x0 + 196 * s, hy + 128 * s)], fill=(160, 142, 108), width=v.w(1))


def draw_mask(img, mask_img, v, col):
    bb = mask_img.getbbox()
    if not bb:
        return
    a, b = v.p(bb[0], bb[1]), v.p(bb[2], bb[3])
    w, h = int(b[0] - a[0]), int(b[1] - a[1])
    if w < 2 or h < 2:
        return
    m = mask_img.crop(bb).resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.8))
    img.paste(col, (int(a[0]), int(a[1])), m)


if __name__ == '__main__':
    out = sys.argv[1]
    t0, t1 = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (0, C.TOTAL)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-threads', '2', '-pix_fmt', 'yuv420p', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(t0 * FPS), int(t1 * FPS)):
        p.stdin.write(draw_frame(i / FPS).tobytes())
        if i % 300 == 0:
            print('frame', i, flush=True)
    p.stdin.close()
    p.wait()
