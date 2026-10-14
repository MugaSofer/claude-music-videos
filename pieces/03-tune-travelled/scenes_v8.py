"""Scene art (background strips) and thread materials for each keeper."""
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

THREAD_Y = dict(shepherd=560, monks=560, sailors=600, musicbox=600, parlour=560, radio=600, phone=600, kitchen=520,
                child=560)
THREAD_SPAN = dict(shepherd=300, monks=240, sailors=260, musicbox=240, parlour=260, radio=260, phone=260,
                   kitchen=280, child=160)
PEN_COLOR = dict(shepherd=(255, 250, 235), monks=(200, 40, 30), sailors=(250, 240, 220), musicbox=(255, 220, 140),
                 parlour=(40, 30, 25), radio=(250, 245, 230), phone=(120, 255, 200), kitchen=(255, 225, 170),
                 child=(90, 90, 100))


def hexf(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def noise1d(n, scale, seed, octaves=4):
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    amp = 1.0
    for o in range(octaves):
        k = max(int(n / scale * 2 ** o) + 2, 2)
        pts = rng.uniform(-1, 1, k)
        out += amp * np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
        amp *= 0.5
    return out / 1.9


def paper(h, w, base, seed, grain=0.035, fibres=True):
    rng = np.random.default_rng(seed)
    g = gaussian_filter(rng.standard_normal((-(-h // 4), -(-w // 4))), 1.2)
    g = np.kron(g, np.ones((4, 4)))[:h, :w]
    fine = rng.standard_normal((h, w)) * 0.35
    tex = (g * 0.8 + fine) * grain
    img = np.broadcast_to(base, (h, w, 3)).astype(np.float32).copy()
    img += tex[..., None].astype(np.float32)
    return img


def wash_layer(img, top_curve, color, alpha, soft, seed, bleed=True):
    """An ink-wash silhouette: filled below top_curve, darker at its edge (pigment pools at the wet edge)."""
    h, w, _ = img.shape
    Y = np.arange(h)[:, None]
    d = Y - top_curve[None, :]
    body = np.clip(d / soft + 0.5, 0, 1)
    edge = np.exp(-(d / (soft * 3)) ** 2) * (d > -soft) * 0.5 if bleed else 0
    rng = np.random.default_rng(seed)
    blot = gaussian_filter(rng.standard_normal((-(-h // 8), -(-w // 8))), 2)
    blot = np.kron(blot, np.ones((8, 8)))[:h, :w] * 0.25
    a = np.clip((body * (0.75 + blot) + edge) * alpha, 0, 1)[..., None]
    img *= (1 - a)
    img += a * color
    return img


# ------------------------------------------------------------------ painting toolkit for the figures
def closed_curve(pts, per=8):
    """Closed Catmull-Rom through the points."""
    P = np.array(pts, float)
    n = len(P)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % n], P[(i + 2) % n]
        for tt in np.linspace(0, 1, per, endpoint=False):
            t2, t3 = tt * tt, tt * tt * tt
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * tt + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    return out


def col3(c):
    return np.asarray(c, np.float32)


class Painter:
    """Antialiased masks drawn in strip coordinates on a local patch of a float image, and paint through them."""

    def __init__(self, img, box, ss=3):
        H, W, _ = img.shape
        self.x0, self.y0 = max(int(box[0]), 0), max(int(box[1]), 0)
        x1, y1 = min(int(box[2]), W), min(int(box[3]), H)
        self.w, self.h = max(x1 - self.x0, 1), max(y1 - self.y0, 1)
        self.img, self.ss = img, ss
        yy, xx = np.mgrid[self.y0:self.y0 + self.h, self.x0:self.x0 + self.w]
        self.X, self.Y = xx.astype(np.float32), yy.astype(np.float32)

    @property
    def view(self):
        return self.img[self.y0:self.y0 + self.h, self.x0:self.x0 + self.w]

    def _canvas(self):
        im = Image.new('L', (self.w * self.ss, self.h * self.ss), 0)
        return im, ImageDraw.Draw(im)

    def _tp(self, pts):
        s = self.ss
        return [((x - self.x0) * s, (y - self.y0) * s) for x, y in pts]

    def _m(self, im):
        return np.asarray(im.resize((self.w, self.h), Image.BOX), np.float32) / 255

    def poly(self, pts, smooth=True, per=8):
        if smooth:
            pts = closed_curve(pts, per)
        im, d = self._canvas()
        d.polygon(self._tp(pts), fill=255)
        return self._m(im)

    def ellipse(self, cx, cy, rx, ry, rot=0.0):
        a = np.linspace(0, 2 * np.pi, 72, endpoint=False)
        c, s = np.cos(rot), np.sin(rot)
        pts = [(cx + rx * np.cos(t) * c - ry * np.sin(t) * s, cy + rx * np.cos(t) * s + ry * np.sin(t) * c) for t in a]
        return self.poly(pts, smooth=False)

    def stroke(self, pts, w0, w1=None, smooth=True, caps=True):
        """A brush stroke through pts whose width goes from w0 to w1."""
        if smooth and len(pts) > 2:
            pts = smooth_curve(pts, 10)
        P = np.array(pts, float)
        wid = np.linspace(w0, w0 if w1 is None else w1, len(P))[:, None]
        T = np.gradient(P, axis=0)
        T /= np.hypot(T[:, 0], T[:, 1])[:, None] + 1e-9
        N = np.stack([-T[:, 1], T[:, 0]], 1)
        L, R = P + N * wid / 2, P - N * wid / 2
        im, d = self._canvas()
        d.polygon(self._tp([tuple(p) for p in L] + [tuple(p) for p in R[::-1]]), fill=255)
        if caps:
            for p, r in ((P[0], wid[0, 0] / 2), (P[-1], wid[-1, 0] / 2)):
                (cx, cy), = self._tp([tuple(p)])
                d.ellipse([cx - r * self.ss, cy - r * self.ss, cx + r * self.ss, cy + r * self.ss], fill=255)
        return self._m(im)

    def paint(self, m, col, alpha=1.0):
        a = np.clip(m * alpha, 0, 1)[..., None]
        v = self.view
        v *= (1 - a)
        v += a * (col3(col) if np.ndim(col) == 1 else col)

    def add(self, m, col, k=1.0):
        self.view[...] += (m * k)[..., None] * col3(col)

    def edge(self, m, s=1.2):
        """The inner rim band of a mask (for outlines and wet edges)."""
        return np.clip((m - gaussian_filter(m, s)) * 2.5, 0, 1)

    def ink(self, m, col, alpha=0.85, edge=0.5, seed=0, tex=0.35, grain=9.0, fade=None, bleed=0.06):
        """Ink wash through a mask: a slow tonal wander, fine pigment granulation, pigment pooled at the wet edge,
        a faint bleed into the paper around it. fade=(y_top, y_bottom) lightens the wash downwards."""
        rng = np.random.default_rng(seed)
        nz = gaussian_filter(rng.standard_normal((self.h, self.w)), grain)
        nz /= nz.std() + 1e-6
        gr = gaussian_filter(rng.standard_normal((self.h, self.w)), 0.7)
        gr /= gr.std() + 1e-6
        m = gaussian_filter(m, 0.45)
        body = alpha * (1 - tex * 0.4 + tex * 0.2 * nz + 0.06 * gr)
        if fade is not None:
            body = body * np.clip(1 - 0.45 * (self.Y - fade[0]) / (fade[1] - fade[0]), 0.5, 1)
        a = m * body + self.edge(m, 2.0) * edge * alpha
        if bleed:
            a = np.maximum(a, gaussian_filter(m, 3.5) * bleed * alpha)
        self.paint(np.clip(a, 0, 1), col)

    def lit(self, m, dark, light, lamps, amb=0.12, rim=0.9, vol=0.55, s=7.0, tex=None):
        """Paint a form lit by warm point lights: a soft volume term plus a rim on the edges facing each light."""
        gb = gaussian_filter(m, s)
        gy, gx = np.gradient(gb)
        nx, ny = -gx * s * 2.5, -gy * s * 2.5
        dome = np.clip(gaussian_filter(m, s * 2) * 1.6 - 0.3, 0, 1)
        k = np.full(m.shape, amb, np.float32)
        for lx, ly, R, st in lamps:
            dx, dy = lx - self.X, ly - self.Y
            dist = np.hypot(dx, dy) + 1e-3
            fall = st / (1 + (dist / R) ** 2)
            facing = np.clip((nx * dx + ny * dy) / dist, -1, 1)
            k += fall * (vol * (0.45 + 0.55 * dome) + rim * np.clip(facing, 0, 1) - 0.25 * np.clip(-facing, 0, 1))
        if tex is not None:
            k *= tex
        k = np.clip(k, 0, 1.15)[..., None]
        self.paint(m, col3(dark) + (col3(light) - col3(dark)) * k)

    def glow(self, x, y, R, col, k):
        d2 = ((self.X - x) ** 2 + (self.Y - y) ** 2) / R ** 2
        self.add(np.exp(-d2), col, k)

    def polys(self, many, smooth=False):
        """Many polygons into one mask."""
        im, d = self._canvas()
        for pts in many:
            d.polygon(self._tp(closed_curve(pts, 6) if smooth else pts), fill=255)
        return self._m(im)


def glow(img, x, y, R, col, k):
    Painter(img, (x - 3 * R, y - 3 * R, x + 3 * R, y + 3 * R), ss=1).glow(x, y, R, col, k)


def rot_pts(pts, cx, cy, ang, ox=0.0, oy=0.0):
    """Rotate local points (about the local origin) by ang radians and move them to (cx, cy)."""
    c, s = np.cos(ang), np.sin(ang)
    return [(cx + (x - ox) * c - (y - oy) * s, cy + (x - ox) * s + (y - oy) * c) for x, y in pts]


# ------------------------------------------------------------------ shepherd: ink wash hills
INK = (0.17, 0.18, 0.2)
WASH = (0.3, 0.32, 0.35)
PAPER = (0.93, 0.9, 0.84)


def _sheep(img, x, y, s, seed, face):
    """A woolly ink-wash sheep: paper-pale fleece with a grey wet edge, dark face and legs. face = +1 / -1."""
    rng = np.random.default_rng(seed)
    P = Painter(img, (x - 34 * s, y - 26 * s, x + 34 * s, y + 22 * s))
    graze = rng.random() < 0.45
    legs = np.maximum.reduce([P.stroke([(x + u * s, y + 4 * s), (x + (u + rng.uniform(-1, 1)) * s, y + 14 * s)],
                                       2.6 * s, 2.0 * s) for u in (-10, -5, 6, 11)])
    P.ink(legs, INK, 0.85, 0.2, seed, tex=0.2)
    puffs = [P.ellipse(x, y - 1 * s, 16 * s, 9 * s)]
    for k in range(9):
        a = np.pi * (0.95 + 1.1 * k / 8)
        puffs.append(P.ellipse(x + 13 * s * np.cos(a) * -1, y - 1 * s + 7.5 * s * np.sin(a),
                               rng.uniform(4.5, 6.5) * s, rng.uniform(4, 5.5) * s))
    body = np.clip(np.maximum.reduce(puffs), 0, 1)
    P.paint(body, (0.9, 0.88, 0.82), 0.97)
    under = body * np.clip((P.Y - (y - 2 * s)) / (9 * s), 0, 1)
    P.ink(under, WASH, 0.35, 0.0, seed + 1, tex=0.5)
    P.ink(body, WASH, 0.0, 0.9, seed + 2, tex=0.0)
    hx, hy = x + face * 16 * s, y + (5 if graze else -5) * s
    head = P.ellipse(hx, hy, 5.2 * s, 3.6 * s, rot=face * (0.9 if graze else -0.35))
    ear = P.ellipse(hx - face * 3.5 * s, hy - 3 * s, 2.8 * s, 1.3 * s, rot=-face * 0.5)
    P.ink(np.maximum(head, ear), INK, 0.9, 0.3, seed + 3, tex=0.15)


def _shepherd(img, sx, sy, S=1.2):
    """A hooded, cloaked shepherd facing right, head raised to whistle, with a crook; a collie sits at his feet."""
    def F(pts):
        return [(sx + u * S, sy + v * S) for u, v in pts]
    P = Painter(img, (sx - 120 * S, sy - 320 * S, sx + 160 * S, sy + 14 * S))
    # legs and boots
    legs = np.maximum(P.stroke(F([(3, -34), (2, -18), (5, -4)]), 8 * S, 7 * S),
                      P.stroke(F([(14, -34), (17, -18), (20, -4)]), 8 * S, 7 * S))
    boots = np.maximum(P.ellipse(*F([(9, -3)])[0], 9.5 * S, 4.5 * S), P.ellipse(*F([(24, -3)])[0], 9.5 * S, 4.5 * S))
    P.ink(np.maximum(legs, boots), INK, 0.9, 0.3, 31, tex=0.2)
    # the crook, held out in front: a slightly knotted stick, darker where the brush pressed
    staff = P.stroke(F([(52, 3), (47, -60), (44, -140), (41, -268)]), 4.6 * S, 3.0 * S)
    curl = P.stroke(F([(41, -266), (40, -283), (47, -294), (57, -293), (61, -284), (57, -275)]), 3.4 * S, 2.2 * S)
    P.ink(np.maximum(staff, curl), INK, 0.92, 0.35, 32, tex=0.25)
    # the cloak, blowing back in the hill wind
    cloak = P.poly(F([(10, -214), (19, -196), (22, -150), (24, -100), (22, -56), (20, -30), (8, -24), (-4, -28),
                      (-18, -20), (-32, -27), (-48, -20), (-62, -28), (-80, -22), (-72, -48), (-56, -104),
                      (-40, -158), (-24, -198), (-10, -214)]))
    P.ink(cloak, (0.22, 0.235, 0.26), 0.97, 0.6, 33, tex=0.18, grain=16, fade=(sy - 150 * S, sy + 60 * S))
    folds = np.maximum.reduce([P.stroke(F(p), 2.4 * S, 0.5 * S) for p in (
        [(-6, -198), (-20, -140), (-40, -80), (-60, -32)],
        [(4, -186), (-2, -120), (-10, -60), (-16, -26)],
        [(-16, -176), (-32, -116), (-46, -64), (-50, -28)],
        [(14, -150), (14, -90), (10, -30)])])
    P.ink(folds * cloak, INK, 0.5, 0.0, 34, tex=0.3, bleed=0)
    # satchel on its strap
    strap = P.stroke(F([(12, -198), (-2, -160), (-16, -122)]), 2.4 * S)
    bag = P.poly(F([(-26, -124), (-6, -126), (-3, -100), (-12, -94), (-25, -98)]))
    P.ink(np.maximum(strap, bag), INK, 0.7, 0.4, 35, tex=0.3)
    # arm reaching to the crook
    sleeve = P.stroke(F([(8, -196), (24, -176), (38, -154)]), 15 * S, 10 * S)
    P.ink(sleeve, (0.22, 0.24, 0.27), 0.9, 0.5, 36, tex=0.3)
    hand = P.ellipse(*F([(42, -150)])[0], 6 * S, 5 * S, rot=0.4)
    P.paint(hand, (0.84, 0.79, 0.7))
    P.ink(hand, WASH, 0.0, 1.0, 37, tex=0)
    # hood and face, raised to the sky
    hood = P.poly(F([(-16, -206), (-20, -228), (-12, -246), (2, -254), (16, -250), (24, -240), (22, -226),
                     (16, -210), (4, -204)]))
    P.ink(hood, (0.2, 0.21, 0.24), 0.9, 0.6, 38, tex=0.35)
    face = P.poly(F([(12, -244), (19, -242), (24, -236), (29, -232), (25, -229), (26, -225), (24, -222),
                     (25, -219), (21, -214), (14, -213), (10, -226)]), per=5)
    P.paint(face, (0.86, 0.81, 0.72))
    P.ink(face, WASH, 0.05, 1.1, 39, tex=0)
    rimh = P.stroke(F([(15, -250), (10, -238), (9, -224), (13, -210)]), 4.5 * S, 3 * S)
    P.ink(rimh, INK, 0.9, 0.2, 40, tex=0.1)
    eye = P.stroke(F([(19, -234), (22, -233.5)]), 1.1 * S)
    P.paint(eye, INK, 0.8)
    # the dog: a collie sitting, looking up at him
    DS = 1.25                                    # the dog's own scale, about its front paws

    def D(pts):
        return F([(88 + (u - 88) * DS, v * DS) for u, v in pts])
    dog = P.poly(D([(114, 0), (122, -12), (120, -28), (111, -42), (104, -54), (100, -64), (95, -73), (86, -75),
                    (79, -71), (71, -67), (67, -63), (70, -59), (77, -57), (80, -52), (76, -44), (75, -34),
                    (82, -18), (81, -1), (91, -1), (100, -5), (108, -1)]), per=6)
    ears = np.maximum(P.poly(D([(84, -72), (86, -80), (88, -84), (91, -80), (94, -72)]), smooth=False),
                      P.poly(D([(92, -73), (95, -80), (98, -84), (100, -78), (101, -70)]), smooth=False))
    ruff = P.poly(D([(96, -64), (104, -58), (102, -46), (92, -40), (84, -46)]))
    tail = P.stroke(D([(116, -2), (128, -1), (137, -5), (141, -11)]), 7 * S * DS, 3 * S * DS)
    P.ink(np.clip(dog + ears + ruff + tail, 0, 1), INK, 0.9, 0.5, 41, tex=0.2, grain=12)
    blaze = np.maximum.reduce([P.poly(D([(80, -54), (87, -52), (90, -38), (86, -20), (80, -22), (76, -36)])),
                               P.ellipse(*D([(139, -10)])[0], 3 * S * DS, 3.5 * S * DS)])
    P.paint(blaze * np.clip(dog + tail, 0, 1), (0.87, 0.85, 0.79), 0.92)
    paws = np.maximum(P.ellipse(*D([(84, -2)])[0], 4 * S * DS, 2.5 * S * DS),
                      P.ellipse(*D([(90, -2)])[0], 4 * S * DS, 2.5 * S * DS))
    P.paint(paws, (0.84, 0.82, 0.76), 0.9)
    eyed = P.ellipse(*D([(80, -68)])[0], 1.5 * S, 1.5 * S)
    P.paint(eyed, (0.8, 0.78, 0.72), 0.8)
    # grass tufts about their feet
    rng = np.random.default_rng(42)
    tufts = []
    for k in range(22):
        u = rng.uniform(-100, 150)
        for j in range(3):
            lean = rng.uniform(-8, 10)
            tufts.append(P.stroke(F([(u + j * 2, 4), (u + j * 2 + lean * 0.5, -6), (u + j * 2 + lean, -rng.uniform(9, 18))]),
                                  2.2 * S, 0.4 * S))
    P.ink(np.clip(np.maximum.reduce(tufts), 0, 1), INK, 0.6, 0.0, 43, tex=0.4)


def strip_shepherd(w, h, at):
    img = paper(h, w, hexf('#efe7d6'), 1)
    sky = np.linspace(0, 1, h)[:, None, None]
    img = img * (0.92 + 0.08 * sky) + hexf('#c9d6de') * (1 - sky) ** 2 * 0.25
    x = np.arange(w)
    for i, (base, amp, col, a) in enumerate([(640, 90, '#9aa3a8', 0.35), (720, 70, '#7c8589', 0.5),
                                              (820, 60, '#5d6468', 0.65), (930, 40, '#3f4548', 0.8)]):
        curve = base + amp * noise1d(w, 900 - 150 * i, 10 + i)
        img = wash_layer(img, curve, hexf(col), a, 6 + 3 * i, 20 + i)
    # the shepherd on a near hilltop, with a crook and his dog, and a scatter of sheep down the slope
    img = np.ascontiguousarray(img, np.float32)
    near = 930 + 40 * noise1d(w, 450, 13)
    sx = int(at(3.2)) + 40                       # standing where the pen is when the whistling starts
    sy = int(near[sx]) + 3
    rng = np.random.default_rng(4)
    flock = []
    for k in range(30):
        x0 = rng.uniform(0.03, 0.97) * w
        if sx - 170 < x0 < sx + 230:
            continue
        dep = rng.uniform(0, 1)
        flock.append((dep, x0, near[int(x0)] + 18 + dep * 100, 0.9 + 0.8 * dep, int(rng.integers(1000)),
                      1 if rng.random() < 0.5 else -1))
    for dep, x0, y0, s, sd, face in sorted(flock):              # far ones first
        _sheep(img, x0, y0, s, sd, face)
    _shepherd(img, sx, sy)
    return img


# ------------------------------------------------------------------ kitchen: night interior, ink wash warm
def strip_kitchen(w, h, at, child=False):
    img = paper(h, w, hexf('#1d2233'), 2, grain=0.02)
    x = np.arange(w)
    # warm lamplight pools along the room
    lamp = np.exp(-((x - at(150)) / 1400) ** 2) * (0.35 if child else 1.0)
    Y = np.linspace(0, 1, h)[:, None]
    img += (hexf('#5a3a1c') * (lamp[None, :] * np.exp(-((Y - 0.35) / 0.4) ** 2))[..., None] * 0.9).astype(np.float32)
    img = np.ascontiguousarray(img, np.float32)
    if child:
        child_t0 = next(s['t0'] for s in json.load(open('timeline.json'))['scenes'] if s['name'] == 'child')
        bx = int(at(child_t0 + 3.5)) - 90                      # the child's bed
        _child_room(img, bx)
        return img
    px = int(at(146))                          # the parent's head passes under the pen mid-song
    lx = int(at(150)) + 40                     # the table lamp, where the room's light pool is centred
    lamps = [(lx, 712, 430, 1.35)]
    _kitchen_wall(img, at, px, lamps)
    _parent_behind(img, px, lamps)
    _table(img, lx, lamps)
    _parent_front(img, px, lamps)
    _lamp(img, lx)
    _teapot(img, int(at(160)) + 300, lamps)
    return img


# kitchen palette: (shadow, lamplit) pairs
WOOD = ((0.1, 0.065, 0.06), (0.62, 0.4, 0.24))
CARD = ((0.16, 0.09, 0.09), (0.84, 0.5, 0.32))       # a rust-coloured knitted cardigan
SKIN = ((0.24, 0.14, 0.12), (1.0, 0.8, 0.6))
HAIR = ((0.08, 0.06, 0.07), (0.5, 0.32, 0.2))
CREAM = ((0.2, 0.17, 0.17), (0.95, 0.88, 0.74))


def _kitchen_wall(img, at, px, lamps):
    H, W, _ = img.shape
    # tongue-and-groove boarding below a dado rail
    X = np.arange(W)
    img[700:862] *= 0.8
    img[700:862, X % 46 < 2] *= 0.72
    img[700:862, X % 46 == 2] *= 1.12
    P = Painter(img, (0, 684, W, 712), ss=2)
    P.lit(P.poly([(0, 690), (W, 690), (W, 704), (0, 704)], smooth=False), *WOOD, lamps, amb=0.2, s=3)
    # the window, the moon, a curtain
    wx = int(at(137)) + 350
    P = Painter(img, (wx - 130, 120, wx + 400, 560))
    glass = P.poly([(wx, 170), (wx + 300, 170), (wx + 300, 470), (wx, 470)], smooth=False)
    k = ((P.Y - 170) / 300)[..., None]
    P.paint(glass, col3((0.05, 0.08, 0.17)) * (1 - k) + col3((0.13, 0.16, 0.28)) * k)
    P.glow(wx + 215, 235, 70, (0.25, 0.27, 0.3), 0.5 * 1)
    rng = np.random.default_rng(71)
    for _ in range(14):
        sx, sy = wx + rng.uniform(10, 290), rng.uniform(180, 440)
        P.paint(P.ellipse(sx, sy, 1.3, 1.3) * glass, (0.8, 0.8, 0.75), rng.uniform(0.3, 0.8))
    moon = P.ellipse(wx + 215, 235, 25, 25)
    P.paint(moon, (0.93, 0.91, 0.83))
    P.paint(P.ellipse(wx + 206, 229, 6, 5) + P.ellipse(wx + 222, 244, 4, 4), (0.8, 0.79, 0.74), 0.6)
    outer = P.poly([(wx - 12, 158), (wx + 312, 158), (wx + 312, 482), (wx - 12, 482)], smooth=False)
    bars = np.maximum(P.poly([(wx + 146, 170), (wx + 154, 170), (wx + 154, 470), (wx + 146, 470)], smooth=False),
                      P.poly([(wx, 316), (wx + 300, 316), (wx + 300, 324), (wx, 324)], smooth=False))
    P.lit(np.clip(outer - glass + bars, 0, 1), (0.1, 0.08, 0.08), (0.7, 0.62, 0.52), lamps, amb=0.18, s=3)
    sill = P.poly([(wx - 34, 478), (wx + 334, 478), (wx + 330, 496), (wx - 30, 496)], smooth=False)
    P.lit(sill, (0.1, 0.08, 0.08), (0.8, 0.7, 0.58), lamps, amb=0.2, s=3)
    rod = P.stroke([(wx - 70, 146), (wx + 370, 146)], 5)
    P.lit(rod, *WOOD, lamps, s=2)
    curtain = P.poly([(wx - 60, 146), (wx + 58, 146), (wx + 44, 230), (wx + 30, 330), (wx + 36, 420),
                      (wx + 52, 540), (wx - 6, 548), (wx - 64, 540), (wx - 58, 400)])
    folds = 1 + 0.16 * np.sin((P.X - wx) / 9 + 0.004 * np.clip(P.Y - 146, 0, None) ** 1.4)
    P.lit(curtain, (0.07, 0.09, 0.08), (0.46, 0.55, 0.42), lamps, amb=0.14, s=6, tex=folds)
    # a shelf of kitchen things, right of the lamp
    sx0 = px + 430
    P = Painter(img, (sx0 - 20, 300, sx0 + 440, 560))
    plank = P.poly([(sx0, 430), (sx0 + 400, 430), (sx0 + 400, 446), (sx0, 446)], smooth=False)
    brackets = P.polys([[(sx0 + 40, 446), (sx0 + 52, 446), (sx0 + 52, 500)], [(sx0 + 348, 446), (sx0 + 360, 446),
                                                                                (sx0 + 348, 500)]])
    P.lit(np.clip(plank + brackets, 0, 1), *WOOD, lamps, s=3)
    # jars of beans and oats
    for x0, x1, y0, fill_col in ((sx0 + 18, sx0 + 72, 356, (0.62, 0.36, 0.18)), (sx0 + 82, sx0 + 118, 384,
                                                                                  (0.78, 0.66, 0.44))):
        jar = P.poly([(x0, y0 + 10), (x1, y0 + 10), (x1 + 2, 424), (x1 - 4, 430), (x0 + 4, 430), (x0 - 2, 424)],
                     per=4)
        content = jar * (P.Y > y0 + 0.4 * (430 - y0))
        P.lit(jar, (0.08, 0.08, 0.1), (0.5, 0.52, 0.5), lamps, amb=0.2, s=4)
        P.lit(content, (0.1, 0.06, 0.05), fill_col, lamps, amb=0.15, s=4,
              tex=1 + 0.18 * np.sin(P.X * 1.3) * np.sin(P.Y * 1.1))
        P.paint(P.edge(jar, 1.0), (0.85, 0.82, 0.75), 0.25)
        lid = P.poly([(x0 - 2, y0), (x1 + 2, y0), (x1 + 2, y0 + 11), (x0 - 2, y0 + 11)], per=3)
        P.lit(lid, (0.1, 0.08, 0.06), (0.72, 0.58, 0.36), lamps, s=2)
    # a pot plant trailing over the edge
    pot = P.poly([(sx0 + 148, 396), (sx0 + 202, 396), (sx0 + 196, 430), (sx0 + 154, 430)], smooth=False)
    P.lit(pot, (0.14, 0.06, 0.04), (0.78, 0.42, 0.26), lamps, s=3)
    rng = np.random.default_rng(72)
    leaves = []
    for k in range(9):
        a = -np.pi / 2 + rng.uniform(-1.3, 1.3)
        r = rng.uniform(16, 30)
        cx, cy = sx0 + 175 + r * np.cos(a), 392 + r * np.sin(a) * 0.9
        leaves.append(P.ellipse(cx, cy, 11, 5, rot=a))
    vine = [(sx0 + 196, 420), (sx0 + 214, 440), (sx0 + 218, 480), (sx0 + 210, 520), (sx0 + 214, 546)]
    stem = P.stroke(vine, 2)
    for i, (vx, vy) in enumerate(smooth_curve(vine, 3)[1::2]):
        leaves.append(P.ellipse(vx + (6 if i % 2 else -6), vy, 7, 4, rot=0.6 if i % 2 else -0.6))
    P.lit(np.clip(np.maximum.reduce(leaves) + stem, 0, 1), (0.04, 0.07, 0.05), (0.42, 0.56, 0.3), lamps, s=3)
    # books, one leaning
    for i, (bc, bw, bh, lean) in enumerate((((0.55, 0.2, 0.18), 18, 76, 0), ((0.25, 0.32, 0.5), 15, 70, 0),
                                            ((0.7, 0.55, 0.28), 17, 64, 0.28))):
        x0 = sx0 + 236 + i * 19
        pts = rot_pts([(0, 0), (bw, 0), (bw, -bh), (0, -bh)], x0 + (4 if lean else 0), 430, lean)
        P.lit(P.poly(pts, smooth=False), col3(bc) * 0.15, bc, lamps, amb=0.15, s=3)
    # a small framed photo: the child
    fx = sx0 + 330
    frame_m = P.poly([(fx, 368), (fx + 50, 368), (fx + 50, 430), (fx, 430)], smooth=False)
    P.lit(frame_m, *WOOD, lamps, s=3)
    inner = P.poly([(fx + 7, 375), (fx + 43, 375), (fx + 43, 423), (fx + 7, 423)], smooth=False)
    P.paint(inner, (0.62, 0.55, 0.45))
    kid = np.maximum(P.ellipse(fx + 25, 392, 7, 8), P.ellipse(fx + 25, 418, 13, 11))
    P.paint(kid * inner, (0.3, 0.2, 0.18), 0.9)
    # further along: a clock at ten to three, and the child's drawing pinned up
    cx0 = px + 1260
    P = Painter(img, (cx0 - 80, 220, cx0 + 80, 380))
    rim = P.ellipse(cx0, 300, 58, 58)
    P.lit(rim, *WOOD, lamps, amb=0.15, s=4)
    face_m = P.ellipse(cx0, 300, 49, 49)
    P.lit(face_m, *CREAM, lamps, amb=0.2, s=5)
    ticks = P.polys([rot_pts([(-1.5, -44), (1.5, -44), (1.5, -36), (-1.5, -36)], cx0, 300, k * np.pi / 6)
                     for k in range(12)])
    hands = np.maximum(P.stroke(rot_pts([(0, 4), (0, -26)], cx0, 300, np.pi * 2 * 2.83 / 12), 4),
                       P.stroke(rot_pts([(0, 5), (0, -40)], cx0, 300, np.pi * 2 * 50 / 60), 2.5))
    P.paint(np.clip(ticks + hands, 0, 1), (0.14, 0.1, 0.1), 0.9)
    dx0 = px + 1560
    P = Painter(img, (dx0 - 120, 180, dx0 + 120, 440))
    sheet = P.poly(rot_pts([(-90, -110), (90, -110), (90, 110), (-90, 110)], dx0, 310, 0.05), smooth=False)
    P.lit(sheet, (0.2, 0.18, 0.18), (0.85, 0.8, 0.7), lamps, amb=0.3, s=4)
    crayon = []
    sun = P.ellipse(dx0 + 52, 236, 16, 16)
    rays = [P.stroke(rot_pts([(0, 20), (0, 30)], dx0 + 52, 236, k * np.pi / 4), 2.2) for k in range(8)]
    P.paint(np.clip(sun + np.maximum.reduce(rays), 0, 1) * sheet, (0.85, 0.6, 0.15), 0.8)
    for fxp, sz in ((-38, 1.0), (10, 0.7)):        # a big figure and a small one, holding hands
        cx, top = dx0 + fxp, 262 + (1 - sz) * 60
        crayon += [P.ellipse(cx, top, 11 * sz, 11 * sz) - P.ellipse(cx, top, 8 * sz, 8 * sz),
                   P.poly([(cx, top + 11 * sz), (cx - 20 * sz, top + 80 * sz), (cx + 20 * sz, top + 80 * sz)],
                          smooth=False) - P.poly([(cx, top + 17 * sz), (cx - 15 * sz, top + 76 * sz),
                                                  (cx + 15 * sz, top + 76 * sz)], smooth=False),
                   P.stroke([(cx - 6 * sz, top + 80 * sz), (cx - 8 * sz, top + 108 * sz)], 2.5),
                   P.stroke([(cx + 6 * sz, top + 80 * sz), (cx + 8 * sz, top + 108 * sz)], 2.5)]
    crayon.append(P.stroke([(dx0 - 26, 300), (dx0 - 6, 312), (dx0 + 4, 306)], 2.5))
    P.paint(np.clip(np.maximum.reduce(crayon), 0, 1) * sheet, (0.55, 0.2, 0.3), 0.75)
    grass = P.stroke([(dx0 - 85, 395), (dx0 - 40, 388), (dx0, 396), (dx0 + 50, 388), (dx0 + 85, 394)], 4)
    P.paint(grass * sheet, (0.3, 0.55, 0.3), 0.7)
    P.paint(P.ellipse(dx0 - 4, 206, 5, 5), (0.7, 0.2, 0.18))      # the drawing pin


def _parent_behind(img, px, lamps):
    """The humming parent, seen in profile facing the lamp: chair, cardigan, head tilted back, eyes shut."""
    P = Painter(img, (px - 170, 460, px + 180, 900))
    # the chair back behind them
    posts = np.maximum(P.stroke([(px - 128, 880), (px - 124, 700), (px - 118, 598)], 12, 10),
                       P.stroke([(px - 60, 880), (px - 58, 700), (px - 56, 606)], 12, 10))
    crest = P.poly([(px - 134, 590), (px - 48, 598), (px - 48, 626), (px - 132, 618)], per=4)
    spindles = np.maximum.reduce([P.stroke([(px - 108 + 16 * k, 620), (px - 106 + 16 * k, 880)], 6)
                                  for k in range(3)])
    P.lit(np.clip(posts + crest + spindles, 0, 1), *WOOD, lamps, amb=0.1, s=4)
    # torso in the cardigan, ribbed knit
    rib = 1 + 0.05 * np.sin(P.X * 2 * np.pi / 7) * (P.Y > 600)
    torso = P.poly([(px - 22, 592), (px - 42, 604), (px - 60, 626), (px - 70, 676), (px - 76, 760), (px - 78, 890),
                    (px + 36, 890), (px + 52, 822), (px + 58, 762), (px + 50, 700), (px + 34, 654), (px + 18, 620),
                    (px + 4, 602)])
    P.lit(torso, *CARD, lamps, s=10, tex=rib)
    neck = P.poly([(px - 16, 574), (px + 12, 578), (px + 18, 616), (px - 20, 616)], per=4)
    P.lit(neck, *SKIN, lamps, amb=0.08, s=5)
    shirt = P.poly([(px - 2, 604), (px + 12, 606), (px + 26, 640), (px + 12, 634)], per=4)
    P.lit(shirt, *CREAM, lamps, s=3)
    collar = P.stroke([(px - 10, 600), (px + 10, 622), (px + 28, 664), (px + 42, 720), (px + 48, 760)], 18, 9)
    P.lit(collar * torso, (0.2, 0.11, 0.1), (0.92, 0.6, 0.4), lamps, s=4)
    P.paint(P.edge(collar, 1.0) * torso, CARD[0], 0.5)
    for by in (748, 796):
        P.lit(P.ellipse(px + 40, by, 3.5, 3.5), (0.15, 0.1, 0.06), (0.9, 0.75, 0.5), lamps, s=1.5)
    # the head, tilted back a little as they hum, eyes closed
    ang = -0.17
    cx, cy = px + 2, 548

    def Hp(pts):
        return rot_pts(pts, cx, cy, ang)
    head = P.poly(Hp([(30, -30), (35, -18), (36, -8), (39, -3), (45, 7), (46, 11), (40, 15), (40, 19), (42, 22),
                      (38, 25), (40, 28), (35, 33), (36, 40), (28, 46), (12, 46), (0, 44), (-20, 36), (-34, 20),
                      (-40, 0), (-36, -24), (-22, -40), (0, -47), (18, -42)]), per=4)
    P.lit(head, *SKIN, lamps, amb=0.08, s=6, vol=0.6, rim=1.1)
    P.glow(*Hp([(24, 14)])[0], 10, (0.25, 0.04, 0.02), 0.25)                    # warm cheek
    hair = P.poly(Hp([(30, -32), (22, -45), (4, -53), (-20, -49), (-39, -35), (-47, -12), (-45, 8), (-38, 22),
                      (-27, 30), (-17, 25), (-13, 6), (-5, -8), (8, -20), (20, -26)]))
    bun = P.ellipse(*Hp([(-36, -40)])[0], 18, 15, rot=ang - 0.5)
    wisps = np.maximum.reduce([P.stroke(Hp(p), 1.6, 0.4) for p in ([(-44, -30), (-54, -24), (-56, -10)],
                                                                    [(-30, -52), (-34, -62), (-26, -66)],
                                                                    [(-12, 6), (-10, 20), (-14, 32)])])
    bcx, bcy = Hp([(-36, -40)])[0]
    strands = 1 + 0.16 * np.sin(np.arctan2(P.Y - bcy, P.X - bcx) * 38) * np.clip(np.hypot(P.X - bcx, P.Y - bcy) / 30 - 0.5, 0, 1)
    P.lit(np.clip(hair + bun + wisps, 0, 1), *HAIR, lamps, amb=0.1, s=5, tex=strands)
    ear = P.ellipse(*Hp([(-7, 5)])[0], 6.5, 10, rot=ang + 0.2)
    P.lit(ear, *SKIN, lamps, amb=0.05, s=3)
    P.paint(P.stroke(Hp([(-5, 0), (-8, 6), (-5, 11)]), 1.4), SKIN[0], 0.6)
    lid = P.stroke(Hp([(20, -3), (25, 0.5), (31, -1)]), 1.8)
    lashes = P.stroke(Hp([(25, 1), (27, 4)]), 1.1)
    brow = P.stroke(Hp([(17, -13), (25, -15), (33, -12)]), 2.6, 1.4)
    lips = P.stroke(Hp([(36, 23.5), (40, 24)]), 1.6)
    nostril = P.stroke(Hp([(38, 11), (41, 12)]), 1.4)
    P.paint(np.clip(lid + lashes + lips + nostril, 0, 1), (0.22, 0.11, 0.1), 0.85)
    P.paint(brow, HAIR[0], 0.8)
    P.paint(P.edge(head, 0.8) * (P.X < cx + 10), SKIN[0], 0.35)
    P.glow(px + 60, 560, 45, (0.35, 0.18, 0.06), 0.12)             # lamplight catching the face


def _table(img, lx, lamps):
    H, W, _ = img.shape
    P = Painter(img, (0, 854, W, H), ss=2)
    rng = np.random.default_rng(73)
    wob = gaussian_filter(rng.standard_normal(W), 40)[None, :] * 60
    grain = 1 + 0.07 * np.sin(P.Y * 0.8 + wob) + 0.04 * np.sin(P.Y * 2.3 + wob * 1.7)
    top = P.poly([(0, 860), (W, 860), (W, 926), (0, 926)], smooth=False)
    P.lit(top, (0.07, 0.05, 0.05), (0.62, 0.4, 0.25), lamps, amb=0.12, vol=0.7, s=3, tex=grain)
    front = P.poly([(0, 926), (W, 926), (W, H), (0, H)], smooth=False)
    P.lit(front, (0.05, 0.035, 0.035), (0.34, 0.22, 0.15), lamps, amb=0.1, vol=0.45, rim=0, s=3, tex=grain)
    P.paint(P.stroke([(0, 861), (W, 861)], 3), (0.55, 0.38, 0.25), 0.5)
    P.paint(P.stroke([(0, 927), (W, 927)], 2), (0.03, 0.02, 0.02), 0.6)
    pool = np.exp(-((P.X - lx) / 360) ** 2 - ((P.Y - 895) / 38) ** 2) * top
    P.add(pool, (0.45, 0.28, 0.1), 0.6)


def _parent_front(img, px, lamps):
    """Forearms on the table, both hands round a mug."""
    P = Painter(img, (px - 80, 620, px + 200, 900))
    rib = 1 + 0.06 * np.sin(P.X * 2 * np.pi / 7 + P.Y * 0.3)
    upper = P.stroke([(px - 24, 640), (px - 30, 700), (px - 26, 756), (px - 12, 792)], 46, 40)
    fore = P.stroke([(px - 14, 796), (px + 16, 786), (px + 50, 766), (px + 70, 750)], 40, 30)
    P.lit(upper, *CARD, lamps, s=9, tex=rib)
    P.paint(P.edge(upper, 1.4) * (P.X < px - 20), CARD[0], 0.55)
    P.lit(fore, *CARD, lamps, s=8, tex=rib)
    P.paint(P.edge(fore, 1.4) * (P.Y > 770) * (P.X < px + 40), CARD[0], 0.45)
    P.paint(P.stroke([(px - 24, 776), (px - 12, 790), (px + 2, 794)], 2.2, 0.8), CARD[0], 0.5)   # elbow crease
    cuff = P.stroke([(px + 56, 770), (px + 72, 746)], 30)
    P.lit(cuff * fore, (0.2, 0.11, 0.1), (0.95, 0.62, 0.42), lamps, s=3, tex=1 + 0.12 * np.sin(P.X * 1.6))
    # the mug, held up under the chin
    mx, my = px + 100, 700
    body = P.poly([(mx - 23, my), (mx + 23, my), (mx + 22, my + 70), (mx + 17, my + 78), (mx - 17, my + 78),
                   (mx - 22, my + 70)], per=4)
    P.lit(body, CREAM[0], (0.86, 0.8, 0.68), lamps, amb=0.1, s=6)
    P.paint(body * (np.abs(P.Y - my - 16) < 4), (0.25, 0.35, 0.6), 0.75)
    P.lit(P.ellipse(mx, my, 23, 5), *CREAM, lamps, amb=0.3, s=2)
    P.paint(P.ellipse(mx, my + 1, 19, 3.2), (0.22, 0.12, 0.07), 0.95)          # tea
    # the far hand's fingertips, round the far side
    far = P.poly([(mx + 17, my + 26), (mx + 27, my + 30), (mx + 29, my + 46), (mx + 23, my + 54), (mx + 17, my + 48)],
                 per=4)
    P.lit(far, *SKIN, lamps, amb=0.1, s=3)
    # the near hand, wrapped round the front
    hand = P.poly([(mx - 36, my + 44), (mx - 26, my + 32), (mx - 10, my + 28), (mx + 8, my + 32), (mx + 20, my + 40),
                   (mx + 20, my + 56), (mx + 8, my + 66), (mx - 12, my + 70), (mx - 28, my + 68), (mx - 36, my + 58)])
    P.lit(hand, *SKIN, lamps, amb=0.1, s=5, vol=0.6)
    fingers = np.maximum.reduce([P.stroke([(mx - 6 + 7 * k, my + 34 + 7 * k), (mx + 10 + 3 * k, my + 40 + 7 * k),
                                           (mx + 19, my + 44 + 7 * k)], 1.1) for k in range(3)])
    P.paint(fingers * hand, SKIN[0], 0.5)
    P.paint(P.stroke([(mx - 24, my + 36), (mx - 12, my + 32), (mx - 2, my + 36)], 1.2), SKIN[0], 0.4)   # knuckles
    P.paint(P.edge(hand, 1.0), SKIN[0], 0.3)


def _lamp(img, lx):
    glow(img, lx, 700, 170, (0.55, 0.32, 0.12), 0.35)
    glow(img, lx, 690, 420, (0.32, 0.18, 0.07), 0.25)
    P = Painter(img, (lx - 300, 440, lx + 300, 900))
    L = [(lx, 736, 60, 2.0)]
    # the cone of light down onto the table, and up onto the wall
    cone = gaussian_filter(P.poly([(lx - 92, 734), (lx + 92, 734), (lx + 250, 900), (lx - 250, 900)], smooth=False), 10)
    P.add(cone, (0.35, 0.22, 0.08), 0.35)
    up = gaussian_filter(P.poly([(lx - 56, 642), (lx + 56, 642), (lx + 120, 540), (lx - 120, 540)], smooth=False), 14)
    P.add(up * np.clip((P.Y - 520) / 120, 0, 1), (0.3, 0.18, 0.07), 0.3)
    base = P.poly([(lx - 9, 810), (lx + 9, 810), (lx + 27, 836), (lx + 31, 862), (lx + 22, 890), (lx - 22, 890),
                   (lx - 31, 862), (lx - 27, 836)], per=4)
    P.lit(base, (0.05, 0.1, 0.11), (0.5, 0.7, 0.62), L, amb=0.15, s=6)
    P.glow(lx - 10, 846, 6, (0.4, 0.4, 0.35), 0.5)                       # glaze highlight
    stem = P.stroke([(lx, 736), (lx, 812)], 5)
    P.lit(stem, (0.1, 0.08, 0.05), (0.8, 0.62, 0.35), L, s=2)
    shade = np.maximum(P.poly([(lx - 58, 642), (lx + 58, 642), (lx + 95, 732), (lx - 95, 732)], smooth=False),
                       P.ellipse(lx, 732, 95, 7))
    k = np.clip((P.Y - 642) / 90, 0, 1)
    across = 1 - 0.25 * np.abs(P.X - lx) / 95
    shade_col = (col3((0.8, 0.46, 0.2)) * (1 - k[..., None]) + col3((1.0, 0.82, 0.52)) * k[..., None]) * across[..., None]
    P.paint(shade, shade_col)
    P.paint(P.stroke([(lx - 58, 642), (lx + 58, 642)], 3) + P.stroke([(lx - 95, 732), (lx + 95, 732)], 3) * 0,
            (0.55, 0.3, 0.12), 0.6)
    P.paint(P.ellipse(lx, 733, 88, 5), (1.0, 0.95, 0.8), 0.9)


def _teapot(img, cx, lamps):
    P = Painter(img, (cx - 130, 740, cx + 110, 900))
    brown = ((0.06, 0.035, 0.03), (0.55, 0.3, 0.17))
    spout = P.stroke([(cx - 40, 862), (cx - 72, 838), (cx - 96, 804)], 20, 8)
    handle = P.stroke([(cx + 46, 818), (cx + 80, 816), (cx + 86, 846), (cx + 52, 870)], 10)
    body = P.poly([(cx - 62, 850), (cx - 52, 812), (cx - 22, 796), (cx + 22, 796), (cx + 52, 812), (cx + 62, 850),
                   (cx + 50, 880), (cx + 30, 890), (cx - 30, 890), (cx - 50, 880)])
    P.lit(np.clip(spout + handle, 0, 1), *brown, lamps, amb=0.1, s=4)
    P.lit(body, *brown, lamps, amb=0.1, s=10, vol=0.7)
    lidm = P.ellipse(cx, 796, 30, 7) + P.ellipse(cx, 786, 7, 6)
    P.lit(np.clip(lidm, 0, 1), *brown, lamps, amb=0.12, s=2)
    P.glow(cx - 30, 822, 7, (0.5, 0.45, 0.4), 0.45)


def _child_room(img, bx):
    """The child's bedroom: bed, quilt, teddy, a moon nightlight, and the parent in the lit doorway."""
    H, W, _ = img.shape
    nlx, nly = bx - 150, 718
    dx = bx + 880
    lamps = [(nlx, nly, 260, 1.3), (dx + 120, 600, 300, 0.55)]
    # starry wallpaper, very faint
    P = Painter(img, (bx - 900, 0, dx + 900, 860), ss=1)
    rng = np.random.default_rng(81)
    stars = []
    for gx in range(bx - 900, dx + 900, 90):
        for gy in range(40, 860, 90):
            sx, sy = gx + rng.uniform(0, 60) + (45 if (gy // 90) % 2 else 0), gy + rng.uniform(0, 40)
            r = rng.uniform(4, 7)
            stars.append([(sx + r * np.cos(a) * (1 if k % 2 == 0 else 0.4), sy + r * np.sin(a) * (1 if k % 2 == 0 else 0.4))
                          for k, a in enumerate(np.linspace(0, 2 * np.pi, 10, endpoint=False) - np.pi / 2)])
    P.paint(P.polys(stars), (0.55, 0.52, 0.45), 0.08)
    # skirting and floorboards
    P = Painter(img, (bx - 900, 850, dx + 900, H), ss=2)
    skirt = P.poly([(bx - 900, 852), (dx + 900, 852), (dx + 900, 880), (bx - 900, 880)], smooth=False)
    P.lit(skirt, (0.08, 0.08, 0.1), (0.72, 0.62, 0.5), lamps, amb=0.15, s=3)
    floor = P.poly([(bx - 900, 880), (dx + 900, 880), (dx + 900, H), (bx - 900, H)], smooth=False)
    lines = np.ones_like(P.X)
    for yl in (898, 922, 952, 990, 1036):
        lines -= 0.35 * np.exp(-((P.Y - yl) / 1.2) ** 2)
    P.lit(floor, (0.05, 0.04, 0.05), (0.48, 0.32, 0.22), lamps, amb=0.1, vol=0.8, rim=0, s=3, tex=lines)
    # the doorway: warm hall light, the door half open, the parent leaning on the frame
    P = Painter(img, (dx - 500, 180, dx + 420, H), ss=2)
    hall = P.poly([(dx, 240), (dx + 240, 240), (dx + 240, 895), (dx, 895)], smooth=False)
    k = ((P.Y - 240) / 655)[..., None]
    hall_col = col3((0.98, 0.78, 0.5)) * (1 - k) + col3((0.78, 0.52, 0.3)) * k
    hall_col = hall_col * (1 - 0.35 * np.clip((P.X - dx - 170) / 70, 0, 1))[..., None]    # hall wall in shade
    P.paint(hall, hall_col)
    frame_m = P.poly([(dx - 22, 220), (dx + 262, 220), (dx + 262, 895), (dx - 22, 895)], smooth=False) - hall
    P.lit(np.clip(frame_m, 0, 1), (0.1, 0.09, 0.11), (0.85, 0.72, 0.58), lamps, amb=0.15, s=3)
    leaf = P.poly([(dx + 262, 226), (dx + 330, 204), (dx + 330, 930), (dx + 262, 897)], smooth=False)
    P.lit(leaf, (0.07, 0.06, 0.08), (0.45, 0.35, 0.3), lamps, amb=0.12, s=3)
    spill = gaussian_filter(P.poly([(dx + 4, 895), (dx + 240, 895), (dx + 230, H), (dx - 330, H)], smooth=False), 10)
    spill *= np.clip(1.1 - (P.Y - 895) / 260, 0, 1)
    shadow = gaussian_filter(P.poly([(dx + 44, 895), (dx + 102, 895), (dx - 50, H), (dx - 160, H)], smooth=False), 6)
    P.add(spill * (1 - 0.7 * shadow), (0.6, 0.38, 0.2), 0.5)
    P.glow(dx + 120, 560, 330, (0.3, 0.18, 0.08), 0.18)
    # the parent, leaning a shoulder on the frame, arms folded, head resting against it: watching
    fx, fy, lean = dx + 72, 896, -0.06

    def Fp(pts):
        return rot_pts(pts, fx, fy, lean)
    body = P.poly(Fp([(-12, -462), (-38, -452), (-50, -430), (-54, -392), (-62, -356), (-60, -324), (-50, -306),
                      (-48, -260), (-53, -198),
                      (-44, -194), (-40, -130), (-37, -72), (-24, -70), (-22, -10), (-32, -1), (-4, -1), (-8, -12),
                      (-6, -70), (6, -70), (8, -12), (4, -1), (30, -1), (18, -10), (20, -70), (37, -72), (41, -130),
                      (45, -194), (54, -198), (50, -262), (50, -306), (60, -324), (62, -356), (54, -392),
                      (50, -430), (38, -452), (12, -462)]), per=4)
    headm = P.ellipse(*Fp([(-2, -500)])[0], 28, 33, rot=lean - 0.28)
    bun = P.ellipse(*Fp([(21, -528)])[0], 14, 12)
    neck = P.poly(Fp([(-12, -476), (10, -476), (12, -452), (-12, -452)]), per=4)
    sil = np.clip(body + headm + bun + neck, 0, 1)
    P.paint(sil, (0.13, 0.085, 0.09))
    P.paint(P.edge(sil, 1.6), (0.95, 0.66, 0.4), 0.5)
    folded = P.stroke(Fp([(-58, -330), (-20, -326), (20, -336), (58, -346)]), 3, 1.5)          # the folded arms
    hem = P.stroke(Fp([(-52, -198), (0, -194), (54, -198)]), 2)
    P.paint(np.clip(folded + hem, 0, 1) * sil, (0.24, 0.15, 0.12), 0.8)
    # bedside table with the moon nightlight and a book
    P = Painter(img, (bx - 300, 560, bx + 20, 900))
    top = P.poly([(bx - 250, 760), (bx - 50, 760), (bx - 50, 778), (bx - 250, 778)], per=3)
    cab = P.poly([(bx - 240, 778), (bx - 60, 778), (bx - 60, 885), (bx - 240, 885)], smooth=False)
    legs = P.polys([[(bx - 238, 885), (bx - 226, 885), (bx - 226, 898), (bx - 238, 898)],
                    [(bx - 74, 885), (bx - 62, 885), (bx - 62, 898), (bx - 74, 898)]])
    P.lit(np.clip(top + cab + legs, 0, 1), (0.08, 0.07, 0.1), (0.78, 0.62, 0.52), lamps, amb=0.1, s=4)
    P.paint(P.stroke([(bx - 226, 820), (bx - 74, 820)], 2), (0.1, 0.08, 0.1), 0.6)
    P.lit(P.ellipse(bx - 150, 800, 6, 6), (0.1, 0.08, 0.05), (0.9, 0.75, 0.45), lamps, s=2)
    book = P.poly([(bx - 236, 744), (bx - 176, 744), (bx - 176, 760), (bx - 236, 760)], per=3)
    P.lit(book, (0.08, 0.05, 0.08), (0.62, 0.3, 0.38), lamps, amb=0.1, s=2)
    P.glow(nlx, nly, 60, (0.7, 0.45, 0.18), 0.55)
    stand = P.stroke([(nlx, 758), (nlx, 742)], 5) + P.ellipse(nlx, 759, 18, 4)
    P.lit(np.clip(stand, 0, 1), (0.1, 0.08, 0.08), (0.6, 0.5, 0.4), lamps, s=2)
    moon = np.clip(P.ellipse(nlx, nly, 26, 26) - P.ellipse(nlx + 13, nly - 9, 23, 23), 0, 1)
    P.paint(moon, (1.0, 0.88, 0.62))
    glow(img, nlx, nly, 240, (0.4, 0.24, 0.1), 0.35)
    # the bed
    P = Painter(img, (bx - 60, 560, bx + 620, 905))
    bed_lamps = [(nlx, nly, 210, 1.2), (dx + 120, 600, 300, 0.45)]
    head_b = P.poly([(bx - 42, 896), (bx - 42, 646), (bx - 30, 618), (bx - 12, 610), (bx + 8, 618), (bx + 18, 646),
                     (bx + 18, 896)], per=4)
    foot_b = P.poly([(bx + 546, 896), (bx + 546, 716), (bx + 551, 703), (bx + 564, 697), (bx + 577, 703),
                     (bx + 582, 716), (bx + 582, 896)], per=4)
    rail = P.poly([(bx + 10, 846), (bx + 560, 846), (bx + 560, 880), (bx + 10, 880)], smooth=False)
    wood = ((0.07, 0.06, 0.08), (0.8, 0.66, 0.54))
    P.lit(np.clip(head_b + foot_b + rail, 0, 1), *wood, lamps, amb=0.1, s=5)
    heart = P.poly([(bx - 12, 668), (bx - 20, 656), (bx - 12, 650), (bx - 12, 650), (bx - 4, 656)], per=5)
    P.paint(heart, (0.05, 0.05, 0.08), 0.7)
    sheet = P.poly([(bx + 12, 792), (bx + 556, 792), (bx + 556, 848), (bx + 12, 848)], per=3)
    P.lit(sheet, (0.08, 0.08, 0.12), (0.8, 0.76, 0.72), bed_lamps, amb=0.1, s=4)
    pillow = P.poly([(bx + 14, 716), (bx + 62, 700), (bx + 150, 704), (bx + 186, 722), (bx + 182, 782),
                     (bx + 120, 794), (bx + 34, 792), (bx + 12, 772)])
    P.lit(pillow, (0.1, 0.09, 0.14), (0.9, 0.84, 0.8), bed_lamps, amb=0.1, s=9, vol=0.7)
    P.paint(P.stroke([(bx + 60, 790), (bx + 90, 776), (bx + 140, 778)], 2, 0.5) * pillow, (0.1, 0.09, 0.14), 0.25)
    # the child, asleep, face turned up to the light
    hx, hy = bx + 100, 734
    headm = P.ellipse(hx, hy, 32, 30, rot=0.25)
    dent = gaussian_filter(np.roll(np.roll(headm, 7, 0), 9, 1), 6) * pillow
    P.paint(dent, (0.06, 0.05, 0.1), 0.4)                       # the hollow the head makes in the pillow
    P.lit(headm, *SKIN, lamps, amb=0.1, s=6, vol=0.7)
    P.glow(hx + 8, hy + 14, 9, (0.3, 0.05, 0.03), 0.25)
    hairm = P.poly([(hx - 33, hy + 4), (hx - 34, hy - 20), (hx - 20, hy - 34), (hx + 4, hy - 38), (hx + 26, hy - 30),
                    (hx + 36, hy - 14), (hx + 26, hy - 20), (hx + 20, hy - 12), (hx + 12, hy - 22), (hx + 2, hy - 12),
                    (hx - 8, hy - 18), (hx - 18, hy - 4), (hx - 24, hy + 10)])
    P.lit(hairm, (0.06, 0.04, 0.05), (0.62, 0.42, 0.26), lamps, amb=0.1, s=4,
          tex=1 + 0.2 * np.sin(P.X * 0.7 - P.Y * 0.5))
    eyes = np.maximum(P.stroke([(hx - 4, hy + 2), (hx + 1, hy + 5), (hx + 6, hy + 3)], 1.7),
                      P.stroke([(hx + 16, hy - 1), (hx + 20, hy + 2), (hx + 24, hy + 0)], 1.6))
    mouth = P.stroke([(hx + 11, hy + 19), (hx + 14, hy + 20), (hx + 16, hy + 19)], 1.5)
    nose = P.stroke([(hx + 13, hy + 9), (hx + 15, hy + 12)], 1.3)
    P.paint(np.clip(eyes + mouth, 0, 1), (0.28, 0.14, 0.12), 0.8)
    P.paint(nose, SKIN[0], 0.4)
    # teddy, tucked in beside them
    tx, ty = bx + 196, 744
    ted = np.clip(P.ellipse(tx, ty, 19, 17) + P.ellipse(tx - 14, ty - 14, 7, 7) + P.ellipse(tx + 14, ty - 14, 7, 7)
                  + P.ellipse(tx + 8, ty + 22, 22, 18), 0, 1)
    fur = ((0.1, 0.06, 0.05), (0.78, 0.52, 0.3))
    P.lit(ted, *fur, lamps, amb=0.1, s=5, tex=1 + 0.08 * np.sin(P.X * 2.1) * np.sin(P.Y * 1.9))
    P.lit(P.ellipse(tx - 3, ty + 5, 8, 6), (0.2, 0.14, 0.1), (0.95, 0.82, 0.62), lamps, s=2)
    P.paint(P.ellipse(tx - 5, ty + 2, 2.5, 2), (0.1, 0.06, 0.05), 0.9)
    P.paint(P.ellipse(tx - 9, ty - 5, 1.8, 1.8) + P.ellipse(tx + 4, ty - 5, 1.8, 1.8), (0.1, 0.06, 0.05), 0.9)
    # the patchwork quilt, pulled up to the chin
    quilt = P.poly([(bx + 110, 770), (bx + 140, 756), (bx + 190, 766), (bx + 240, 752), (bx + 300, 734),
                    (bx + 360, 740), (bx + 420, 750), (bx + 470, 744), (bx + 520, 750), (bx + 552, 772),
                    (bx + 566, 820), (bx + 562, 858), (bx + 300, 866), (bx + 100, 862), (bx + 90, 820)])
    pal = np.array([(0.68, 0.43, 0.44), (0.5, 0.57, 0.47), (0.76, 0.62, 0.38), (0.42, 0.47, 0.64), (0.8, 0.74, 0.64)],
                   np.float32)
    u = (P.X - bx) / 44 + 0.25 * (P.Y - 760) / 44
    v = (P.Y - 700) / 40
    idx = (np.floor(u).astype(int) * 7 + np.floor(v).astype(int) * 3) % 5
    light = pal[idx]
    seam = 1 - 0.35 * (np.exp(-((u - np.round(u)) * 44 / 1.3) ** 2) + np.exp(-((v - np.round(v)) * 40 / 1.3) ** 2))
    drape = 1 - 0.12 * np.clip((P.Y - 800) / 60, 0, 1) * (0.5 + 0.5 * np.sin((P.X - bx) / 23))
    P.lit(quilt, light * 0.1, light * 0.85, bed_lamps, amb=0.08, s=10, vol=0.75, tex=seam * drape)
    below = np.zeros_like(quilt)
    below[15:] = quilt[:-15]
    turn = quilt * (1 - below) * np.clip((bx + 250 - P.X) / 14, 0, 1)        # the sheet turned down over it
    P.lit(turn, (0.1, 0.1, 0.14), (0.9, 0.84, 0.76), bed_lamps, amb=0.1, s=3)
    P.paint(P.edge(turn, 1.0) * (P.Y > 760), (0.1, 0.1, 0.14), 0.25)
    # a small arm out over the quilt, holding the bear
    sleeve = P.stroke([(bx + 150, 782), (bx + 180, 780), (bx + 204, 770)], 16, 13)
    P.lit(sleeve, (0.1, 0.12, 0.18), (0.62, 0.72, 0.9), lamps, amb=0.1, s=4,
          tex=1 - 0.2 * (np.sin(P.X * 0.9) > 0.6))
    handm = P.ellipse(bx + 212, 766, 9, 7, rot=-0.4)
    P.lit(handm, *SKIN, lamps, amb=0.1, s=3)


def strip_child(w, h, at):
    return strip_kitchen(w, h, at, child=True)


def strip_placeholder(name):
    cols = dict(monks='#e8d9b5', sailors='#e6dcc6', musicbox='#3a2a1c', parlour='#d8c4a0', radio='#d9d4c8',
                phone='#0f1220', child='#f6f5f1')

    def f(w, h, at):
        return paper(h, w, hexf(cols[name]), sum(map(ord, name)))
    return f


STRIP_FUNCS = dict(shepherd=strip_shepherd, kitchen=strip_kitchen, child=strip_child)


def render_strip(name, w, h, at):
    import scenes_mid
    f = STRIP_FUNCS.get(name) or scenes_mid.STRIPS.get(name) or strip_placeholder(name)
    return (np.clip(f(w, h, at), 0, 1) * 255).astype(np.uint8)


# ------------------------------------------------------------------ threads
def smooth_curve(pts, per=10):
    """Catmull-Rom through the points."""
    if len(pts) < 3:
        return pts
    P = np.array(pts, float)
    P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for tt in np.linspace(0, 1, per, endpoint=False):
            t2, t3 = tt * tt, tt * tt * tt
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * tt + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    out.append(tuple(P[-2]))
    return out


def draw_thread(pil, name, segs, tv, cam):
    d = ImageDraw.Draw(pil, 'RGBA')
    if name == 'shepherd':
        # a whistle glides: a smooth ink curve through the middle of each note
        c = [((x0 + x1) / 2, y) for x0, x1, y, n in segs]
        if segs:
            c = [(segs[0][0], segs[0][2])] + c + [(segs[-1][1], segs[-1][2])]
        pts = smooth_curve(c)
        if len(pts) > 1:
            d.line(pts, fill=(58, 66, 76, 235), width=4, joint='curve')
    elif name in ('kitchen', 'child'):
        # steam: each sung stretch rises and fades as it gets older (breath, memory)
        for x0, x1, y, n in segs:
            age = tv - (n['t'] + n['d'])
            rise = max(age, 0) * 14
            a = int(220 * np.exp(-max(age, 0) / 6))
            col = (255, 232, 190, a) if name == 'kitchen' else (225, 215, 200, int(a * 0.7))
            wob = 6 * np.sin(np.linspace(0, 3, 8) + x0 / 60 + tv)
            xs = np.linspace(x0, x1, 8)
            d.line([(xx, y - rise + ww) for xx, ww in zip(xs, wob)], fill=col, width=4 if name == 'kitchen' else 2)
    else:
        import scenes_mid
        scenes_mid.thread_mid(pil, name, segs, tv, cam, 960)
