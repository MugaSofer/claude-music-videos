"""Maintenance v5: the gloves, painted properly (Muga: the old ones were "a bit MS Paint").

Both gloves share one shape, a canvas work glove hanging from its cuff with the palm toward us:
a flared cuff, a palm, four fingers of different lengths with a little splay, and an angled thumb.
Everything is painted once at high resolution in glove units (GU) on a local canvas and then pasted
through the scene's view, so it stays crisp at the closing zoom.

  real_sprite()           -> RGBA: canvas glove with volume shading, weave, a knit cuff, seams, a leather
                             palm patch, creases and soft soil wear
  replica_sprite(u, t)    -> RGBA: the leaf glove at growth fraction u (0..1): stems first, then ~900
                             individually painted leaves (light and dark halves, midrib, small shadow)
                             following the fingers, born from the cuff down to the fingertips
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import distance_transform_edt

PX = 4.2                         # sprite pixels per glove unit
X0, Y0, X1, Y1 = -96, -6, 128, 310   # local canvas in GU (hook at 0, 0)
SW, SH = int((X1 - X0) * PX), int((Y1 - Y0) * PX)
# fingers: (centre x at the palm, length below the palm, splay in degrees, width)
FINGERS = [(-48, 70, -7, 30), (-16, 92, -2.5, 31), (16, 100, 0, 31), (48, 82, 3.5, 30)]
PALM_TOP, PALM_BOT = 74, 186
THUMB = ((58, 112), (100, 176), 33)          # base, tip, width


def P(x, y):
    """GU -> sprite pixels."""
    return ((x - X0) * PX, (y - Y0) * PX)


def finger_line(k):
    cx, L, ang, w = FINGERS[k]
    a = math.radians(ang)
    base = (cx, PALM_BOT - 14)
    tip = (cx + math.sin(a) * L, PALM_BOT + L * math.cos(a))
    return base, tip, w


def capsule(d, a, b, w, fill):
    ax, ay = P(*a)
    bx, by = P(*b)
    r = w * PX / 2
    d.line([(ax, ay), (bx, by)], fill=fill, width=int(2 * r))
    for x, y in ((ax, ay), (bx, by)):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def shape_mask(ss=2):
    """The glove silhouette as an L mask (antialiased by supersampling)."""
    big = Image.new("L", (SW * ss, SH * ss), 0)
    d = ImageDraw.Draw(big)

    def Q(x, y):
        return ((x - X0) * PX * ss, (y - Y0) * PX * ss)
    # cuff (slightly flared, rounded) and palm
    d.rounded_rectangle([*Q(-72, 4), *Q(72, 82)], radius=int(10 * PX * ss), fill=255)
    d.polygon([Q(-72, 70), Q(72, 70), Q(66, PALM_TOP + 20), Q(-66, PALM_TOP + 20)], fill=255)
    d.rounded_rectangle([*Q(-66, PALM_TOP), *Q(66, PALM_BOT + 6)], radius=int(24 * PX * ss), fill=255)
    for k in range(4):
        a, b, w = finger_line(k)
        ax, ay = Q(*a)
        bx, by = Q(*b)
        r = w * PX * ss / 2
        d.line([(ax, ay), (bx, by)], fill=255, width=int(2 * r))
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=255)
    (tx0, ty0), (tx1, ty1), tw = THUMB
    ax, ay = Q(tx0, ty0)
    bx, by = Q(tx1, ty1)
    r = tw * PX * ss / 2
    d.line([(ax, ay), (bx, by)], fill=255, width=int(2 * r))
    d.ellipse([bx - r, by - r, bx + r, by + r], fill=255)
    return big.resize((SW, SH), Image.LANCZOS)


MASK = shape_mask()
M = np.asarray(MASK).astype(np.float32) / 255
DIST = distance_transform_edt(M > 0.5) / PX          # GU from the edge, inside the glove
YY, XX = np.mgrid[0:SH, 0:SW]
GX, GY = XX / PX + X0, YY / PX + Y0                  # GU coordinates of every sprite pixel


def real_sprite():
    """The gardener's canvas glove."""
    rng = np.random.default_rng(3)
    base = np.array([196, 180, 140], np.float32)
    vol = 0.62 + 0.38 * np.clip(DIST / 10.0, 0, 1) ** 0.55                       # rounded volume, darker rim
    key = 1.0 + 0.10 * np.clip((-GX + 40) / 160, -1, 1) - 0.06 * (GY / 300)     # lit from the upper left
    weave = 1 + 0.035 * (np.sin(GX * 2.6) * np.sin(GY * 2.6)) + rng.normal(0, 0.018, GX.shape)
    col = base[None, None, :] * (vol * key * weave)[..., None]
    cuff = (GY < 80)[..., None]                                                 # a darker knit cuff with ribs
    rib = 1 - 0.07 * (np.sin(GX * 1.4) > 0.6)
    col = np.where(cuff, col * np.array([0.82, 0.78, 0.72])[None, None, :] * rib[..., None], col)
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    # leather palm patch, stitched
    pad = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))             # a worn leather palm pad, soft-edged
    ImageDraw.Draw(pad).ellipse([*P(-44, 128), *P(46, 182)], fill=(146, 114, 78, 90))
    pad = pad.filter(ImageFilter.GaussianBlur(PX * 2.5))
    img = Image.alpha_composite(img, pad)
    d = ImageDraw.Draw(img, "RGBA")
    ring = [P(-40 + 82 * (0.5 + 0.5 * math.cos(a)), 130 + 48 * (0.5 + 0.5 * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 40)]
    _dashes(d, ring, (112, 86, 58, 150), seg=2.5)
    shade = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))           # shadows between the fingers, a highlight down each
    sh = ImageDraw.Draw(shade)
    for k in range(4):
        (bx, by), (tx, ty), w = finger_line(k)
        for side in (-1, 1):
            off = side * (w / 2 - 1.5)
            sh.line([P(bx + off, by + 8), P(tx + off, ty)], fill=(70, 56, 36, 110), width=int(PX * 3))
        sh.line([P(bx - w / 4, by + 10), P(tx - w / 4, ty - 6)], fill=(255, 246, 220, 70), width=int(PX * 3))
    shade = shade.filter(ImageFilter.GaussianBlur(PX * 1.6))
    img = Image.alpha_composite(img, shade)
    d = ImageDraw.Draw(img, "RGBA")
    # cuff hem stitching
    _dashes(d, [P(-68, 76), P(68, 76)], (120, 100, 70, 220))
    _dashes(d, [P(-68, 12), P(68, 12)], (120, 100, 70, 200))
    # finger seams and knuckle creases
    for k in range(4):
        (bx, by), (tx, ty), w = finger_line(k)
        for side in (-1, 1):
            off = side * (w / 2 - 3)
            _dashes(d, [P(bx + off, by + 6), P(tx + off, ty - 4)], (150, 130, 96, 150), seg=3)
        for f in (0.38, 0.7):
            cx, cy = bx + (tx - bx) * f, by + (ty - by) * f
            d.arc([*P(cx - w / 2 + 4, cy - 3), *P(cx + w / 2 - 4, cy + 5)], 200, 340, fill=(140, 120, 88, 170),
                  width=max(1, int(PX * 0.9)))
    # wear: soft soil on the fingertips and the heel of the palm, painted on a separate blurred layer
    soil = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    sd = ImageDraw.Draw(soil)
    for k in range(4):
        (_, _), (tx, ty), w = finger_line(k)
        sd.ellipse([*P(tx - w / 2 + 2, ty - 16), *P(tx + w / 2 - 2, ty + w / 2)], fill=(104, 80, 52, 120))
    sd.ellipse([*P(-30, 168), *P(30, 192)], fill=(110, 86, 56, 70))
    soil = soil.filter(ImageFilter.GaussianBlur(PX * 3))
    img = Image.alpha_composite(img, soil)
    img.putalpha(MASK)
    return img


def _dashes(d, pts, col, seg=4.0):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / (seg * PX)))
        for i in range(0, n, 2):
            a, b = i / n, min(1, (i + 1) / n)
            d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)],
                   fill=col, width=max(1, int(PX * 0.8)))


# ------------------------------------------------------------------ the replica: leaves
def _axis_at(x, y):
    """The direction a leaf should lie at (x, y): along the finger it is on, else roughly downward."""
    if y > PALM_BOT - 10:
        k = int(np.argmin([abs(x - FINGERS[i][0]) for i in range(4)]))
        return math.pi / 2 + math.radians(-FINGERS[k][2])
    if x > 52 and y > 100:
        (a, b), (c, e), _ = THUMB
        return math.atan2(e - b, c - a)
    return math.pi / 2 + (0.5 if y < 80 else 0.15) * math.sin(x * 0.2)


def _make_leaves(n=950, seed=7):
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(M > 0.5)
    pick = rng.choice(len(xs), n * 3, replace=False)
    out = []
    edge_quota = int(n * 0.35)
    for i in pick:
        x, y = GX[ys[i], xs[i]], GY[ys[i], xs[i]]
        dist = DIST[ys[i], xs[i]]
        if dist < 4 and edge_quota <= 0:
            continue
        if dist < 4:
            edge_quota -= 1
        in_finger = y > PALM_BOT - 6
        if in_finger and dist < 2.5:
            continue                                   # keep finger leaves inside their finger: the gaps stay open
        ang = _axis_at(x, y) + rng.normal(0, 0.22 if in_finger else 0.4)
        L = rng.uniform(9, 14) * (min(1.0, 0.55 + dist / 8) if in_finger else 1.0)
        born = np.clip((y + 6) / 300 + rng.normal(0, 0.05), 0, 0.97)     # from the cuff down to the tips
        shade = rng.uniform(0, 1)
        out.append((x, y, ang, L, born, shade, rng.uniform(0.24, 0.32)))
        if len(out) >= n:
            break
    out.sort(key=lambda q: (q[5] > 0.5, q[1]))   # darker back layer first, then the lighter front layer, top to bottom
    return out


LEAVES = _make_leaves()
GREENS = [((72, 118, 60), (108, 156, 82)), ((60, 104, 52), (96, 144, 70)), ((84, 132, 66), (128, 172, 94)),
          ((54, 92, 48), (86, 130, 64))]


def _leaf(d, x, y, ang, L, wr, cols, s=1.0):
    """A lens-shaped leaf: lighter half / darker half, a midrib, painted in sprite pixels."""
    ca, sa = math.cos(ang), math.sin(ang)
    L, W = L * s, L * wr * s
    pts_l, pts_r = [], []
    for k in range(9):
        u = k / 8
        px = (u - 0.5) * L
        half = W * math.sin(math.pi * u) ** 0.8
        pts_l.append((px, -half))
        pts_r.append((px, half))

    def tr(p):
        return P(x + p[0] * ca - p[1] * sa, y + p[0] * sa + p[1] * ca)
    dark, light = cols
    d.polygon([tr(p) for p in pts_l + [(L / 2, 0), (-L / 2, 0)][::-1]], fill=light + (255,))
    d.polygon([tr(p) for p in pts_r + [(L / 2, 0), (-L / 2, 0)][::-1]], fill=dark + (255,))
    d.line([tr((-L / 2, 0)), tr((L / 2 * 0.85, 0))], fill=(46, 78, 40, 220), width=max(1, int(PX * 0.6)))


def replica_sprite(u, t=0.0):
    """The leaf glove at growth fraction u in [0, 1]."""
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    shadow = Image.new("L", (SW, SH), 0)
    d = ImageDraw.Draw(img, "RGBA")
    sd = ImageDraw.Draw(shadow)
    # stems first: from the cuff down each finger, growing with u
    for k in range(4):
        (bx, by), (tx, ty), _ = finger_line(k)
        front = -6 + u * 1.05 * 316                       # the stems lead the leaves only slightly
        path = [(0, 4), (bx * 0.6, 60), (bx, by), (tx, ty)]
        pts = [path[0]]
        for (ax, ay), (cx2, cy2) in zip(path, path[1:]):
            if cy2 <= front:
                pts.append((cx2, cy2))
            else:
                if ay < front:
                    f = (front - ay) / (cy2 - ay)
                    pts.append((ax + (cx2 - ax) * f, front))
                break
        if len(pts) > 1:
            d.line([P(*p) for p in pts], fill=(52, 86, 46, 255), width=int(PX * 1.6), joint="curve")
    sway = 0.04 * math.sin(t * 0.8)
    for (x, y, ang, L, born, shade, wr) in LEAVES:
        if born > u:
            continue
        g = min(1.0, (u - born) / 0.08)                   # a new leaf unfurls
        s = 0.35 + 0.65 * (1 - (1 - g) ** 3)
        cols = GREENS[3] if shade < 0.5 and shade < 0.25 else GREENS[1] if shade < 0.5 else GREENS[0] if shade < 0.75 else GREENS[2]
        if g < 1:                                          # fresh leaves are lighter
            cols = tuple(tuple(int(c + (190 - c) * 0.25 * (1 - g)) for c in cc) for cc in cols)
        sx, sy = P(x + 1.2, y + 2.0)
        r = L * PX * 0.3 * s
        sd.ellipse([sx - r, sy - r * 0.6, sx + r, sy + r * 0.6], fill=90)
        _leaf(d, x, y, ang + sway * math.sin(y * 0.05), L, wr, cols, s)
    shadow = shadow.filter(ImageFilter.GaussianBlur(PX * 1.2))
    out = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    out.paste((20, 30, 18, 255), (0, 0), shadow)
    return Image.alpha_composite(out, img)


def paste(img, v, sprite, hx, hy, gs, dy_rows=None):
    """Paste a sprite (hook at local 0,0) into the frame through view v, at world hook (hx, hy), scale gs."""
    extra = 0
    if dy_rows is not None:                                # warp rows (the replica's fingers stretching)
        extra = max(0, int(np.ceil(np.max(dy_rows))) + 2)  # grow the canvas so stretched fingers aren't cut off
        arr = np.asarray(sprite)
        arr = np.concatenate([arr, np.zeros((extra, arr.shape[1], 4), arr.dtype)], 0)
        n = SH + extra
        src = np.arange(SH, dtype=float)
        dest = src + dy_rows
        back = np.round(np.interp(np.arange(n), dest, src, right=SH)).astype(int)
        back = np.clip(back, 0, n - 1)
        sprite = Image.fromarray(arr[back])
    wx0, wy0 = hx + X0 * gs, hy + Y0 * gs
    wx1, wy1 = hx + X1 * gs, hy + (Y1 + extra / PX) * gs
    a, b = v.p(wx0, wy0), v.p(wx1, wy1)
    w, h = int(round(b[0] - a[0])), int(round(b[1] - a[1]))
    if w < 2 or h < 2:
        return
    sp = sprite.resize((w, h), Image.LANCZOS)
    img.paste(sp, (int(round(a[0])), int(round(a[1]))), sp)


if __name__ == "__main__":
    r = real_sprite()
    reps = [replica_sprite(u) for u in (0.3, 0.65, 1.0)]
    sheet = Image.new("RGBA", (SW * 4, SH), (120, 128, 126, 255))
    for k, s in enumerate([r] + reps):
        sheet.alpha_composite(s, (k * SW, 0))
    sheet.convert("RGB").save("E:/Claude/music-video-2-work/04/glove_art.png")
    print("ok", SW, SH, len(LEAVES))
