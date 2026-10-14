"""The parlour's upright piano, drawn as a sepia lithograph (v5; Muga found the v1-v4 box 'simplistic').

A Victorian upright: moulded lid, a fretwork panel over red cloth, brass candle sconces, sheet music on the
desk, a keyboard with real black-key groups, scrolled consoles, an inset lower panel, pedals and a stool.
Drawn 3x supersampled in flat tones, then wood grain, hatched shadow (the lithograph's shading) and
candlelight are added in numpy.

    piano_layer() -> (rgba float32 [H, W, 4] at final size, [(x, y) flame positions in layer pixels])
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

W, H = 640, 520          # layer size in final pixels; the floor line is the bottom edge
S = 3                    # supersampling

INK = (40, 26, 18)
WOOD = (74, 47, 31)
WOOD_D = (52, 32, 21)
WOOD_L = (112, 76, 50)
IVORY = (236, 226, 204)
EBONY = (30, 22, 18)
BRASS = (196, 156, 82)
BRASS_D = (128, 96, 46)
CLOTH = (120, 44, 34)
PAPER = (232, 220, 192)
VELVET = (110, 38, 32)


def _s(v):
    return [c * S for c in v]


def piano_layer():
    img = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # tag image: which pixels are wood (for grain) and where the hatched shadows go
    tag = Image.new('L', (W * S, H * S), 0)
    t = ImageDraw.Draw(tag)

    def rect(box, fill, outline=INK, width=1, wood=True):
        d.rectangle(_s(box), fill=fill, outline=outline, width=width * S)
        if wood:
            t.rectangle(_s(box), fill=1)

    def poly(pts, fill, outline=INK, width=1, wood=True):
        p = [(x * S, y * S) for x, y in pts]
        d.polygon(p, fill=fill, outline=outline, width=width * S)
        if wood:
            t.polygon(p, fill=1)

    def line(pts, fill=INK, width=1):
        d.line([(x * S, y * S) for x, y in pts], fill=fill, width=max(1, int(width * S)))

    def ell(box, fill, outline=INK, width=1):
        d.ellipse(_s(box), fill=fill, outline=outline, width=width * S)

    # ---- floor shadow
    sh = Image.new('L', (W * S, H * S), 0)
    ImageDraw.Draw(sh).ellipse(_s([10, 500, 560, 540]), fill=150)

    # ---- the case
    rect([52, 204, 468, 332], WOOD)                                  # upper case
    rect([60, 214, 460, 324], WOOD_D, width=1)                       # recessed frame
    rect([92, 224, 428, 300], CLOTH, wood=False)                     # red cloth behind the fretwork
    # fretwork: a band of linked scrolls cut from the wood, over the cloth
    fx0, fx1, fy0, fy1 = 92, 428, 224, 300
    fret = Image.new('L', ((fx1 - fx0) * S, (fy1 - fy0) * S), 255)
    fd = ImageDraw.Draw(fret)
    cy = (fy1 - fy0) / 2
    for k in range(9):
        cx = 18 + k * 37.5
        for r, wdt in ((15, 3.2), (7, 2.4)):
            fd.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], outline=0, width=int(wdt * S))
        fd.ellipse([(cx - 2) * S, (cy - 2) * S, (cx + 2) * S, (cy + 2) * S], fill=0)
        for sgn in (-1, 1):                                           # leaf sprays between the rings
            x0 = cx + 18.75
            fd.arc([(x0 - 12) * S, (cy + sgn * 6 - 22) * S, (x0 + 12) * S, (cy + sgn * 6 + 22) * S],
                   200 if sgn < 0 else 20, 340 if sgn < 0 else 160, fill=0, width=int(2.2 * S))
    fd.rectangle([0, 0, fret.width - 1, fret.height - 1], outline=0, width=4 * S)
    fret_a = np.asarray(fret) < 128                                  # the tracery is wood; the rest is cut away to the cloth
    arr = np.asarray(img).copy()
    sub = arr[fy0 * S:fy1 * S, fx0 * S:fx1 * S]
    sub[fret_a] = (*WOOD, 255)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    tag_a = np.asarray(tag).copy()
    tag_a[fy0 * S:fy1 * S, fx0 * S:fx1 * S][fret_a] = 1
    tag = Image.fromarray(tag_a)
    t = ImageDraw.Draw(tag)
    line([(92, 224), (428, 224), (428, 300), (92, 300), (92, 224)], INK, 1)

    # lid with a moulded, overhanging edge
    rect([34, 190, 486, 198], WOOD_L)
    rect([40, 198, 480, 206], WOOD)
    line([(36, 191), (484, 191)], (168, 124, 84), 1.2)               # lit top edge

    # sheet music on the desk, leaning back
    poly([(176, 236), (258, 233), (262, 302), (172, 302)], PAPER, wood=False)
    poly([(262, 233), (346, 236), (350, 302), (262, 302)], PAPER, wood=False)
    line([(261, 233), (262, 302)], (170, 150, 120), 1)
    for page, (a, b) in enumerate(((182, 252), (270, 342))):
        for row in range(4):
            y0 = 246 + row * 14
            for k in range(5):
                line([(a, y0 + k * 1.6), (b, y0 + k * 1.6)], (130, 110, 90), 0.4)
            rng = np.random.default_rng(page * 10 + row)
            for x in np.arange(a + 6, b - 4, 7.5):
                y = y0 + rng.integers(0, 6) * 0.8
                ell([x - 1.2, y - 0.9, x + 1.2, y + 0.9], (60, 44, 34), outline=None)
                line([(x + 1.1, y), (x + 1.1, y - 5)], (60, 44, 34), 0.4)
    rect([150, 300, 370, 308], WOOD_L)                               # the desk ledge

    # candle sconces: brass arms swinging out from the case, cups, candles, flames
    flames = []
    for side in (-1, 1):
        bx = 62 if side < 0 else 458
        ex = bx + side * 46
        ell([bx - 6, 252, bx + 6, 264], BRASS, BRASS_D)                # the mount
        line([(bx, 258), (bx + side * 18, 262), (ex - side * 6, 258), (ex, 250)], BRASS_D, 3.2)
        line([(bx, 257), (bx + side * 18, 261), (ex - side * 6, 257), (ex, 249)], BRASS, 1.8)
        ell([ex - 13, 244, ex + 13, 252], BRASS, BRASS_D)              # drip pan
        rect([ex - 5, 196, ex + 5, 246], (236, 228, 206), outline=(150, 130, 100), wood=False)   # candle
        poly([(ex - 3, 197), (ex + 3, 197), (ex + 2, 200), (ex - 2, 200)], (250, 244, 230), outline=None, wood=False)
        line([(ex, 196), (ex, 191)], INK, 0.6)                        # wick
        poly([(ex, 172), (ex + 3.6, 184), (ex + 2, 191), (ex - 2, 191), (ex - 3.6, 184)], (255, 214, 120),
             outline=None, wood=False)
        poly([(ex, 180), (ex + 1.6, 186), (ex, 190), (ex - 1.6, 186)], (255, 246, 210), outline=None, wood=False)
        flames.append((ex, 184))

    # fallboard (open) and the nameboard's gilt line
    rect([52, 332, 468, 342], WOOD_D)
    line([(200, 337), (320, 337)], BRASS, 0.8)
    # cheek blocks
    rect([52, 342, 68, 376], WOOD)
    rect([452, 342, 468, 376], WOOD)
    # keys: white, then black in 2-3 groups
    kx0, kx1, ky0, ky1 = 68, 452, 342, 374
    n = 36
    kw = (kx1 - kx0) / n
    d.rectangle(_s([kx0, ky0, kx1, ky1]), fill=IVORY)
    for i in range(n + 1):
        line([(kx0 + i * kw, ky0), (kx0 + i * kw, ky1)], (150, 136, 112), 0.5)
    line([(kx0, ky1 - 0.5), (kx1, ky1 - 0.5)], (170, 156, 130), 0.8)   # key fronts
    for i in range(n - 1):
        if i % 7 in (0, 1, 3, 4, 5):                                 # C# D#  F# G# A#
            x = kx0 + (i + 1) * kw
            d.rectangle(_s([x - kw * 0.3, ky0, x + kw * 0.3, ky0 + 19]), fill=EBONY)
            line([(x - kw * 0.15, ky0 + 2), (x - kw * 0.15, ky0 + 16)], (90, 76, 66), 0.5)
    # keybed front (key slip), moulded
    rect([42, 374, 478, 392], WOOD)
    line([(44, 375), (476, 375)], (150, 108, 70), 1)
    line([(42, 392), (478, 392)], INK, 1.4)

    # lower case and inset panel with a carved oval
    rect([60, 392, 460, 502], WOOD)
    rect([98, 404, 422, 490], WOOD_D)
    rect([104, 410, 416, 484], WOOD)
    ell([206, 422, 314, 472], WOOD_D)
    ell([212, 427, 308, 467], WOOD)
    for k in range(6):                                                # carved petals in the oval
        a = k * np.pi / 3
        cx, cy = 260 + 30 * np.cos(a), 447 + 13 * np.sin(a)
        ell([cx - 7, cy - 3.5, cx + 7, cy + 3.5], WOOD_L, WOOD_D)
    ell([253, 441, 267, 453], WOOD_L, WOOD_D)
    # scrolled consoles under the keybed, down to toe blocks
    for side in (-1, 1):
        x = 50 if side < 0 else 470
        pts = []
        for u in np.linspace(0, 1, 30):                              # an S-curve bracket
            pts.append((x + side * (-4 + 10 * np.sin(u * np.pi * 1.5)), 392 + u * 110))
        inner = [(px - side * 14, py) for px, py in reversed(pts)]
        poly(pts + inner, WOOD_L if side < 0 else WOOD)
        ell([x - 9 - side * 5, 392, x + 9 - side * 5, 410], WOOD_L, INK)   # the scroll's volute
        ell([x - 4 - side * 5, 397, x + 4 - side * 5, 405], WOOD_D, None)
        rect([x - 16 - side * 4, 502, x + 12 - side * 4, 512], WOOD_D)
    rect([46, 502, 474, 514], WOOD_D)                                  # plinth
    for x in (244, 276):                                               # pedals
        poly([(x - 5, 505), (x + 5, 505), (x + 7, 516), (x - 7, 516)], BRASS, BRASS_D, wood=False)

    # the stool: a round velvet seat on a turned column with three splayed feet
    cx = 330
    line([(cx, 452), (cx - 38, 516)], INK, 5)
    line([(cx, 452), (cx - 38, 516)], WOOD_L, 3)
    line([(cx, 452), (cx + 38, 516)], INK, 5)
    line([(cx, 452), (cx + 38, 516)], WOOD, 3)
    line([(cx, 452), (cx + 4, 518)], INK, 4)
    rect([cx - 7, 438, cx + 7, 486], WOOD)
    for y in (452, 468):
        ell([cx - 10, y - 4, cx + 10, y + 4], WOOD_L, INK)
    ell([cx - 52, 424, cx + 52, 446], WOOD, INK)                       # seat rim
    ell([cx - 50, 418, cx + 50, 438], VELVET, INK)                     # velvet top
    ell([cx - 30, 421, cx + 6, 429], (150, 62, 50), None)

    # ---- to numpy at final size
    rgba = np.asarray(img.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    wood = np.asarray(tag.resize((W, H), Image.BILINEAR)).astype(np.float32)
    shadow_floor = np.asarray(sh.resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
    rgb, a = rgba[..., :3], rgba[..., 3:]

    rng = np.random.default_rng(303)
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    grain = gaussian_filter(rng.standard_normal((H, W)), (0.7, 26))   # long horizontal figure
    grain = grain / (np.abs(grain).max() + 1e-6)
    figure = np.sin(xx / 9 + 3 * gaussian_filter(rng.standard_normal((H, W)), 30) * 40) * 0.5
    rgb *= 1 + (0.14 * grain + 0.04 * figure)[..., None] * np.clip(wood, 0, 1)[..., None]

    # lithograph shading: light from the upper left, deeper to the right and under every overhang
    shade = np.clip((xx - 60) / 420, 0, 1) * 0.55
    for y0, y1 in ((206, 218), (308, 316), (392, 412), (514, 520)):   # cast shadows below lid, desk, keybed
        shade = np.maximum(shade, np.clip(1 - (yy - y0) / (y1 - y0), 0, 1) * (yy >= y0) * 0.9)
    hatch = ((xx + yy) % 4.0 < 1.3).astype(np.float32)               # 45 degree hatching
    cross = ((xx - yy) % 5.0 < 1.1).astype(np.float32)               # cross-hatching in the deepest shade
    ink = np.clip(hatch * shade + cross * np.clip(shade - 0.55, 0, 1) * 1.6, 0, 1) * 0.55
    rgb *= (1 - ink * np.clip(wood, 0, 1))[..., None]

    # candlelight: warm on the case near each flame, and a halo (returned as glow for the wall)
    glow = np.zeros((H, W), np.float32)
    for fx, fy in flames:
        r2 = (xx - fx) ** 2 + (yy - fy) ** 2
        glow += np.exp(-r2 / (2 * 70 ** 2)) * 0.55 + np.exp(-r2 / (2 * 14 ** 2)) * 0.6
    rgb += (glow[..., None] * np.array([0.30, 0.20, 0.08], np.float32)) * (a > 0.5)
    rgb = np.clip(rgb, 0, 1)

    # premultiply-free output; the floor shadow is a separate soft alpha under the piano
    out = np.concatenate([rgb, a], -1)
    floor = shadow_floor * 0.45 * (1 - a[..., 0])
    out[..., :3] = np.where(floor[..., None] > 0, out[..., :3] * (a > 0) + (1 - (a > 0)) * 0.0, out[..., :3])
    out[..., 3] = np.maximum(a[..., 0], floor)
    return out, glow, flames


def paste_piano(img, x, y_floor):
    """Composite onto img (float32 HxWx3) with the layer's bottom edge on y_floor; adds the wall glow."""
    lay, glow, flames = piano_layer()
    h, w = img.shape[:2]
    x0, y0 = int(x), int(y_floor) - H
    sx0, sy0 = max(0, -x0), max(0, -y0)
    ex, ey = min(w, x0 + W), min(h, y0 + H)
    if ex <= x0 + sx0 or ey <= y0 + sy0:
        return img
    wx0, wy0 = max(0, x0 - 300), max(0, y0 - 300)          # candle halo on the wall, in a window round the piano
    wx1, wy1 = min(w, x0 + W + 300), min(h, y0 + H)
    yy, xx = np.mgrid[wy0:wy1, wx0:wx1].astype(np.float32)
    halo = np.zeros(yy.shape, np.float32)
    for fx, fy in flames:
        r2 = (xx - x0 - fx) ** 2 + (yy - y0 - fy) ** 2
        halo += np.exp(-r2 / (2 * 90 ** 2)) * 0.5 + np.exp(-r2 / (2 * 18 ** 2)) * 0.5
    img[wy0:wy1, wx0:wx1] += halo[..., None] * np.array([0.16, 0.10, 0.03], np.float32)
    L = lay[sy0:ey - y0, sx0:ex - x0]
    reg = img[y0 + sy0:ey, x0 + sx0:ex]
    reg[:] = reg * (1 - L[..., 3:]) + L[..., :3] * L[..., 3:]
    np.clip(img[wy0:wy1, wx0:wx1], 0, 1, out=img[wy0:wy1, wx0:wx1])
    return img


def parlour_room(pil, px, w, h):
    """Around the piano (px = the layer's left edge): floorboards, a rug, and an oval silhouette portrait."""
    from PIL import ImageDraw as _D
    d = _D.Draw(pil)
    rng = np.random.default_rng(304)
    d.rectangle([0, 900, w, h], fill=(92, 64, 42))                     # floorboards, receding
    y, k = 900.0, 0
    while y < h:
        gap = 10 + k * 5.5
        d.line([(0, y), (w, y)], fill=(58, 38, 24), width=2)
        for x in range(int(rng.uniform(0, 300)), w, int(rng.uniform(260, 420))):   # board ends
            d.line([(x, y), (x, y + gap)], fill=(64, 42, 28), width=2)
        y += gap
        k += 1
    rx0, rx1 = px - 40, px + 680                                         # a patterned rug in front of the piano
    d.polygon([(rx0 + 40, 902), (rx1 - 40, 902), (rx1, 990), (rx0, 990)], fill=(118, 42, 34), outline=(60, 24, 18))
    d.polygon([(rx0 + 56, 908), (rx1 - 56, 908), (rx1 - 22, 982), (rx0 + 22, 982)], outline=(196, 150, 84), width=3)
    for i in range(13):                                                  # a row of medallions, foreshortened
        cx = rx0 + 70 + i * (rx1 - rx0 - 140) / 12
        d.ellipse([cx - 14, 938, cx + 14, 954], outline=(196, 150, 84), width=2)
        d.ellipse([cx - 4, 943, cx + 4, 949], fill=(60, 30, 50))
    for x in range(rx0, rx1, 9):                                         # fringe
        d.line([(x, 990), (x + 2, 998)], fill=(210, 190, 150), width=1)
    cx, cy = px + 260, 255                                               # the portrait: oval frame, cord, a profile
    ey = cy - 112 * np.sqrt(1 - (50 / 86) ** 2) + 5                     # the cord ends on screw eyes in the frame's rim
    d.line([(cx, 110), (cx - 50, ey)], fill=(70, 48, 32), width=2)
    d.line([(cx, 110), (cx + 50, ey)], fill=(70, 48, 32), width=2)
    d.ellipse([cx - 5, 105, cx + 5, 115], fill=(150, 116, 60))
    d.ellipse([cx - 86, cy - 112, cx + 86, cy + 112], fill=(160, 120, 60), outline=(70, 48, 32), width=3)
    d.ellipse([cx - 74, cy - 100, cx + 74, cy + 100], fill=(110, 78, 40))
    d.ellipse([cx - 66, cy - 92, cx + 66, cy + 92], fill=(238, 228, 204))
    for sx in (-50, 50):
        d.ellipse([cx + sx - 4, ey - 4, cx + sx + 4, ey + 4], outline=(150, 116, 60), width=2)
    prof = np.array([(-10, -64), (6, -64), (18, -56), (24, -44), (26, -32), (27, -24), (25, -19), (33, -8),
                     (27, -4), (28, 2), (26, 6), (27, 10), (23, 14), (23, 20), (16, 26), (10, 30), (10, 40),
                     (16, 50), (34, 60), (44, 72), (46, 84), (-46, 84), (-44, 70), (-34, 56), (-22, 46),
                     (-20, 30), (-28, 18), (-34, 0), (-36, -20), (-32, -42), (-22, -58)], float)
    from scipy.interpolate import splprep, splev                         # a smooth cut-paper bust facing right
    tck, _ = splprep([prof[:, 0], prof[:, 1]], s=6, per=True)
    xs, ys = splev(np.linspace(0, 1, 400), tck)
    d.polygon([(cx + x, cy + y) for x, y in zip(xs, ys)], fill=(34, 24, 20))
    d.ellipse([cx - 52, cy - 46, cx - 26, cy - 18], fill=(34, 24, 20))   # the bun
    return pil
