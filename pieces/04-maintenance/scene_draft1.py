"""Maintenance: the picture. Vector-drawn in screen space so the camera can push in crisply.

World coordinates are a 1920x1080 view of the whole glasshouse at zoom 1.
usage: python scene.py OUT.mp4 [t0 t1]
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import cues as C
from growth import Growth, sample_mask

W, H, FPS = 1920, 1080, 30
rng = np.random.default_rng(44)

# camera path: (time, centre x, centre y, zoom)
CAMERA = [(0, 960, 540, 1.0), (12, 960, 540, 1.05), (18, 640, 560, 1.7), (33, 640, 580, 1.9), (37, 900, 560, 1.5),
          (54, 980, 520, 1.45), (60, 1120, 700, 2.6), (86, 1110, 690, 3.1), (104, 1110, 690, 3.3),
          (112, 1160, 670, 3.0), (130, 1160, 670, 3.1), (140, 1160, 670, 3.15)]


def ease(a):
    return a * a * (3 - 2 * a)


def camera(t):
    ts = [k[0] for k in CAMERA]
    i = int(np.clip(np.searchsorted(ts, t, side='right') - 1, 0, len(ts) - 2))
    a = ease(np.clip((t - ts[i]) / (ts[i + 1] - ts[i]), 0, 1))
    k0, k1 = np.array(CAMERA[i][1:]), np.array(CAMERA[i + 1][1:])
    cx, cy, z = k0 + (k1 - k0) * a
    return cx, cy, z


def ramp(t, a, b):
    return float(ease(np.clip((t - a) / (b - a), 0, 1)))


# ------------------------------------------------------------------ world objects
TAP = (560, 470)
POT_TAP = (560, 640)
BENCH_Y = 760
POTS = [(700 + 62 * k, BENCH_Y - 34) for k in range(5)]
STRAY = (700 + 62 * 5 + 40, BENCH_Y - 34)          # one pot out of line
PANE = (1250, 250, 1400, 420)                      # the cracked pane
STOOL = (1180, 900)
GLOVES = (1150, 840)                               # the real gloves, on the stool
REPLICA = (1035, 842)                              # where the replica grows, beside them on the bench end
CAN = (1265, 835)


def glove_mask(ox, oy, s=0.42, flip=False, size=(1920, 1080)):
    im = Image.new('L', size, 0)
    d = ImageDraw.Draw(im)
    f = -1 if flip else 1

    def X(v):
        return ox + f * v * s

    d.rounded_rectangle(sorted([X(0), X(150)]) and [min(X(0), X(150)), oy, max(X(0), X(150)), oy + 120 * s],
                        radius=int(30 * s), fill=255)
    for k, L in enumerate([110, 130, 122, 92]):
        a, b = X(12 + k * 34), X(40 + k * 34)
        d.rounded_rectangle([min(a, b), oy - L * s, max(a, b), oy + 20 * s], radius=int(14 * s), fill=255)
    a, b = X(-60), X(10)
    d.rounded_rectangle([min(a, b), oy + 20 * s, max(a, b), oy + 60 * s], radius=int(20 * s), fill=255)
    a, b = X(5), X(145)
    d.rectangle([min(a, b), oy + 120 * s, max(a, b), oy + 185 * s], fill=255)
    return np.asarray(im) > 0


def build_growths():
    g = {}
    # 1: from the tap's pot up to the handle, wrapping it
    at = np.vstack([np.column_stack([np.full(40, TAP[0] + 8) + rng.normal(0, 10, 40), np.linspace(630, 480, 40)]),
                    np.column_stack([TAP[0] + 30 + 22 * np.cos(np.linspace(0, 5, 50)), TAP[1] + 22 * np.sin(np.linspace(0, 5, 50))])])
    g['tap'] = (Growth([(POT_TAP[0] + 10, POT_TAP[1] - 20)], at, step=3, influence=70, kill=5, seed=1), 15.0, C.TAP_TURN[0])
    # 2: along the bench to the stray pot
    at = np.column_stack([np.linspace(POTS[0][0], STRAY[0] + 10, 90), BENCH_Y - 8 + rng.normal(0, 4, 90)])
    g['pot'] = (Growth([(POTS[0][0] - 20, BENCH_Y - 4)], at, step=4, influence=60, kill=6, seed=2), 33.0, C.POT_NUDGE[0])
    # 3: up the frame to prop the cracked pane
    at = np.column_stack([np.full(80, PANE[0] - 14) + rng.normal(0, 6, 80), np.linspace(BENCH_Y - 60, PANE[3] - 10, 80)])
    g['pane'] = (Growth([(PANE[0] - 20, BENCH_Y - 40)], at, step=4, influence=70, kill=6, seed=3), 40.0, C.PANE_PROP[1])
    # 4: from the stool leg up to the gloves, then along the bench into the replica shape
    real = glove_mask(*GLOVES)
    rep = glove_mask(*REPLICA, flip=True)
    at = np.vstack([np.column_stack([np.full(50, STOOL[0] - 40) + rng.normal(0, 8, 50), np.linspace(1060, 880, 50)]),
                    sample_mask(real, 160, rng)])
    g['find'] = (Growth([(STOOL[0] - 40, 1075)], at, step=4, influence=70, kill=6, seed=4), 50.0, C.GLOVE_FIND)
    at = sample_mask(rep, 1600, rng)
    g['replica'] = (Growth([(GLOVES[0] - 30, GLOVES[1] + 60)], at, step=2.5, influence=60, kill=4, seed=5), *C.REPLICA)
    out = {}
    for k, (gr, t0, t1) in g.items():
        while gr.grow():
            pass
        th = gr.thickness(0.5, 0.42)
        born = np.array(gr.born, float)
        bt = t0 + (t1 - t0) * born / max(born.max(), 1)
        out[k] = dict(pos=np.array(gr.pos), parent=np.array(gr.parent), th=th, bt=bt)
    return out, real, rep


GROWTHS, REAL_MASK, REP_MASK = build_growths()


# ------------------------------------------------------------------ drawing
class View:
    def __init__(self, t):
        self.cx, self.cy, self.z = camera(t)

    def p(self, x, y):
        return (W / 2 + (x - self.cx) * self.z, H / 2 + (y - self.cy) * self.z)

    def box(self, x0, y0, x1, y1):
        a, b = self.p(x0, y0), self.p(x1, y1)
        return [a[0], a[1], b[0], b[1]]

    def s(self, v):
        return v * self.z


def light(t):
    """Grey dawn, warming at the end."""
    w = ramp(t, *C.DAWN)
    cool, warm = np.array([150, 160, 158]), np.array([214, 196, 160])
    return cool * (1 - w) + warm * w


def draw_frame(t):
    v = View(t)
    base = light(t)
    img = Image.new('RGB', (W, H), tuple(int(c * 0.5) for c in base))
    d = ImageDraw.Draw(img, 'RGBA')
    # back wall and floor
    d.rectangle(v.box(-400, -400, 2320, BENCH_Y + 40), fill=tuple(int(c * 0.62) for c in base))
    d.rectangle(v.box(-400, BENCH_Y + 140, 2320, 1500), fill=(58, 54, 46))
    # glass panes behind (soft light), mullions
    for x in range(160, 1800, 240):
        for y in range(60, 700, 220):
            d.rectangle(v.box(x + 6, y + 6, x + 234, y + 214), fill=tuple(int(min(255, c * 0.8)) for c in base) + (255,))
    for x in range(160, 1820, 240):
        d.line([v.p(x, 40), v.p(x, BENCH_Y + 40)], fill=(52, 64, 56), width=max(2, int(v.s(8))))
    for y in range(60, 720, 220):
        d.line([v.p(140, y), v.p(1820, y)], fill=(52, 64, 56), width=max(2, int(v.s(8))))
    # the cracked pane
    x0, y0, x1, y1 = PANE
    d.line([v.p(x0 + 20, y0 + 10), v.p(x0 + 80, y0 + 90), v.p(x0 + 60, y1 - 20)], fill=(70, 80, 76), width=max(1, int(v.s(2))))
    d.line([v.p(x0 + 80, y0 + 90), v.p(x1 - 10, y0 + 70)], fill=(70, 80, 76), width=max(1, int(v.s(2))))
    # the tap on its pipe; its handle turns a quarter
    d.line([v.p(TAP[0], 40), v.p(TAP[0], TAP[1])], fill=(80, 70, 50), width=max(2, int(v.s(10))))
    d.line([v.p(TAP[0], TAP[1]), v.p(TAP[0] + 22, TAP[1] + 12)], fill=(160, 126, 60), width=max(2, int(v.s(9))))
    ang = np.pi / 2 * ramp(t, *C.TAP_TURN)
    hx, hy = TAP[0], TAP[1] - 16
    d.line([v.p(hx - 22 * np.cos(ang), hy - 22 * np.sin(ang)), v.p(hx + 22 * np.cos(ang), hy + 22 * np.sin(ang))],
           fill=(176, 140, 70), width=max(2, int(v.s(7))))
    s0, s1 = C.STREAM
    if s0 <= t <= s1:
        k = min(1, (t - s0) / 0.4, (s1 - t) / 0.6)
        d.line([v.p(TAP[0] + 24, TAP[1] + 14), v.p(TAP[0] + 24, POT_TAP[1] - 30)], fill=(200, 215, 220, int(200 * k)),
               width=max(1, int(v.s(3))))
    # pots: the tap's pot, the row, the stray one nudged into line
    def pot(x, y, sc=1.0):
        d.polygon([v.p(x - 26 * sc, y - 30 * sc), v.p(x + 26 * sc, y - 30 * sc), v.p(x + 19 * sc, y + 30 * sc),
                   v.p(x - 19 * sc, y + 30 * sc)], fill=(150, 84, 54))
        d.rectangle(v.box(x - 29 * sc, y - 34 * sc, x + 29 * sc, y - 24 * sc), fill=(164, 94, 60))
    pot(*POT_TAP)
    d.rectangle(v.box(640, BENCH_Y, 1120, BENCH_Y + 22), fill=(92, 70, 48))          # the bench top
    for lx in (660, 1090):
        d.rectangle(v.box(lx, BENCH_Y + 22, lx + 18, BENCH_Y + 140), fill=(72, 54, 38))
    for x, y in POTS:
        pot(x, y)
    nudge = ramp(t, *C.POT_NUDGE)
    pot(STRAY[0] - 40 * nudge, STRAY[1] + 8 * (1 - nudge))
    # the stool, the real gloves, the can (which the replica lifts)
    sx, sy = STOOL
    d.rectangle(v.box(sx - 70, sy - 20, sx + 70, sy), fill=(96, 72, 50))
    for lx in (sx - 60, sx + 50):
        d.line([v.p(lx, sy), v.p(lx + (8 if lx > sx else -8), 1075)], fill=(80, 60, 42), width=max(2, int(v.s(8))))
    lift = ramp(t, *C.LIFT) * 10
    tilt = ramp(t, *C.POUR) * 0.35 * (1 - ramp(t, C.POUR[1], C.POUR[1] + 3))
    cxn, cyn = CAN[0], CAN[1] - lift

    def rot(x, y):
        dx, dy = x - cxn, y - cyn
        return v.p(cxn + dx * np.cos(-tilt) - dy * np.sin(-tilt), cyn + dx * np.sin(-tilt) + dy * np.cos(-tilt))
    body = [rot(cxn - 40, cyn - 55), rot(cxn + 40, cyn - 55), rot(cxn + 40, cyn + 5), rot(cxn - 40, cyn + 5)]
    d.polygon(body, fill=(100, 116, 110))
    d.line([rot(cxn - 40, cyn - 40), rot(cxn - 95, cyn - 75)], fill=(100, 116, 110), width=max(2, int(v.s(8))))
    if t > C.POUR[0] + 0.5 and t < C.POUR[1]:
        a = rot(cxn - 95, cyn - 75)
        for k in range(6):
            yy = a[1] + v.s(20 + 25 * k + 40 * ((t * 3 + k * 0.3) % 1))
            d.ellipse([a[0] - v.s(2), yy - v.s(3), a[0] + v.s(2), yy + v.s(3)], fill=(200, 215, 222, 200))
    # the seedling that receives the water
    sdx, sdy = CAN[0] - 120, BENCH_Y + 132
    d.line([v.p(sdx, sdy), v.p(sdx, sdy - 30 - 8 * ramp(t, C.POUR[1], C.TOTAL))], fill=(92, 140, 70), width=max(1, int(v.s(3))))
    d.ellipse(v.box(sdx - 10, sdy - 44, sdx, sdy - 34), fill=(110, 160, 80))
    # the real gloves: canvas, flat colour
    gm = Image.fromarray((REAL_MASK * 255).astype(np.uint8))
    draw_mask(img, gm, v, (196, 180, 140))
    # all growth, revealed as it is born
    lift_off = np.array([0, -lift])
    for name, G in GROWTHS.items():
        vis = G['bt'] <= t
        if not vis.any():
            continue
        pos = G['pos'].copy()
        if name == 'replica' and t > C.LIFT[0]:
            inside = pos[:, 0] < GLOVES[0] - 60                 # the replica's hand moves with the can
            pos[inside] += lift_off
        for i in np.nonzero(vis)[0]:
            p = G['parent'][i]
            if p < 0:
                continue
            w = max(1, int(v.s(G['th'][i] * 0.9)))
            d.line([v.p(*pos[p]), v.p(*pos[i])], fill=(64, 102, 58), width=w)
        # leaves on the young tips
        tips = np.nonzero(vis & (G['th'] < 0.9))[0]
        for i in tips[::2 if name != 'replica' else 1]:
            x, y = pos[i]
            age = min(1, (t - G['bt'][i]) / 1.5)
            r = (4 if name != 'replica' else 5.5) * age
            col = (98, 150, 76) if (i * 7) % 3 else (120, 170, 88)
            d.ellipse(v.box(x - r * 1.3, y - r, x + r * 1.3, y + r), fill=col)
    # vignette and grain
    arr = np.asarray(img).astype(np.float32)
    Y, X = np.ogrid[:H, :W]
    vig = 1 - 0.35 * (((X - W / 2) / (W / 2)) ** 2 + ((Y - H / 2) / (H / 2)) ** 2)
    arr *= np.clip(vig, 0.4, 1)[..., None]
    arr += rng.normal(0, 3, (H, W, 1))
    return np.clip(arr, 0, 255).astype(np.uint8)


def draw_mask(img, mask_img, v, col):
    """Draw a world-space mask (glove) through the camera transform."""
    x0, y0 = v.p(0, 0)
    size = (int(1920 * v.z), int(1080 * v.z))
    if size[0] < 2:
        return
    bb = mask_img.getbbox()
    if not bb:
        return
    crop = mask_img.crop(bb)
    a, b = v.p(bb[0], bb[1]), v.p(bb[2], bb[3])
    w, h = int(b[0] - a[0]), int(b[1] - a[1])
    if w < 2 or h < 2:
        return
    m = crop.resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.8))
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
