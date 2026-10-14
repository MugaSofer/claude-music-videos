"""Typewriter Weather: the film. python film.py still OUT.png T [T ...] | smoke x | video OUT.mp4 [T0 T1]

The page moves like a real typewriter's: it slides left under a fixed strike point as each
character lands, snaps back on the carriage return, and feeds up a line. The weather in each line
blooms as a watercolour vignette in the right margin. At the end the page comes out and we see
the whole letter with its strip of weather.
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, "../..")
from craft import Finisher, PRESETS, clamp01, ease_in_out  # noqa: E402

W, H, FPS = 1920, 1080, 24
S = json.load(open("score.json"))
EV = S["events"]
LINES = S["lines"]
TOTAL = S["total"] + 2
FONT = ImageFont.truetype("C:/Windows/Fonts/courbd.ttf", 25)
CW = FONT.getlength("M")                 # monospace advance
LS = 96                                  # line spacing on the page (double spaced)
PW, PH = 1420, 1250                      # page size
TX, TY0 = 110, 150                       # text left edge / first baseline on the page
MX, MW, MH = 1130, 220, 80               # margin vignette box
STRIKE = (840, 780)                      # screen point where the typebars hit
PAPER = (242, 236, 222)

KEYS = [e for e in EV if e["kind"] in ("key", "space", "shift", "punct")]
RETURNS = {e["line"]: e["t"] for e in EV if e["kind"] == "return"}


def mix(a, b, u):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


# ---------------------------------------------------------------- the desk
def make_desk():
    r = np.random.default_rng(1)
    y = np.arange(H)[:, None]
    x = np.arange(W)[None, :]
    grain = np.sin(x / 7.0 + 3 * np.sin(y / 90.0) + r.normal(0, 0.3, (H, 1))) * 0.5 + 0.5
    base = np.array([54, 36, 26], np.float32)
    arr = base[None, None, :] * (0.8 + 0.25 * grain[..., None])
    d = np.hypot((x - 760) / 900, (y - 520) / 700)
    lamp = np.clip(1.25 - d, 0.18, 1.2)[..., None]
    arr = arr * lamp + np.array([40, 26, 10], np.float32) * np.clip(0.9 - d, 0, 1)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


DESK = make_desk()


# ---------------------------------------------------------------- vignettes (painted once)
def blot(img, box, col, a=0.8, seed=0):
    r = np.random.default_rng(seed)
    m = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(m)
    x0, y0, x1, y1 = box
    for _ in range(9):
        cx, cy = r.uniform(x0, x1), r.uniform(y0, y1)
        rr = r.uniform(0.25, 0.5) * (x1 - x0)
        d.ellipse([cx - rr, cy - rr * 0.6, cx + rr, cy + rr * 0.6], fill=int(255 * a * r.uniform(0.5, 0.9)))
    m = m.filter(ImageFilter.GaussianBlur(8))
    layer = Image.new("RGBA", img.size, col + (0,))
    layer.putalpha(m)
    img.alpha_composite(layer)


def vignette(kind, seed):
    im = Image.new("RGBA", (MW, MH), PAPER + (255,))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    if kind == "rain":
        blot(im, (0, 0, MW, MH), (110, 130, 160), 0.8, seed)
        for _ in range(40):
            x, y = r.uniform(0, MW), r.uniform(0, MH)
            d.line([(x, y), (x - 6, y + 16)], fill=(70, 90, 130, 170), width=2)
    elif kind == "wind":
        blot(im, (0, 0, MW, MH * 0.7), (150, 190, 220), 0.7, seed)
        d.line([(10, 30), (MW - 10, 38)], fill=(80, 70, 60, 230), width=2)
        for k, c in enumerate([(200, 80, 70), (240, 200, 90), (90, 140, 200), (240, 240, 240), (120, 170, 110)]):
            x = 25 + k * 40
            d.polygon([(x, 32 + k * 1.5), (x + 30, 34 + k * 1.5), (x + 44, 60 + 8 * math.sin(k)), (x + 12, 62)],
                      fill=c + (220,))
    elif kind == "fog":
        blot(im, (0, 0, MW, MH), (170, 175, 185), 0.9, seed)
        for k in range(5):
            x = 20 + k * 42
            h = 30 + (k % 3) * 12
            d.rectangle([x, MH - 20 - h, x + 28, MH - 20], fill=(120, 124, 136, int(200 - 38 * k)))
    elif kind == "sun":
        blot(im, (0, 0, MW, MH), (240, 200, 120), 0.7, seed)
        d.polygon([(40, 20), (190, 10), (190, MH - 10), (40, MH - 16)], fill=(236, 170, 90, 220))
        d.polygon([(40, 20), (90, 20), (70, MH - 16), (40, MH - 16)], fill=(180, 110, 70, 160))
    elif kind == "snow":
        blot(im, (0, 0, MW, MH), (60, 76, 120), 0.9, seed)
        for _ in range(60):
            x, y, s = r.uniform(0, MW), r.uniform(0, MH), r.uniform(1.5, 4)
            d.ellipse([x - s, y - s, x + s, y + s], fill=(250, 250, 255, 230))
    elif kind == "stars":
        blot(im, (0, 0, MW, MH), (26, 30, 70), 1.0, seed)
        for _ in range(45):
            x, y, s = r.uniform(0, MW), r.uniform(0, MH), r.uniform(0.8, 2.2)
            d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 244, 200, 240))
    elif kind == "all":
        for k, c in enumerate([(110, 130, 160), (150, 190, 220), (170, 175, 185), (240, 200, 120), (60, 76, 120), (26, 30, 70)]):
            blot(im, (k * MW / 6, 0, (k + 1) * MW / 6 + 10, MH), c, 0.85, seed + k)
    elif kind == "home":
        blot(im, (0, 0, MW, MH), (40, 44, 80), 0.85, seed)
        d.polygon([(80, 60), (115, 32), (150, 60)], fill=(120, 60, 50, 240))
        d.rectangle([88, 60, 142, 96], fill=(170, 140, 110, 240))
        d.rectangle([108, 70, 122, 84], fill=(255, 210, 120, 255))
    return im


VIGS = {L["line"]: vignette(L["weather"], L["line"] * 7 + 3) for L in LINES if L["weather"] != "none"}
REVEAL_NOISE = np.asarray(Image.fromarray((np.random.default_rng(2).random((13, 23)) * 255).astype(np.uint8))
                          .resize((MW, MH), Image.BICUBIC)).astype(np.float32) / 255


def reveal_mask(u):
    """A wet bloom spreading from the centre with a ragged edge; u in 0..1."""
    y, x = np.mgrid[0:MH, 0:MW]
    dist = np.hypot((x - MW / 2) / (MW / 2), (y - MH / 2) / (MH / 2)) / 1.45
    edge = dist + 0.35 * (REVEAL_NOISE - 0.5)
    return Image.fromarray((np.clip((u * 1.25 - edge) * 6, 0, 1) * 255).astype(np.uint8))


# ---------------------------------------------------------------- the page at time t
def ink_for(k):
    r = np.random.default_rng(k)
    wear = 1 - 0.25 * k / len(KEYS)
    return r.uniform(0.78, 1.0) * wear, r.uniform(-1.2, 1.2), r.uniform(-0.8, 0.8)


INK = [ink_for(k) for k in range(len(KEYS))]


def page(t):
    pg = Image.new("RGBA", (PW, PH), PAPER + (255,))
    d = ImageDraw.Draw(pg)
    for k, e in enumerate(KEYS):
        if e["t"] > t or e["ch"] == " ":
            continue
        a, jy, jx = INK[k]
        age = t - e["t"]
        a *= min(1.0, 0.55 + age * 12)            # the strike darkens as the ink settles
        c = mix(PAPER, (14, 12, 18), a)
        d.text((TX + e["col"] * CW + jx, TY0 + e["line"] * LS - 20 + jy), e["ch"], font=FONT, fill=c)
    for L in LINES:
        v = VIGS.get(L["line"])
        if v is None:
            continue
        u = clamp01((t - (L["t0"] + 2.5)) / 4.0)
        if u <= 0:
            continue
        m = reveal_mask(ease_in_out(u))
        pg.paste(v, (MX, TY0 + L["line"] * LS - MH // 2 - 8), m)
    return pg


# ---------------------------------------------------------------- where the page sits on screen
def carriage(t):
    """(line_float, col_float): which line is at the strike point and how far along it."""
    line, col = 0.0, 0.0
    for e in KEYS:
        if e["t"] <= t:
            line, col = e["line"], e["col"] + 1
    # after a return, the carriage snaps back and the page feeds up
    for li, rt in RETURNS.items():
        if rt <= t:
            u = ease_in_out(clamp01((t - rt) / 0.45))
            if li + 1 < len(LINES):
                if line <= li:
                    line = li + u
                    col = col * (1 - u)
            else:
                line = li
    return line, col


def frame(t):
    img = DESK.copy()
    line, col = carriage(t)
    end = clamp01((t - (LINES[-1]["t1"] + 0.5)) / 5.0)       # the page comes out and we see it whole
    e = ease_in_out(end)
    px = STRIKE[0] - (TX + col * CW)
    py = STRIKE[1] - (TY0 + line * LS)
    zoom = 1 - 0.28 * e
    fx, fy = (W - PW * zoom) / 2 + 60, (H - PH * zoom) / 2 + 30
    ox, oy = px * (1 - e) + fx * e, py * (1 - e) + fy * e
    pg = page(t)
    if zoom != 1:
        pg = pg.resize((int(PW * zoom), int(PH * zoom)), Image.LANCZOS)
    sh = Image.new("RGBA", pg.size, (0, 0, 0, 120))
    img.paste((0, 0, 0), (int(ox) + 12, int(oy) + 16), sh.split()[3].filter(ImageFilter.GaussianBlur(4)))
    img.paste(pg, (int(ox), int(oy)), pg)
    # the typewriter: platen and type guide at the bottom, sliding away at the end
    d = ImageDraw.Draw(img)
    ty = STRIKE[1] + 20 + int(400 * e)
    d.rectangle([0, ty, W, ty + 90], fill=(28, 26, 30))
    d.rectangle([0, ty, W, ty + 12], fill=(60, 58, 64))
    d.polygon([(STRIKE[0] - 26, ty), (STRIKE[0] + 26, ty), (STRIKE[0] + 10, ty - 26), (STRIKE[0] - 10, ty - 26)],
              fill=(150, 146, 150))
    if ty + 90 < H:
        d.rectangle([0, ty + 90, W, H], fill=(18, 17, 20))
    return img


FIN = None


def finished(t, i):
    global FIN
    if FIN is None:
        FIN = Finisher(W, H, seed=9, **dict(PRESETS["night"], paper=0.03, grain=0.022, halation=0.2))
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
