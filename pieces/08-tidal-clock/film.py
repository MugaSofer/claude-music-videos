"""Tidal Clock: the film. The sea surface, the boats' bobbing and the bells all come from sea.py.

python film.py still OUT.png T [T ...]
python film.py video OUT.mp4 [T0 T1]
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, "../..")
from craft import Finisher, PRESETS, clamp01  # noqa: E402
from sea import A, BOATS, HARBOUR, K, P, W as OMEGA, height, slope, tide  # noqa: E402

W, H, FPS = 1920, 1080, 24
E = json.load(open("events.json"))
EV = E["events"]
TOTAL = E["total"] + 6
X0, SX = 150.0, 13.2            # screen x = X0 + metres * SX  (harbour 0..120 m)
SEA_Y = 730                      # still-water line
VZ = 95.0                        # vertical exaggeration: px per metre of wave height

BELLS = {}
for e in EV:
    if e["kind"] == "bell":
        BELLS.setdefault(e["boat"], []).append(e["t"])
LIGHTS = [e["t"] for e in EV if e["kind"] == "light"]


def sx(xm):
    return X0 + xm * SX


def mix(a, b, u):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


def night(t):
    """0 at dusk, 1 at full night (reached at ~140 s)."""
    return clamp01((t - 20) / 120) ** 1.2


# ---------------------------------------------------------------- watercolour helpers
_rng = np.random.default_rng(3)
_blot = Image.fromarray((_rng.random((34, 60)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
BLOT = np.asarray(_blot.filter(ImageFilter.GaussianBlur(18))).astype(np.float32) / 255


def wash(img, mask, col, strength=1.0, edge=0.25):
    """Paint `col` through an L mask like a watercolour wash: soft mottled fill plus a darker wet edge."""
    m = np.asarray(mask.filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
    inner = np.asarray(mask.filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    rim = np.clip(m - inner, 0, 1) * 2.2                       # pigment pools at the edge
    a = m * strength * (0.82 + 0.3 * (BLOT - 0.5))
    arr = np.asarray(img).astype(np.float32)
    c = np.array(col, np.float32)
    dark = c * 0.72
    arr = arr * (1 - a[..., None]) + c * a[..., None]
    arr = arr * (1 - (rim * edge * m)[..., None]) + dark * (rim * edge * m)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- static scenery masks
def poly_mask(pts):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


HILLS = poly_mask([(0, SEA_Y)] + [(x, 500 + 40 * math.sin(x / 260) + 25 * math.sin(x / 97 + 1)) for x in range(0, W + 20, 20)] + [(W, SEA_Y)])
HEADLAND = poly_mask([(0, SEA_Y + 10), (0, 420), (60, 400), (130, 430), (190, 520), (230, 600), (250, SEA_Y + 10)])
QUAY = poly_mask([(1740, SEA_Y + 60), (1740, 640), (W, 640), (W, SEA_Y + 60)])
HOUSES = Image.new("L", (W, H), 0)
_hd = ImageDraw.Draw(HOUSES)
for i, (x, w, h) in enumerate([(1745, 60, 120), (1808, 50, 150), (1860, 60, 110)]):
    _hd.rectangle([x, 640 - h, x + w, 640], fill=255)
    _hd.polygon([(x - 4, 640 - h), (x + w / 2, 640 - h - 40), (x + w + 4, 640 - h)], fill=255)
WINDOWS = [(1762, 560), (1780, 590), (1820, 530), (1835, 575), (1875, 575), (1890, 600)]
LH_X, LH_TOP = 95, 250          # lighthouse on the headland


def sky(t):
    n = night(t)
    top = mix((226, 150, 120), (16, 20, 46), n)
    mid = mix((244, 196, 150), (40, 44, 84), n)
    y = np.linspace(0, 1, SEA_Y)[:, None, None]
    s = np.array(top, np.float32) * (1 - y) + np.array(mid, np.float32) * y
    arr = np.zeros((H, W, 3), np.float32)
    arr[:SEA_Y] = s * (0.94 + 0.12 * BLOT[:SEA_Y, :, None])
    arr[SEA_Y:] = np.array(mix((150, 130, 140), (14, 18, 40), n), np.float32)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if n > 0.5:                                     # stars come out
        d = ImageDraw.Draw(img)
        r = np.random.default_rng(5)
        for k in range(140):
            x, yy = r.uniform(0, W), r.uniform(0, 420)
            a = clamp01((n - 0.5) * 2) * r.uniform(0.3, 1) * (0.7 + 0.3 * math.sin(t * r.uniform(1, 3) + k))
            d.point((x, yy), fill=mix(mix(top, mid, yy / SEA_Y), (250, 246, 230), a))
    return img


def beam(t):
    """Lighthouse beam brightness toward the viewer and its sweep angle, from the light events."""
    best = 0.0, 0.0
    for lt in LIGHTS:
        u = (t - lt) / 2.2
        if -1.5 < u < 1.5:
            best = (math.exp(-u * u * 2), u)
    return best


# ---------------------------------------------------------------- frame
def frame(t):
    n = night(t)
    img = sky(t)
    img = wash(img, HILLS, mix((150, 120, 150), (30, 32, 60), n), 0.9)
    img = wash(img, HEADLAND, mix((96, 82, 96), (16, 18, 34), n), 1.0, 0.35)
    img = wash(img, QUAY, mix((120, 100, 96), (22, 22, 40), n), 1.0, 0.35)
    img = wash(img, HOUSES, mix((200, 170, 150), (34, 32, 56), n), 1.0, 0.3)
    d = ImageDraw.Draw(img)
    for (wx, wy) in WINDOWS:                         # windows light up as night falls
        a = clamp01((n - 0.3) * 2.5)
        d.rectangle([wx, wy, wx + 9, wy + 12], fill=mix(mix((200, 170, 150), (34, 32, 56), n), (255, 206, 120), a))
    # lighthouse tower
    d.polygon([(LH_X - 16, 420), (LH_X + 16, 420), (LH_X + 10, LH_TOP + 20), (LH_X - 10, LH_TOP + 20)],
              fill=mix((236, 228, 216), (70, 70, 90), n))
    for k in range(3):
        yy = 420 - 45 * k - 20
        d.rectangle([LH_X - 14 + k * 2, yy, LH_X + 14 - k * 2, yy + 14], fill=mix((180, 60, 56), (60, 24, 30), n))
    d.rectangle([LH_X - 12, LH_TOP, LH_X + 12, LH_TOP + 20], fill=mix((250, 240, 200), (255, 230, 150), n))

    glow = Image.new("RGB", (W // 2, H // 2))
    gd = ImageDraw.Draw(glow)
    b, u = beam(t)
    if b > 0.01:                                     # the beam sweeps across toward the viewer
        ang = u * 0.9
        length = 1400 + 600 * b
        tip = (LH_X / 2 + math.cos(ang) * length / 2, LH_TOP / 2 + math.sin(ang) * 120 / 2)
        a = (0.35 + 0.65 * n) * b
        gd.polygon([(LH_X / 2, LH_TOP / 2 - 2), tip, (tip[0], tip[1] + 60)],
                   fill=tuple(int(c * a * 0.5) for c in (255, 236, 180)))
        gd.ellipse([LH_X / 2 - 30 * b, LH_TOP / 2 - 30 * b, LH_X / 2 + 30 * b, LH_TOP / 2 + 30 * b],
                   fill=tuple(int(c * a) for c in (255, 240, 200)))

    # sea: back layers are damped, delayed copies of the same field (depth), then the true surface
    xs = np.linspace(-14, HARBOUR + 16, 300)
    for layer, (depth, damp, col_d, col_n) in enumerate([(-60, 0.35, (170, 150, 160), (26, 30, 60)),
                                                         (-30, 0.6, (150, 132, 150), (22, 26, 54)),
                                                         (0, 1.0, (120, 110, 140), (16, 20, 46))]):
        ys = [SEA_Y + depth + damp * VZ * -height(x, t - 0.4 * (2 - layer)) for x in xs]
        pts = [(sx(x), y) for x, y in zip(xs, ys)] + [(W + 50, H), (-50, H)]
        img = wash(img, poly_mask(pts), mix(col_d, col_n, n), 0.92, 0.4)
        d = ImageDraw.Draw(img)
        d.line([(sx(x), y) for x, y in zip(xs, ys)], fill=mix(mix(col_d, col_n, n), (255, 250, 240), 0.35 - 0.2 * n), width=2)
    # beam light on the water
    if b > 0.01:
        a = (0.3 + 0.5 * n) * b
        gd.rectangle([0, SEA_Y / 2, W / 2, SEA_Y / 2 + 40], fill=tuple(int(c * a * 0.35) for c in (255, 230, 170)))

    gulls(img, t, n)
    # boats ride the true surface
    for i, (xm, step, thr, name) in enumerate(BOATS):
        boat(img, gd, i, xm, t, n)
    glow = glow.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    return ImageChops.add(img, glow)


GULL_SEATS = [(1752, 516), (1770, 518), (1818, 488), (1838, 486), (1866, 528), (1884, 530), (1902, 531)]
GULL_LIFT = 80.0


def gulls(img, t, n):
    """Gulls sit on the quay roofs; in the big set they lift off together and wheel out over the harbour."""
    d = ImageDraw.Draw(img)
    col = mix((246, 242, 236), (150, 150, 172), n)
    for k, (x0, y0) in enumerate(GULL_SEATS):
        u = t - GULL_LIFT - k * 0.35
        if u < 0:                                    # sitting
            d.ellipse([x0 - 6, y0 - 5, x0 + 6, y0 + 2], fill=col)
            d.ellipse([x0 + 3, y0 - 8, x0 + 8, y0 - 3], fill=col)
            continue
        if u > 18:
            continue
        x = x0 - 70 * u - 9 * u * u * 0.5 * (0.6 + 0.1 * k)
        y = y0 - 60 * u + 5 * u * u + 30 * math.sin(u * 0.8 + k)
        flap = math.sin(u * 9 + k)
        s = 9 + 0.4 * k
        d.line([(x - s, y - s * 0.5 * flap), (x, y), (x + s, y - s * 0.5 * flap)], fill=col, width=3, joint="curve")


HULLS = [(186, 60, 50), (40, 70, 120), (230, 222, 206), (60, 110, 80), (200, 150, 60), (120, 50, 70),
         (220, 214, 200), (50, 90, 140), (170, 70, 50), (80, 120, 100), (230, 200, 120), (60, 60, 90)]


def boat(img, gd, i, xm, t, n):
    d = ImageDraw.Draw(img)
    y = SEA_Y - VZ * height(xm, t)
    ang = math.atan(-slope(xm, t) * VZ / SX * 0.6)
    x = sx(xm)
    size = 1.25 + 0.4 * ((i * 7) % 5) / 4
    ca, sa = math.cos(ang), math.sin(ang)

    def R(px, py):
        return (x + px * ca - py * sa, y + px * sa + py * ca)
    hl, hh = 34 * size, 13 * size
    col = mix(HULLS[i], (20, 22, 44), n * 0.75)
    d.polygon([R(-hl, -hh * 0.4), R(hl, -hh * 0.6), R(hl * 0.8, hh * 0.35), R(-hl * 0.75, hh * 0.35)], fill=col)
    d.line([R(-hl, -hh * 0.4), R(hl, -hh * 0.6)], fill=mix(col, (255, 255, 255), 0.25), width=2)
    mast = 78 * size
    d.line([R(-2, -hh * 0.5), R(-2, -hh * 0.5 - mast)], fill=mix((40, 34, 32), (20, 20, 36), n), width=5)
    d.line([R(-1, -hh * 0.5), R(-1, -hh * 0.5 - mast)], fill=mix((236, 226, 210), (170, 170, 196), n), width=2)
    d.line([R(-2, -hh * 0.5 - mast), R(hl * 0.9, -hh * 0.55)], fill=mix((60, 50, 46), (120, 120, 150), n), width=1)
    # masthead lamp: flares on its bell
    g = 0.0
    for bt in BELLS.get(i, []):
        if bt <= t:
            g = max(g, math.exp(-(t - bt) / 0.9))
    lx, ly = R(-2, -hh * 0.5 - mast - 5)
    base = 0.25 + 0.75 * n
    lamp = mix((255, 224, 150), (255, 250, 220), g)
    d.ellipse([lx - 4, ly - 4, lx + 4, ly + 4], fill=mix(mix(col, (255, 230, 170), base), lamp, g))
    a = min(1.0, base * 0.35 + g * (0.6 + 0.4 * n))
    rr = 14 + 26 * g
    gd.ellipse([lx / 2 - rr / 2, ly / 2 - rr / 2, lx / 2 + rr / 2, ly / 2 + rr / 2], fill=tuple(int(c * a) for c in (255, 200, 110)))
    # reflection streak of the lamp
    if a > 0.05:
        gd.rectangle([lx / 2 - 2, (SEA_Y + 20) / 2, lx / 2 + 2, (SEA_Y + 20 + 140 * a) / 2],
                     fill=tuple(int(c * a * 0.6) for c in (255, 200, 110)))


FIN = None


def finished(t, i):
    global FIN
    if FIN is None:
        FIN = Finisher(W, H, seed=8, **dict(PRESETS["paper"], paper=0.06, grain=0.02, vignette=0.26))
    return FIN(np.asarray(frame(t)).astype(np.float32) / 255.0, i)


def to_u8(x):
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "still":
        ts = [float(x) for x in sys.argv[3:]]
        ims = [Image.fromarray(to_u8(finished(t, int(t * FPS)))) for t in ts]
        if len(ims) == 1:
            ims[0].save(out)
        else:
            cols, tw, th = 3, 640, 360
            sheet = Image.new("RGB", (tw * cols, th * math.ceil(len(ims) / cols)))
            for k, im in enumerate(ims):
                sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
            sheet.save(out)
    elif mode == "smoke":
        t = 0.0
        while t < TOTAL:
            frame(t)
            t += 0.5
        print("smoke OK")
    else:
        t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        t1 = float(sys.argv[4]) if len(sys.argv) > 4 else TOTAL
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                               "-pix_fmt", "yuv420p", "-threads", "2", out], stdin=subprocess.PIPE)
        for i in range(int(t0 * FPS), int(t1 * FPS)):
            ff.stdin.write(to_u8(finished(i / FPS, i)).tobytes())
            if i % 240 == 0:
                print(f"{i / FPS:.0f}s", flush=True)
        ff.stdin.close()
        ff.wait()
