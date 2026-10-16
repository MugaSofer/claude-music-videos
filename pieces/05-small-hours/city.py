"""Small Hours: a paper-cutout night city. Each keeper of the night is a vignette along a
long panorama; the camera drifts between them. Timing is supplied later (cues.json from the
song); this module only knows world positions and how each vignette animates in local time.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
WORLD_W = 9600
GROUND = 880
rng = np.random.default_rng(55)

INK = (18, 20, 38)
NIGHT_TOP, NIGHT_LOW = (14, 18, 44), (48, 44, 88)
WARM = (255, 204, 120)


def paper_texture(w, h, seed=1, amt=10):
    g = np.random.default_rng(seed)
    t = g.normal(0, 1, (h // 3 + 1, w // 3 + 1))
    t = np.kron(t, np.ones((3, 3)))[:h, :w]
    return (t * amt).astype(np.float32)


PAPER = paper_texture(W, H)


class Cut:
    """A paper-cut layer: shapes drawn in world coordinates, rendered with a soft drop shadow."""

    def __init__(self, depth, shadow=8):
        self.depth = depth            # parallax: 1 = moves with the camera, <1 = farther
        self.shadow = shadow
        self.items = []               # (kind, coords, colour)
        self.windows = []             # (x0, y0, x1, y1, unlit colour): lit or not is decided per frame
        self.window_state = None      # callable(index) -> brightness 0..1, set by the film

    def poly(self, pts, col):
        self.items.append(('poly', pts, col))

    def rect(self, x0, y0, x1, y1, col):
        self.items.append(('poly', [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col))

    def ellipse(self, x0, y0, x1, y1, col):
        self.items.append(('ell', (x0, y0, x1, y1), col))

    def render(self, base, cam_x, zoom, extra=None, cam_y=H / 2):
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        off = cam_x * self.depth
        cy = H / 2 + (cam_y - H / 2) * self.depth          # vertical camera, with parallax too

        def tr(x, y):
            return ((x - off - W / 2) * zoom + W / 2, (y - cy) * zoom + H / 2)
        items = list(self.items)
        if self.windows:
            n = len(self.windows)
            state = self.window_state(n) if self.window_state else np.zeros(n)
            for (x0, y0, x1, y1, dark), s in zip(self.windows, state):
                col = tuple(int(d * (1 - s) + w * s) for d, w in zip(dark, WARM))
                items.append(('poly', [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col))
        for kind, c, col in items + (extra or []):
            if kind == 'poly':
                pts = [tr(x, y) for x, y in c]
                if max(p[0] for p in pts) < -50 or min(p[0] for p in pts) > W + 50:
                    continue
                d.polygon(pts, fill=col)
            else:
                a, b = tr(c[0], c[1]), tr(c[2], c[3])
                if b[0] < -50 or a[0] > W + 50:
                    continue
                d.ellipse([a[0], a[1], b[0], b[1]], fill=col)
        if self.shadow:
            sh = layer.split()[3].filter(ImageFilter.GaussianBlur(self.shadow * zoom * 0.8))
            shadow = Image.new('RGBA', (W, H), (0, 0, 12, 0))
            shadow.putalpha(sh.point(lambda v: int(v * 0.55)))
            base.alpha_composite(shadow, (int(self.shadow * zoom * 0.6), int(self.shadow * zoom * 0.8)))
        base.alpha_composite(layer)


def building(layer, x, w, h, col, lit_frac, seed, win=(26, 34), gap=(18, 22)):
    g = np.random.default_rng(abs(seed) + 10000)
    top = int(GROUND - h)
    layer.rect(x, top, x + w, GROUND, col)
    if g.random() < 0.4:                                        # a pitched roof or a water tank
        layer.poly([(x - 6, top), (x + w / 2, top - 40), (x + w + 6, top)], col)
    wx0 = x + gap[0]
    lits = []
    for y in range(top + 30, GROUND - 60, win[1] + gap[1]):
        for xx in range(int(wx0), int(x + w - win[0] - 10), win[0] + gap[0]):
            layer.windows.append((xx, y, xx + win[0], y + win[1], tuple(int(v * 0.6) for v in col)))
            lits.append((xx, y))
    return lits


def build_world():
    far, mid, near, street = Cut(0.35, 5), Cut(0.65, 7), Cut(1.0, 9), Cut(1.0, 6)
    x = -400
    while x < WORLD_W * 0.35 + 2400:                             # far skyline
        w = rng.uniform(80, 220)
        building(far, x, w, rng.uniform(260, 560), (40, 44, 86), 0.08, int(x) + 1, win=(10, 14), gap=(10, 12))
        x += w + rng.uniform(4, 30)
    x = -400
    while x < WORLD_W * 0.65 + 2400:                             # middle blocks
        w = rng.uniform(140, 300)
        building(mid, x, w, rng.uniform(220, 460), (30, 32, 66), 0.14, int(x) + 7, win=(16, 22), gap=(14, 16))
        x += w + rng.uniform(20, 80)
    street.rect(-400, GROUND, WORLD_W + 2400, H + 400, (26, 26, 40))           # the road
    for xx in range(-400, WORLD_W + 2400, 160):                  # kerb stones
        street.rect(xx, GROUND - 4, xx + 150, GROUND + 6, (58, 56, 74))
    return far, mid, near, street


FAR, MID, NEAR, STREET = build_world()

# the keepers of the night: (name, world x of the vignette's centre)
VIGNETTES = [('baker', 900), ('bus', 2000), ('nurse', 3000), ('fox', 3900), ('lorry', 5200), ('dad', 6200),
             ('lines', 7200), ('tower', 8300)]
VX = dict(VIGNETTES)


def vignette_items(name, tl):
    """Shapes for one vignette at local time tl (seconds since it began). Returns cut-items in world coords."""
    it = []
    cx = VX[name]
    ink = INK
    if name == 'baker':
        it += [('poly', [(cx - 260, 520), (cx + 260, 520), (cx + 260, GROUND), (cx - 260, GROUND)], (60, 38, 34)),
               ('poly', [(cx - 200, 600), (cx + 200, 600), (cx + 200, 820), (cx - 200, 820)], WARM)]
        knead = np.sin(tl * 5) * 10
        it += [('ell', (cx - 40, 650, cx + 10, 700), ink),
               ('poly', [(cx - 60, 700), (cx + 30, 700), (cx + 50, 820), (cx - 80, 820)], ink),
               ('poly', [(cx + 20, 720), (cx + 90 + knead, 770), (cx + 80 + knead, 785), (cx + 10, 740)], ink),
               ('ell', (cx + 70 + knead, 770, cx + 150 + knead, 800), (236, 214, 176))]            # the dough
        it += [('poly', [(cx - 240, 500), (cx + 240, 500), (cx + 220, 470), (cx - 220, 470)], (150, 60, 50))]
    elif name == 'bus':
        bx = cx - 600 + tl * 120                                                            # the bus drives by
        it += [('poly', [(bx - 220, 720), (bx + 220, 720), (bx + 230, 860), (bx - 230, 860)], (170, 40, 40))]
        for k in range(6):
            it += [('poly', [(bx - 200 + k * 70, 740), (bx - 150 + k * 70, 740), (bx - 150 + k * 70, 790),
                             (bx - 200 + k * 70, 790)], (255, 226, 160))]
        it += [('ell', (bx - 170, 840, bx - 120, 890), ink), ('ell', (bx + 110, 840, bx + 160, 890), ink)]
    elif name == 'nurse':
        it += [('poly', [(cx - 300, 300), (cx + 300, 300), (cx + 300, GROUND), (cx - 300, GROUND)], (200, 206, 214))]
        it += [('poly', [(cx - 120, 420), (cx + 120, 420), (cx + 120, 580), (cx - 120, 580)], (220, 240, 236))]
        it += [('ell', (cx - 30, 450, cx + 10, 490), ink), ('poly', [(cx - 50, 492), (cx + 30, 492), (cx + 40, 580), (cx - 60, 580)], ink)]
        breath = 1 + 0.04 * np.sin(tl * 2.2)                                               # the patient breathes
        it += [('ell', (cx + 40, 540 - 10 * breath, cx + 110, 560 + 10 * breath), (236, 236, 240))]
    elif name == 'fox':
        fx = cx - 200 + tl * 40
        it += [('poly', [(cx + 120, 780), (cx + 220, 780), (cx + 210, GROUND), (cx + 130, GROUND)], (50, 70, 60)),
               ('poly', [(cx + 240, 790), (cx + 330, 790), (cx + 322, GROUND), (cx + 248, GROUND)], (50, 70, 60))]
        step = np.sin(tl * 6) * 6
        body = (212, 110, 50)
        it += [('ell', (fx - 60, 820, fx + 40, 856), body),
               ('poly', [(fx + 30, 820), (fx + 70, 800), (fx + 80, 830), (fx + 40, 840)], body),
               ('poly', [(fx + 55, 802), (fx + 62, 786), (fx + 68, 804)], body),
               ('poly', [(fx - 60, 836), (fx - 120, 820 + step), (fx - 110, 846)], body),
               ('poly', [(fx - 40, 850), (fx - 36 + step, GROUND), (fx - 30 + step, GROUND), (fx - 30, 850)], ink),
               ('poly', [(fx + 20, 850), (fx + 24 - step, GROUND), (fx + 30 - step, GROUND), (fx + 30, 850)], ink)]
    elif name == 'lorry':
        lx = cx - 300 + tl * 60
        it += [('poly', [(cx - 700, 700), (cx + 700, 700), (cx + 700, 720), (cx - 700, 720)], (60, 60, 86))]   # flyover
        it += [('poly', [(lx - 160, 600), (lx + 60, 600), (lx + 60, 700), (lx - 160, 700)], (200, 200, 210)),
               ('poly', [(lx + 60, 630), (lx + 130, 630), (lx + 140, 700), (lx + 60, 700)], (60, 90, 150)),
               ('poly', [(lx + 85, 640), (lx + 120, 640), (lx + 124, 664), (lx + 85, 664)], WARM)]
        it += [('poly', [(lx + 140, 670), (lx + 420, 650), (lx + 420, 700), (lx + 140, 700)], (255, 240, 190, 70))]  # headlight
    elif name == 'dad':
        it += [('poly', [(cx - 280, 460), (cx + 280, 460), (cx + 280, GROUND), (cx - 280, GROUND)], (70, 56, 64)),
               ('poly', [(cx - 180, 520), (cx + 180, 520), (cx + 180, 720), (cx - 180, 720)], WARM)]
        sway = np.sin(tl * 1.6) * 8
        it += [('ell', (cx - 30 + sway, 560, cx + 20 + sway, 610), ink),
               ('poly', [(cx - 60 + sway, 612), (cx + 50 + sway, 612), (cx + 60, 720), (cx - 70, 720)], ink),
               ('ell', (cx - 10 + sway, 630, cx + 50 + sway, 672), (238, 230, 214))]           # the baby, held
    elif name == 'lines':
        mx = cx - 500 + tl * 50
        it += [('poly', [(cx - 500, 950), (mx, 950), (mx, 962), (cx - 500, 962)], (246, 246, 236))]   # the new white line
        it += [('poly', [(mx - 20, 890), (mx + 70, 890), (mx + 70, 948), (mx - 20, 948)], (230, 170, 40)),
               ('ell', (mx + 10, 840, mx + 40, 870), ink), ('poly', [(mx + 5, 870), (mx + 45, 870), (mx + 40, 900), (mx + 10, 900)], ink)]
    elif name == 'tower':
        it += [('poly', [(cx - 170, 140), (cx + 170, 140), (cx + 170, GROUND), (cx - 170, GROUND)], (36, 38, 70))]
        for yy in range(170, GROUND - 60, 56):
            for xx in range(-140, 130, 56):
                last = (yy == 394 and xx == 28)
                it += [('poly', [(cx + xx, yy), (cx + xx + 30, yy), (cx + xx + 30, yy + 36), (cx + xx, yy + 36)],
                        WARM if last else (26, 28, 52))]
    return it


def sky(cam_x, dawn):
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array(NIGHT_TOP) * (1 - dawn) + np.array([120, 150, 200]) * dawn
    low = np.array(NIGHT_LOW) * (1 - dawn) + np.array([250, 196, 150]) * dawn
    img = top * (1 - y) + low * y
    img = np.broadcast_to(img, (H, W, 3)) + PAPER[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')


def frame(cam_x, zoom, dawn, active, cam_y=H / 2):
    """active: list of (vignette name, local time). cam_y: world y at the screen centre (540 = level)."""
    img = sky(cam_x, dawn)
    # the moon, far away, barely moving
    mx = 1500 - cam_x * 0.05
    if dawn < 1:                                               # v4: blended on its own overlay; drawn straight
        moon = Image.new('RGBA', img.size, (0, 0, 0, 0))      # into the sky, its fading alpha cut a hole in it
        ImageDraw.Draw(moon).ellipse([mx - 50, 140 + 300 * dawn, mx + 50, 240 + 300 * dawn],
                                     fill=(240, 236, 214, int(255 * (1 - dawn))))
        img.alpha_composite(moon)
    FAR.render(img, cam_x, zoom, cam_y=cam_y)
    MID.render(img, cam_x, zoom, cam_y=cam_y)
    STREET.render(img, cam_x, zoom, cam_y=cam_y)               # the road first, so vignettes can draw on it
    import vignettes
    extra = []
    for name, x in VIGNETTES:                                  # every vignette's set is always there
        mod = vignettes.load(name)
        if mod is not None:
            extra += mod.set_items(x, GROUND)
    for name, tl in active:                                    # the living parts, when active
        mod = vignettes.load(name)
        extra += mod.action_items(tl, VX[name], GROUND) if mod is not None else vignette_items(name, tl)
    NEAR.render(img, cam_x, zoom, extra, cam_y=cam_y)
    return img.convert('RGB')
