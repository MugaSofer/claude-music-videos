"""The six middle keepers' scenes and thread materials."""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

from scenes import paper, hexf, THREAD_Y, THREAD_SPAN
from piano_art import paste_piano, parlour_room


def to_pil(img):
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def to_arr(pil):
    return np.asarray(pil).astype(np.float32) / 255


# ------------------------------------------------------------------ monks: illuminated manuscript
def strip_monks(w, h, at):
    img = paper(h, w, hexf('#e9d8b0'), 21, grain=0.05)
    rng = np.random.default_rng(21)
    fox = gaussian_filter(rng.standard_normal((h // 16 + 1, w // 16 + 1)), 3)
    fox = np.kron(fox, np.ones((16, 16)))[:h, :w]
    img -= ((np.clip(fox, 0, None) * 0.08)[..., None] * np.array([0.3, 0.5, 0.9])).astype(np.float32)
    pil = to_pil(img)
    d = ImageDraw.Draw(pil)
    top, bot = THREAD_Y['monks'] - THREAD_SPAN['monks'] - 30, THREAD_Y['monks'] + 30
    for k in range(4):                                   # red four-line staff
        y = top + k * (bot - top) / 3
        d.line([(0, y), (w, y)], fill=(178, 44, 34), width=3)
    for row in range(4):                                 # lines of script under the staff
        y = bot + 70 + row * 46
        x = 40
        while x < w - 40:
            L = int(rng.uniform(20, 70))
            for j in range(0, L, 7):
                d.line([(x + j, y), (x + j + 3, y - 14)], fill=(60, 40, 30), width=3)
            x += L + int(rng.uniform(14, 26))
    for yb in (60, h - 60):                              # vine borders
        pts = [(x, yb + 14 * np.sin(x / 40)) for x in range(0, w, 6)]
        d.line(pts, fill=(60, 110, 60), width=4)
        for x in range(30, w, 90):
            yy = yb + 14 * np.sin(x / 40)
            d.ellipse([x - 8, yy - 8, x + 8, yy + 8], fill=(178, 44, 34))
    ix = int(at(24.4)) + 150                             # the illuminated initial at the start
    d.rectangle([ix, top - 20, ix + 220, top + 240], fill=(36, 60, 140), outline=(200, 160, 60), width=10)
    d.rectangle([ix + 40, top + 20, ix + 180, top + 60], fill=(214, 172, 70))
    d.rectangle([ix + 90, top + 60, ix + 130, top + 200], fill=(214, 172, 70))
    for k in range(6):
        cx, cy = ix + 30 + k * 32, top + 215
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(178, 44, 34))
    return to_arr(pil)


# ------------------------------------------------------------------ sailors: woodcut
def strip_sailors(w, h, at):
    img = paper(h, w, hexf('#ece2c9'), 31, grain=0.03)
    pil = to_pil(img)
    d = ImageDraw.Draw(pil)
    ink = (26, 22, 20)
    sx, sy = int(at(46)) + 1400, 200                     # carved sun
    for k in range(24):
        a = k / 24 * 2 * np.pi
        d.line([(sx + 70 * np.cos(a), sy + 70 * np.sin(a)), (sx + 150 * np.cos(a), sy + 150 * np.sin(a))],
               fill=ink, width=5)
    d.ellipse([sx - 55, sy - 55, sx + 55, sy + 55], outline=ink, width=8)
    for row in range(11):                                # the sea: carved wave lines
        y0 = 800 + row * 22
        amp = 8 + row * 1.2
        pts = [(x, y0 + amp * np.sin(x / (60 + 5 * row) + row)) for x in range(0, w, 8)]
        d.line(pts, fill=ink, width=5 if row % 3 == 0 else 3)
    d.rectangle([0, 800 + 11 * 22, w, h], fill=ink)
    shx = int(at(53)) + 250                              # a ship mid-scene
    d.polygon([(shx - 260, 760), (shx + 300, 760), (shx + 220, 850), (shx - 200, 850)], fill=ink)
    d.line([(shx, 760), (shx, 220)], fill=ink, width=12)
    for (y0, y1, wd) in ((260, 450, 190), (470, 700, 230)):
        d.polygon([(shx - wd, y0), (shx + wd, y0), (shx + wd - 20, y1), (shx - wd + 20, y1)], outline=ink, width=6)
        for k in range(y0 + 16, y1, 16):
            d.line([(shx - wd + 30, k), (shx + wd - 30, k)], fill=ink, width=2)
    return to_arr(pil)


# ------------------------------------------------------------------ music box: brass cylinder
def strip_musicbox(w, h, at):
    img = paper(h, w, hexf('#2e2016'), 41, grain=0.025)
    y0, y1 = THREAD_Y['musicbox'] - THREAD_SPAN['musicbox'] - 70, THREAD_Y['musicbox'] + 70
    Y = (np.arange(y0, y1) - y0) / (y1 - y0)
    shade = 0.35 + 0.65 * np.sin(np.pi * Y) ** 0.6 + 0.35 * np.exp(-((Y - 0.3) / 0.06) ** 2)
    img[y0:y1] = (hexf('#b8893a')[None, None, :] * shade[:, None, None]).astype(np.float32)
    img[y0:y0 + 6] *= 0.4
    img[y1 - 6:y1] *= 0.4
    rng = np.random.default_rng(41)
    for _ in range(40):
        img[int(rng.uniform(y0 + 10, y1 - 10))] *= 0.85
    pil = to_pil(img)
    d = ImageDraw.Draw(pil)
    d.rectangle([0, y1 + 70, w, h], fill=(58, 38, 24))
    for k in range(0, w, 160):
        d.line([(k, y1 + 70), (k + 40, h)], fill=(70, 48, 30), width=3)
    return to_arr(pil)


# ------------------------------------------------------------------ parlour: sepia lithograph
STAFF_STEP = 13      # px per scale degree (half a staff space)


def strip_parlour(w, h, at):
    img = paper(h, w, hexf('#e3d2ae'), 51, grain=0.04)
    X = np.arange(w)
    Yy = np.arange(h)[:, None]
    motif = (np.sin(X[None, :] / 38) * np.sin(Yy / 38) + np.sin((X[None, :] + Yy) / 55)) * 0.5
    wall = (Yy < 780)
    img -= ((np.clip(motif, 0, 1) * 0.05 * wall)[..., None] * np.array([0.6, 0.8, 1.0])).astype(np.float32)
    pil = to_pil(img)
    d = ImageDraw.Draw(pil)
    ink = (70, 48, 32)
    base = THREAD_Y['parlour']
    for k in range(5):                                   # treble staff in G: bottom line E4 = degree -2
        y = base - STAFF_STEP * (2 * k)
        d.line([(0, y), (w, y)], fill=ink, width=2)
    px = int(at(80)) + 700                               # v5: a lithograph upright with candle sconces (piano_art.py)
    parlour_room(pil, px - 40, w, h)
    arr = paste_piano(to_arr(pil), px - 40, 900)
    Yn = np.linspace(-1, 1, h, dtype=np.float32)[:, None, None]
    return arr * (1 - 0.18 * Yn ** 2)


# ------------------------------------------------------------------ radio: halftone newsprint
def strip_radio(w, h, at):
    img = paper(h, w, hexf('#dcd6c8'), 61, grain=0.03)
    field = np.zeros((h, w), np.float32)
    rx = int(at(114)) + 900
    field[380:900, max(rx, 0):max(rx + 700, 0)] = 0.55
    Yy, Xx = np.ogrid[:h, :w]
    field[((Xx - rx - 350) ** 2 + (Yy - 600) ** 2) < 190 ** 2] = 0.85
    field[((Xx - rx - 350) ** 2 + (Yy - 830) ** 2) < 40 ** 2] = 0.2
    rng = np.random.default_rng(61)
    for c in range(0, w, 420):
        if abs(c - rx) < 800:
            continue
        for r in range(160, 980, 26):
            L = int(rng.uniform(250, 380))
            field[r:r + 10, c + 30:c + 30 + L] = 0.7
    field = gaussian_filter(field, 3)
    cell = 12
    cy, cx = np.mgrid[:h, :w]
    fy, fx = (cy % cell) - cell / 2, (cx % cell) - cell / 2
    rad = np.sqrt(field) * cell * 0.62
    dots = (np.sqrt(fx ** 2 + fy ** 2) < rad).astype(np.float32)
    img *= (1 - 0.85 * dots)[..., None]
    return img


# ------------------------------------------------------------------ phone: pixel art
def strip_phone(w, h, at):
    img = np.zeros((h, w, 3), np.float32) + hexf('#10131f')
    px = 12
    img[::px] += 0.02
    img[:, ::px] += 0.02
    pil = to_pil(img)
    d = ImageDraw.Draw(pil)
    rng = np.random.default_rng(71)
    ox = int(at(130)) - 500
    d.rounded_rectangle([ox, 120, ox + 1500, 980], radius=60, outline=(80, 90, 130), width=14)
    d.rectangle([ox + 60, 200, ox + 1440, 900], fill=(20, 26, 44))
    for k in range(10):
        bx = ox + 100 + int(rng.uniform(0, 1250)) // px * px
        by = 230 + int(rng.uniform(0, 80)) // px * px
        d.rectangle([bx, by, bx + 48, by + 48], fill=(40, 60, 100))
    return to_arr(pil)


STRIPS = dict(monks=strip_monks, sailors=strip_sailors, musicbox=strip_musicbox, parlour=strip_parlour,
              radio=strip_radio, phone=strip_phone)


# ------------------------------------------------------------------ threads
def thread_mid(pil, name, segs, tv, cam, pen_x):
    d = ImageDraw.Draw(pil, 'RGBA')
    if name == 'monks':                    # square neumes joined by thin strokes
        prev = None
        for x0, x1, y, n in segs:
            s = 16
            d.rectangle([x0, y - s / 2, x0 + s, y + s / 2], fill=(30, 22, 18, 255))
            if prev is not None:
                d.line([(x0, prev), (x0, y)], fill=(30, 22, 18, 255), width=3)
            prev = y
    elif name == 'sailors':                # a rope: two twisted strands; crew answers are knots
        pts = []
        for x0, x1, y, n in segs:
            pts += [(x0, y), (x1, y)]
        if len(pts) > 1:
            xs = np.concatenate([np.linspace(pts[i][0], pts[i + 1][0], 12) for i in range(len(pts) - 1)])
            ys = np.concatenate([np.linspace(pts[i][1], pts[i + 1][1], 12) for i in range(len(pts) - 1)])
            for ph, col in ((0, (110, 80, 50, 255)), (np.pi, (160, 120, 80, 255))):
                d.line(list(zip(xs, ys + 5 * np.sin(xs / 7 + ph))), fill=col, width=7)
            for x0, x1, y, n in segs:
                if n.get('crew'):
                    d.ellipse([x0 - 11, y - 11, x0 + 11, y + 11], fill=(90, 62, 40, 255))
    elif name == 'musicbox':               # pins on the drum; the comb at the pen flashes as they pass
        for x0, x1, y, n in segs:
            r = 7
            d.ellipse([x0 - r, y - r, x0 + r, y + r], fill=(250, 238, 200, 255), outline=(90, 60, 20, 255))
        last_end = max(n['t'] + n['d'] for x0, x1, y, n in segs)
        comb = float(np.clip(1.5 - (tv - last_end), 0, 1))    # the comb leaves with the box
        for k in range(12 if comb > 0 else 0):
            ty = THREAD_Y['musicbox'] - k * THREAD_SPAN['musicbox'] / 11
            hit = any(abs(y - ty) < 14 and 0 <= tv - n['t'] < 0.12 for x0, x1, y, n in segs)
            col = (255, 250, 235, int(255 * comb)) if hit else (150, 150, 160, int(255 * comb))
            d.rectangle([pen_x + 4, ty - 4, pen_x + 140, ty + 4], fill=col)
    elif name == 'parlour':                # real notation on the staff
        base = THREAD_Y['parlour']
        ink = (50, 34, 24, 255)
        # the clef and key signature, drawn just left of the first note so they are always in place
        first = min(segs, key=lambda s: s[3]['t'])
        cxp = first[0] - 190
        try:
            from PIL import ImageFont
            d.text((cxp, base - 8 * STAFF_STEP - 58), '\U0001D11E',
                   font=ImageFont.truetype('C:/Windows/Fonts/seguisym.ttf', 150), fill=ink)
        except OSError:
            pass
        sx, sy = cxp + 110, base - 8 * STAFF_STEP        # F sharp on the top line: G major
        for dx in (0, 10):
            d.line([(sx + dx, sy - 16), (sx + dx, sy + 14)], fill=ink, width=2)
        for dy in (-5, 5):
            d.line([(sx - 5, sy + dy + 2), (sx + 15, sy + dy - 2)], fill=ink, width=4)
        for x0, x1, y, n in segs:
            deg = n['deg']
            yy = base - (deg + 2) * STAFF_STEP           # bottom line E4 is degree -2 in G major
            half = n['d'] >= 1.0                         # long notes are open noteheads
            d.ellipse([x0, yy - 9, x0 + 22, yy + 9], fill=None if half else ink, outline=ink, width=3)
            if deg >= 2:                                 # at or above the middle line: stem down, on the left
                d.line([(x0 + 1, yy), (x0 + 1, yy + 62)], fill=ink, width=3)
            else:
                d.line([(x0 + 21, yy), (x0 + 21, yy - 62)], fill=ink, width=3)
            for ledger in range(-4, deg - 1, -2) if deg <= -4 else range(8, deg + 1, 2):
                ly = base - (ledger + 2) * STAFF_STEP
                d.line([(x0 - 6, ly), (x0 + 28, ly)], fill=ink, width=2)
    elif name == 'radio':                  # a waveform: each note a decaying wiggle
        for x0, x1, y, n in segs:
            xs = np.linspace(x0, x1, max(int(x1 - x0), 2))
            amp = 26 * np.exp(-(xs - x0) / 120)
            ys = y + amp * np.sin((xs - x0) / 3.2)
            d.line(list(zip(xs, ys)), fill=(20, 20, 20, 255), width=3)
    elif name == 'phone':                  # pixel steps
        q = 12
        pts = []
        for x0, x1, y, n in segs:
            yq = round(y / q) * q
            pts += [(round(x0 / q) * q, yq), (round(x1 / q) * q, yq)]
        if len(pts) > 1:
            d.line(pts, fill=(120, 255, 200, 255), width=q)
