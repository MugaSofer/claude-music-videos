"""Relay: the film (see design.md). Stage 1: river world, boat, lantern line, time of day.

python film.py still OUT.png T [T ...]
python film.py video OUT.mp4 [T0 T1]
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, "../..")
from craft import Finisher, PRESETS, clamp01, ease_in_out  # noqa: E402
from hands import (CHANGED_IDX, HAND_COL, apply_fog, draw_caption, draw_hand, fog_amount,  # noqa: E402
                   gemini_state, hand_state, lantern_ring_glow, ring_positions)

W, H, FPS = 1920, 1080, 24
S = json.load(open("score.json"))
EV = S["events"]
SEC = dict(S["sections"])
TOTAL = S["total"] + 3
WATER_Y = 700

# ---------------------------------------------------------------- palettes (time of day per hand)
PAL = {  # sky_top, sky_bot, far, mid, near, water, light (lantern glow strength)
    "claude":  ((196, 176, 206), (246, 208, 190), (170, 150, 176), (122, 118, 140), (70, 74, 88), (170, 160, 186), 0.35),
    "grok":    ((120, 170, 222), (206, 228, 240), (132, 170, 170), (78, 128, 102), (42, 78, 58), (104, 150, 176), 0.2),
    "chatgpt": ((236, 176, 96), (250, 222, 160), (196, 150, 108), (150, 104, 70), (86, 60, 44), (200, 150, 96), 0.4),
    "gemini":  ((92, 104, 132), (150, 160, 178), (112, 120, 140), (86, 94, 112), (56, 62, 76), (100, 108, 128), 0.6),
    "last":    ((14, 16, 40), (42, 40, 82), (30, 32, 60), (22, 24, 46), (12, 14, 28), (20, 22, 48), 1.0),
}
ORDER = ["claude", "grok", "chatgpt", "gemini", "last"]


def palette(t):
    """Blend from the previous hand's palette to the current one over 6 s around each section start."""
    i = 0
    for k, h in enumerate(ORDER):
        if t >= SEC[h] - 3:
            i = k
    cur = PAL[ORDER[i]]
    if i == 0:
        return cur
    prev = PAL[ORDER[i - 1]]
    u = ease_in_out(clamp01((t - (SEC[ORDER[i]] - 3)) / 6))
    return tuple(tuple(int(a + (b - a) * u) for a, b in zip(p, q)) if isinstance(p, tuple) else p + (q - p) * u
                 for p, q in zip(prev, cur))


def mix(a, b, u):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


# ---------------------------------------------------------------- scenery masks (built once, tiled)
rng = np.random.default_rng(7)


def ridge(width, base, amp, octaves, seed):
    r = np.random.default_rng(seed)
    x = np.arange(width)
    y = np.full(width, float(base))
    for k in range(octaves):
        f = (k + 1) * 2 * math.pi / width * r.integers(1, 4) * (k + 1)
        y += amp / (k + 1) * np.sin(f * x + r.uniform(0, 6.28))
    return y


def make_strip(width, kind, seed):
    m = Image.new("L", (width, H), 0)
    d = ImageDraw.Draw(m)
    r = np.random.default_rng(seed)
    if kind == "far":
        y = ridge(width, 520, 60, 4, seed)
        d.polygon([(0, WATER_Y)] + [(i, y[i]) for i in range(0, width, 8)] + [(width, WATER_Y)], fill=255)
    elif kind == "mid":
        y = ridge(width, 650, 14, 3, seed)
        d.polygon([(0, WATER_Y + 6)] + [(i, y[i]) for i in range(0, width, 8)] + [(width, WATER_Y + 6)], fill=255)
        x = 0
        while x < width:            # willows and poplars
            x += int(r.uniform(90, 260))
            gy = int(y[min(x, width - 1)])
            if r.random() < 0.55:
                rw, rh = r.uniform(50, 90), r.uniform(90, 150)
                d.ellipse([x - rw, gy - rh * 1.6, x + rw, gy - rh * 0.2], fill=255)
                for k in range(9):   # willow fall
                    xx = x - rw + k * rw / 4
                    d.line([(xx, gy - rh), (xx + r.uniform(-6, 6), gy - 8)], fill=255, width=5)
            else:
                ph = r.uniform(140, 220)
                d.ellipse([x - 16, gy - ph, x + 16, gy - 10], fill=255)
            d.rectangle([x - 3, gy - 40, x + 3, gy], fill=255)
    elif kind == "near":
        x = 0
        while x < width:            # reed clumps and stones at the bottom edge
            x += int(r.uniform(70, 240))
            if r.random() < 0.6:
                for k in range(int(r.uniform(4, 9))):
                    bx = x + r.uniform(-20, 20)
                    top = H - r.uniform(70, 190)
                    tx = bx + r.uniform(-25, 25)                       # v3: the head sits on its own stem's tip
                    d.line([(bx, H), (tx, top)], fill=255, width=int(r.uniform(3, 6)))
                    if r.random() < 0.35:
                        d.ellipse([tx - 5, top - 24, tx + 7, top + 10], fill=255)   # bulrush head
            else:
                s = r.uniform(40, 90)
                d.ellipse([x - s, H - s * 0.8, x + s, H + s * 0.4], fill=255)
    return m


STRIPS = {k: make_strip(3840, k, i + 3) for i, k in enumerate(["far", "mid", "near"])}
SPEED = {"far": 6.0, "mid": 22.0, "near": 70.0}


def scrolled(kind, t):
    s = STRIPS[kind]
    off = int(t * SPEED[kind]) % s.width
    a = s.crop((off, 0, min(off + W, s.width), H))
    if a.width < W:
        b = s.crop((0, 0, W - a.width, H))
        c = Image.new("L", (W, H))
        c.paste(a, (0, 0))
        c.paste(b, (a.width, 0))
        return c
    return a


# ---------------------------------------------------------------- the tune on the line
TUNE = {}   # hand -> list of (beat_in_tune, midi, idx) for the lantern line layout
for e in EV:
    if e["section"] in (1, 2, 3, 4, 5) and e["hand"] not in TUNE:
        TUNE[e["hand"]] = []
    if e["section"] in (1, 2, 3, 4, 5):
        TUNE[e["hand"]].append(e)
LINE_X0, LINE_X1, LINE_Y = 470, 1450, 430


def current_hand(t):
    h = "claude"
    for k in ORDER:
        if t >= SEC[k] - 0.2:
            h = k
    return h


def lantern_layout(hand):
    """26 lantern slots: x by position in the tune (first statement only), hang by pitch."""
    evs = [e for e in TUNE[hand]]
    first = {}
    for e in evs:
        first.setdefault(e["idx"], e)
    t0 = min(e["t"] for e in first.values())
    span = 32 * 60 / S["bpm"]
    out = {}
    for idx, e in first.items():
        x = LINE_X0 + (e["t"] - t0) / span * (LINE_X1 - LINE_X0)
        out[idx] = (x, e["midi"])
    return out


LAYOUT = {h: lantern_layout(h) for h in TUNE}


def glow_level(t, hand, idx):
    """How lit lantern idx is: a flash on each of its notes, decaying."""
    g = 0.0
    for e in TUNE[hand]:
        if e["idx"] == idx and e["t"] <= t:
            g = max(g, math.exp(-(t - e["t"]) / 0.9) * (1.3 if e["changed"] else 1.0))
    return g


# ---------------------------------------------------------------- frame
def frame(t):
    p = palette(t)
    sky_top, sky_bot, far_c, mid_c, near_c, water_c, light = p
    img = Image.new("RGB", (W, H))
    # sky gradient
    grad = np.linspace(0, 1, WATER_Y)[:, None, None]
    sky = (np.array(sky_top)[None, None, :] * (1 - grad) + np.array(sky_bot)[None, None, :] * grad)
    arr = np.zeros((H, W, 3), np.float32)
    arr[:WATER_Y] = sky
    arr[WATER_Y:] = np.array(water_c, np.float32)
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    # stars at night
    if light > 0.7:
        sr = np.random.default_rng(11)
        a = clamp01((light - 0.7) / 0.3)
        for k in range(160):
            x, y = sr.uniform(0, W), sr.uniform(0, 520)
            tw = 0.6 + 0.4 * math.sin(t * sr.uniform(1, 3) + k)
            c = mix(sky_top, (240, 236, 220), a * tw * sr.uniform(0.4, 1))
            d.point((x, y), fill=c)
    # water shimmer lines
    for k in range(40):
        y = WATER_Y + 8 + k * 9 + 3 * math.sin(t * 0.8 + k)
        x0 = ((k * 397 + t * 40) % (W + 400)) - 200
        d.line([(x0, y), (x0 + 120 + (k % 5) * 30, y)], fill=mix(water_c, sky_bot, 0.35), width=2)
    # paper-cut layers with drop shadows
    for kind, col in (("far", far_c), ("mid", mid_c)):
        m = scrolled(kind, t)
        sh = m.filter(ImageFilter.GaussianBlur(6))
        img.paste(mix(col, (0, 0, 0), 0.5), (4, 8), ImageChops.multiply(sh, Image.new("L", (W, H), 90)))
        img.paste(col, (0, 0), m)
        if kind == "mid":   # bank edge meets water: reflection band
            refl = m.transpose(Image.FLIP_TOP_BOTTOM).crop((0, H - WATER_Y - 330, W, H - WATER_Y + 60))
            refl = refl.filter(ImageFilter.GaussianBlur(3))
            rl = Image.new("L", refl.size, 0)
            rl.paste(ImageChops.multiply(refl, Image.new("L", refl.size, 70)))
            img.paste(mix(water_c, col, 0.6), (0, WATER_Y), rl)
    boat(img, t, p)
    hands_layer(img, t)
    img = apply_fog(img, t, fog_amount(t, SEC) * 0.85)
    m = scrolled("near", t)
    sh = m.filter(ImageFilter.GaussianBlur(8))
    img.paste((0, 0, 0), (6, 10), ImageChops.multiply(sh, Image.new("L", (W, H), 80)))
    img.paste(near_c, (0, 0), m)
    draw_caption(img, t, SEC, light)
    title_card(img, t)
    return img


F_TITLE = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf", 120)
F_SUB = ImageFont.truetype("C:/Windows/Fonts/georgiai.ttf", 46)


def title_card(img, t):
    """RELAY over the opening dawn: in at 0.4 s, out by 4.5 s."""
    a = clamp01((t - 0.4) / 0.8) * clamp01((4.5 - t) / 1.0)
    if a <= 0:
        return
    d = ImageDraw.Draw(img)
    bg = img.getpixel((960, 260))
    ink = (60, 44, 52)
    d.text((960, 230), "RELAY", font=F_TITLE, anchor="mm", fill=mix(bg, ink, a))
    d.text((960, 320), "one tune, passed between four AIs", font=F_SUB, anchor="mm", fill=mix(bg, ink, a * 0.85))


def geom(t):
    bob = 6 * math.sin(t * 1.3)
    roll = 0.01 * math.sin(t * 0.9 + 1)
    return 960, 790 + bob, bob, roll


def lantern_pos(t, x, midi):
    cx, cy, bob, roll = geom(t)
    mx0, mx1 = LINE_X0 - 40, LINE_X1 + 40
    top = LINE_Y + bob
    y0 = top + 26 * math.sin(math.pi * (x - mx0) / (mx1 - mx0))
    hang = 40 + (79 - midi) * 11

    def R(px, py):
        dx, dy = px - cx, py - cy
        return (cx + dx * math.cos(roll) - dy * math.sin(roll), cy + dx * math.sin(roll) + dy * math.cos(roll))
    return R(x, y0), R(x, y0 + hang)


def provenance(version, idx, t):
    """Colour tint for lantern idx in the given version (which hands have touched it so far)."""
    for h in ("grok", "chatgpt", "last"):
        if CHANGED_IDX[h] == idx and ORDER.index(version) >= ORDER.index(h) and t >= SEC[h] - 1.0:
            return HAND_COL[h]
    return None


def draw_lantern(d, gd, lx, ly, g, light, paper, tint, scale=1.0, alpha=1.0, bg=None):
    base = mix(paper, (236, 200, 150), 0.3)
    if tint:
        base = mix(base, tint, 0.65)
    lit = mix((255, 214, 120), tint, 0.35) if tint else (255, 214, 120)
    col = mix(base, lit, g * 0.9 + 0.1 * light)
    if bg is not None and alpha < 1:
        col = mix(bg, col, alpha)
    w, h = 11 * scale, 16 * scale
    d.rounded_rectangle([lx - w, ly - h, lx + w, ly + h], radius=7 * scale, fill=col, outline=mix(col, (0, 0, 0), 0.35))
    d.line([(lx - w, ly - 5 * scale), (lx + w, ly - 5 * scale)], fill=mix(col, (0, 0, 0), 0.15))
    d.line([(lx - w, ly + 5 * scale), (lx + w, ly + 5 * scale)], fill=mix(col, (0, 0, 0), 0.15))
    a = (g * (0.5 + 0.5 * light) + 0.25 * light) * alpha
    if a > 0.02:
        rr = (26 + 30 * g) * scale
        gc = mix((255, 170, 70), tint, 0.4) if tint else (255, 170, 70)
        gd.ellipse([lx / 2 - rr / 2, ly / 2 - rr / 2, lx / 2 + rr / 2, ly / 2 + rr / 2], fill=tuple(int(c * a) for c in gc))
        wy = WATER_Y + (WATER_Y + 60 - ly) * 0.25 + 40
        gd.ellipse([lx / 2 - 6 * scale, wy / 2 - 2, lx / 2 + 6 * scale, wy / 2 + 2], fill=tuple(int(c * a * 0.8) for c in gc))


def boat(img, t, p):
    sky_top, sky_bot, far_c, mid_c, near_c, water_c, light = p
    hand = current_hand(t)
    lay = LAYOUT.get(hand, LAYOUT["claude"])
    cx, cy, bob, roll = geom(t)
    d = ImageDraw.Draw(img)
    paper = mix((246, 242, 232), sky_top, 0.25 * light)
    shade = mix(paper, (0, 0, 0), 0.22)

    def R(x, y):
        dx, dy = x - cx, y - cy
        return (cx + dx * math.cos(roll) - dy * math.sin(roll), cy + dx * math.sin(roll) + dy * math.cos(roll))
    d.polygon([R(cx - 620, cy + 10), R(cx + 620, cy + 10), R(cx + 520, cy + 70), R(cx - 520, cy + 70)],
              fill=mix(water_c, paper, 0.25))
    d.polygon([R(cx - 640, cy - 60), R(cx + 640, cy - 60), R(cx + 540, cy + 10), R(cx - 540, cy + 10)], fill=paper)
    d.polygon([R(cx - 640, cy - 60), R(cx - 540, cy + 10), R(cx - 480, cy - 60)], fill=shade)
    d.polygon([R(cx + 640, cy - 60), R(cx + 540, cy + 10), R(cx + 480, cy - 60)], fill=shade)
    d.line([R(cx - 540, cy + 10), R(cx + 540, cy + 10)], fill=shade, width=3)
    for k in range(1, 6):                       # paper fold creases
        fx = cx - 540 + k * 180
        d.line([R(fx, cy - 58), R(fx - 30, cy + 8)], fill=mix(paper, shade, 0.5), width=2)
    mx0, mx1 = LINE_X0 - 40, LINE_X1 + 40
    top = LINE_Y + bob
    rope = mix(paper, (50, 40, 30), 0.7)
    for mx in (mx0, mx1):
        d.line([R(mx, cy - 60), R(mx, top - 20)], fill=mix(paper, (60, 50, 40), 0.6), width=6)
    glow = Image.new("RGB", (W // 2, H // 2))
    gd = ImageDraw.Draw(glow)
    r0 = SEC["round"]
    line_a = 1 - clamp01((t - r0) / 3.0)
    if line_a > 0:
        sag = lambda x: top + 26 * math.sin(math.pi * (x - mx0) / (mx1 - mx0))
        d.line([R(x, sag(x)) for x in np.linspace(mx0, mx1, 40)], fill=rope, width=2)
        for idx, (x, midi) in sorted(lay.items()):
            (sx, sy), (lx, ly) = lantern_pos(t, x, midi)
            ly -= (1 - line_a) * 200             # the lanterns rise off the line as the round begins
            d.line([(sx, sy), (lx, ly - 16)], fill=mix(paper, (50, 40, 30), 0.6), width=1)
            g = min(1.0, glow_level(t, hand, idx)) if t < r0 else 0.0
            if hand == "last" and idx == 25 and t < SEC["last"] + 0.5:
                g = max(g, clamp01((t - SEC["last"] + 1.0) / 0.5))
            draw_lantern(d, gd, lx, ly, g, light, paper, provenance(hand, idx, t), alpha=line_a,
                         bg=img.getpixel((int(min(max(lx, 0), W - 1)), int(min(max(ly, 0), H - 1)))))
    if t >= r0 - 1:
        spin = (t - r0) * 0.25
        for (h, rcx, rcy, rad, a, depth) in ring_positions(t, SEC, S["total"]):
            if a <= 0.01:
                continue
            thread = mix(img.getpixel((int(rcx), int(rcy))), rope, a * 0.6)
            d.ellipse([rcx - rad, rcy - rad, rcx + rad, rcy + rad], outline=thread, width=1)
            for idx, (x, midi) in LAYOUT[h].items():
                ang = idx / 26 * 2 * math.pi + spin - math.pi / 2
                lx, ly = rcx + rad * math.cos(ang), rcy + rad * math.sin(ang)
                g = lantern_ring_glow(t, EV, h, idx)
                bg = img.getpixel((int(min(max(lx, 0), W - 1)), int(min(max(ly, 0), H - 1))))
                draw_lantern(d, gd, lx, ly, g, light, paper, provenance(h, idx, 1e9), scale=0.45 + 0.35 * depth,
                             alpha=a, bg=bg)
    glow = glow.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    img.paste(ImageChops.add(img, glow))


def hands_layer(img, t):
    for h in ("grok", "chatgpt", "last"):
        f, _ = hand_state(t, SEC, h)
        if f <= 0:
            continue
        x, midi = LAYOUT[h][CHANGED_IDX[h]]
        _, (lx, ly) = lantern_pos(t, x, midi)
        draw_hand(img, lx, -160 + f * (ly - 18 + 160), h, 1.0, t)
    f = gemini_state(t, SEC)
    if f > 0:
        x, midi = LAYOUT["chatgpt"][12]
        _, (lx, ly) = lantern_pos(t, x, midi)
        draw_hand(img, lx, -160 + f * (ly - 18 + 160), "gemini", 0.9, t)


FIN = None


def finished(t, i):
    global FIN
    if FIN is None:
        FIN = Finisher(W, H, seed=5, **dict(PRESETS["day"], paper=0.05, grain=0.02))
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
