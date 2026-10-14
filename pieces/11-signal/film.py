"""Signal: the film. python film.py still OUT.png T [T ...] | smoke x | video OUT.mp4 [T0 T1]

The lighthouse (left) and the boat (right) flash exactly their Morse. Each letter glows above its
sender as it completes; after each message the letters rise into the sky as stars, each word a
small constellation (warm for the lighthouse, cool for the boat).
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
MSGS = S["messages"]
TOTAL = S["total"] + 2
HORIZON = 700
LH = (250, 430)            # lighthouse lamp
FONT = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf", 52)
F_TITLE = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf", 120)
F_SUB = ImageFont.truetype("C:/Windows/Fonts/georgiai.ttf", 44)
CW = 40
WARM, COOL = (255, 214, 140), (170, 210, 255)

MARKS = {"light": [], "boat": []}
for e in EV:
    for who in (("light", "boat") if e["sender"] == "both" else (e["sender"],)):
        MARKS[who].append((e["t"], e["t"] + e["dur"]))


def lit(who, t):
    """1 while a mark is on (with a short attack/decay so flashes read on screen), else a fading glow."""
    v = 0.0
    for a, b in MARKS[who]:
        if a - 0.02 <= t <= b + 0.12:
            v = max(v, clamp01((t - a + 0.02) / 0.03) * (1 if t <= b else 1 - (t - b) / 0.12))
        if a > t + 0.2:
            break
    return v


def mix(a, b, u):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


# ---------------------------------------------------------------- letters and their stars
rng = np.random.default_rng(11)
LETTERS = []
for m in MSGS:
    who = m["sender"]
    n = len(m["text"])
    if who == "light":
        x0, y = 360, 520
    elif who == "boat":
        x0, y = 1580 - n * CW, 560
    else:
        x0, y = 960 - n * CW / 2, 470
    words = m["text"].split()
    col = 0
    li = 0
    for wi, word in enumerate(words):
        cx, cy = rng.uniform(220, 1700), rng.uniform(70, 400)          # the word's constellation centre
        sx, sy = cx, cy
        prev = None
        for k, ch in enumerate(word):
            L = m["letters"][li]
            li += 1
            sx += rng.uniform(-70, 70) if k else 0
            sy += rng.uniform(-45, 45) if k else 0
            star = (float(np.clip(sx, 60, W - 60)), float(np.clip(sy, 40, 430)))
            LETTERS.append(dict(ch=ch, who=who, msg=m["msg"], t=L["t_done"], t_rise=m["t1"] + 1.5,
                                pos=(x0 + (col + k) * CW, y), star=star, prev=prev))
            prev = len(LETTERS) - 1
        col += len(word) + 1


def letter_state(L, t):
    """(x, y, letter alpha, star alpha, glow). The word first lifts whole (legible), then scatters into stars."""
    if t < L["t"]:
        return None
    a = clamp01((t - L["t"]) / 0.25)
    lift = ease_in_out(clamp01((t - L["t_rise"]) / 1.6))
    u = ease_in_out(clamp01((t - L["t_rise"] - 1.6) / 4.8))
    x0, y0 = L["pos"][0], L["pos"][1] - 120 * lift
    x = x0 + (L["star"][0] - x0) * u
    y = y0 + (L["star"][1] - y0) * u
    glow = math.exp(-(t - L["t"]) / 0.8)
    return x, y, a * (1 - u), u, glow


# ---------------------------------------------------------------- background
def make_bg():
    y = np.linspace(0, 1, H)[:, None, None]
    top, hor, sea_top, sea_bot = (np.array(c, np.float32) for c in [(6, 8, 24), (24, 40, 70), (14, 22, 44), (4, 6, 16)])
    arr = np.where(y < HORIZON / H, top * (1 - y / (HORIZON / H)) + hor * (y / (HORIZON / H)),
                   sea_top + (sea_bot - sea_top) * ((y - HORIZON / H) / (1 - HORIZON / H)))
    arr = np.broadcast_to(arr, (H, W, 3)).copy()
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    r = np.random.default_rng(3)
    for _ in range(420):
        x, yy, b = r.uniform(0, W), r.uniform(0, HORIZON - 40), r.uniform(60, 200)
        d.point((x, yy), fill=(int(b), int(b), int(b * 1.05)))
    # cliff and lighthouse tower
    d.polygon([(0, H), (0, 560), (120, 545), (330, 600), (420, HORIZON + 30), (460, H)], fill=(10, 10, 18))
    d.polygon([(LH[0] - 34, 590), (LH[0] + 34, 590), (LH[0] + 22, LH[1] + 20), (LH[0] - 22, LH[1] + 20)], fill=(36, 38, 52))
    for k in range(3):
        yy = 570 - 45 * k
        d.rectangle([LH[0] - 30 + 4 * k, yy - 12, LH[0] + 30 - 4 * k, yy + 6], fill=(70, 30, 36))
    d.rectangle([LH[0] - 26, LH[1] - 22, LH[0] + 26, LH[1] + 20], fill=(30, 32, 44))
    d.polygon([(LH[0] - 30, LH[1] - 22), (LH[0], LH[1] - 50), (LH[0] + 30, LH[1] - 22)], fill=(20, 22, 30))
    return img


BG = make_bg()


def frame(t):
    img = BG.copy()
    d = ImageDraw.Draw(img)
    glow = Image.new("RGB", (W // 2, H // 2))
    gd = ImageDraw.Draw(glow)
    # sea shimmer
    for k in range(34):
        y = HORIZON + 10 + k * 11 + 2 * math.sin(t * 0.7 + k)
        x0 = ((k * 211 + t * 25) % (W + 300)) - 150
        d.line([(x0, y), (x0 + 80 + (k % 4) * 30, y)], fill=(30, 44, 70), width=1)
    # the lighthouse lamp and its beam toward the boat
    v = lit("light", t)
    lamp = mix((90, 80, 60), (255, 236, 180), v)
    d.rectangle([LH[0] - 20, LH[1] - 16, LH[0] + 20, LH[1] + 14], fill=lamp)
    if v > 0.01:
        a = v
        gd.polygon([(LH[0] / 2, LH[1] / 2 - 6), (1650 / 2, 650 / 2 - 60), (1650 / 2, 650 / 2 + 50), (LH[0] / 2, LH[1] / 2 + 6)],
                   fill=tuple(int(c * a * 0.22) for c in WARM))
        gd.ellipse([LH[0] / 2 - 40, LH[1] / 2 - 40, LH[0] / 2 + 40, LH[1] / 2 + 40], fill=tuple(int(c * a) for c in WARM))
        gd.rectangle([LH[0] / 2 - 5, HORIZON / 2 + 10, LH[0] / 2 + 5, HORIZON / 2 + 150 * a], fill=tuple(int(c * a * 0.5) for c in WARM))
    # the boat, rocking, with its mast lamp
    bx, by = 1600, 728 + 6 * math.sin(t * 1.1)
    ang = 0.05 * math.sin(t * 0.9)
    ca, sa = math.cos(ang), math.sin(ang)

    def R(px, py):
        px, py = px * 1.6, py * 1.6                    # v2: a bigger boat
        return (bx + px * ca - py * sa, by + px * sa + py * ca)
    d.polygon([R(-70, -12), R(70, -16), R(55, 14), R(-55, 14)], fill=(26, 26, 36))
    d.line([R(0, -14), R(0, -120)], fill=(50, 52, 66), width=4)
    d.polygon([R(4, -110), R(4, -24), R(58, -24)], fill=(44, 46, 60))
    vb = lit("boat", t)
    lx, ly = R(0, -126)
    d.ellipse([lx - 6, ly - 6, lx + 6, ly + 6], fill=mix((70, 80, 100), (230, 244, 255), vb))
    if vb > 0.01:
        gd.ellipse([lx / 2 - 28, ly / 2 - 28, lx / 2 + 28, ly / 2 + 28], fill=tuple(int(c * vb) for c in COOL))
        gd.rectangle([lx / 2 - 3, HORIZON / 2 + 20, lx / 2 + 3, HORIZON / 2 + 20 + 90 * vb], fill=tuple(int(c * vb * 0.5) for c in COOL))
    # GOODNIGHT: the boat answers with its own beam, and the two lights meet across the water
    if vb > 0.01 and v > 0.01 and t > MSGS[-1]["t0"] - 0.2:
        k = min(vb, v)
        gd.polygon([(lx / 2, ly / 2 - 3), (LH[0] / 2 + 60, LH[1] / 2 - 30), (LH[0] / 2 + 60, LH[1] / 2 + 30), (lx / 2, ly / 2 + 3)],
                   fill=tuple(int(c * k * 0.25) for c in COOL))
    # letters, and the constellations they become
    states = [letter_state(L, t) for L in LETTERS]
    for L, st in zip(LETTERS, states):
        if st is None or L["prev"] is None:
            continue
        ps = states[L["prev"]]
        if ps is None:
            continue
        a = min(st[3], ps[3])
        if a > 0.05:
            c = mix((10, 14, 34), WARM if L["who"] == "light" else COOL if L["who"] == "boat" else (230, 230, 240), 0.25 * a)
            d.line([(ps[0], ps[1]), (st[0], st[1])], fill=c, width=1)
    for L, st in zip(LETTERS, states):
        if st is None:
            continue
        x, y, la, sa_, g = st
        col = WARM if L["who"] == "light" else COOL if L["who"] == "boat" else (240, 236, 230)
        if la > 0.01:
            d.text((x, y), L["ch"], font=FONT, fill=mix((8, 10, 26), col, la), anchor="mm")
            gd.ellipse([x / 2 - 18, y / 2 - 18, x / 2 + 18, y / 2 + 18], fill=tuple(int(c * (0.15 + 0.6 * g) * la) for c in col))
        if sa_ > 0.01:
            tw = 0.75 + 0.25 * math.sin(t * 2.3 + x * 0.01)
            r = 1.5 + 2.2 * sa_
            d.ellipse([x - r, y - r, x + r, y + r], fill=mix((8, 10, 26), col, sa_ * tw))
            gd.ellipse([x / 2 - 6, y / 2 - 6, x / 2 + 6, y / 2 + 6], fill=tuple(int(c * 0.35 * sa_ * tw) for c in col))
    glow = glow.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    img = ImageChops.add(img, glow)
    ta = clamp01((t - 0.3) / 0.8) * clamp01((4.2 - t) / 1.0)   # title card over the opening sea
    if ta > 0:
        d = ImageDraw.Draw(img)
        d.text((960, 300), "SIGNAL", font=F_TITLE, anchor="mm", fill=mix((8, 10, 26), (236, 230, 214), ta))
        d.text((960, 385), "a lighthouse and a small boat, talking in Morse", font=F_SUB, anchor="mm",
               fill=mix((8, 10, 26), (190, 196, 214), ta))
    fade = clamp01((t - (S["total"] - 2.5)) / 3)        # the last seconds dim gently, leaving the stars
    if fade > 0:
        img = Image.blend(img, Image.new("RGB", img.size, (4, 5, 14)), 0.5 * fade)
    return img


FIN = None


def finished(t, i):
    global FIN
    if FIN is None:
        FIN = Finisher(W, H, seed=11, **dict(PRESETS["night"], paper=0.02, grain=0.02))
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
