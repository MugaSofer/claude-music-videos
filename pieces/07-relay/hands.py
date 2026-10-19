"""Relay stage 2: the hands, captions, Gemini's fog and the round finale (lantern-ring carousel).

Imported by film.py. Everything is timed from score.json sections.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from craft import clamp01, ease_in_out

HAND_COL = {"claude": (204, 120, 92), "grok": (44, 44, 52), "chatgpt": (16, 163, 127),
            "gemini": (120, 140, 235), "last": (204, 120, 92)}
CHANGED_IDX = {"grok": 23, "chatgpt": 24, "last": 25}
CAPTIONS = {
    "claude": ("Claude", "the seed: a tune that ends high and open"),
    "grok": ("Grok", "\u201cso the phrase \u2026 lands with a cleaner, more resolved feel\u201d"),
    "chatgpt": ("ChatGPT", "\u201ca little unresolved tension rather than a full arrival\u201d"),
    "gemini": ("Gemini", "an error each time; the tune went on unchanged"),   # v4: was an invented quote
    "last": ("Claude", "the rest becomes an A, so the tune can be passed around forever"),
}
F_NAME = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf", 60)
F_QUOTE = ImageFont.truetype("C:/Windows/Fonts/georgiai.ttf", 44)


def mix(a, b, u):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


# ---------------------------------------------------------------- hand choreography
def hand_state(t, sec, hand):
    """(tip_y_fraction 0=offscreen..1=at lantern, swapped?) for the hand arriving at section `hand`."""
    s = sec[hand]
    a, arrive, hold, leave = s - 4.5, s - 2.2, s - 1.0, s + 1.6
    if t < a or t > leave + 0.1:
        return 0.0, t >= hold
    if t < arrive:
        return ease_in_out((t - a) / (arrive - a)), False
    if t < hold:
        return 1.0, False
    return 1.0 - ease_in_out((t - hold) / (leave - hold)), True


def gemini_state(t, sec):
    """Gemini's hand: reaches, hovers with a tremor, withdraws without taking anything."""
    s = sec["gemini"]
    a, arrive, leave, gone = s - 4.5, s - 2.0, s + 1.5, s + 5.0
    if t < a or t > gone:
        return 0.0
    if t < arrive:
        return 0.85 * ease_in_out((t - a) / (arrive - a))
    if t < leave:
        return 0.85 + 0.04 * math.sin(t * 7)
    return 0.89 * (1 - ease_in_out((t - leave) / (gone - leave)))


def draw_hand(img, x, tip_y, style, alpha=1.0, t=0.0):
    """An arm reaching down from the top edge to a pinching hand whose fingertips are at (x, tip_y)."""
    if tip_y < -10:
        return
    col = HAND_COL[style]
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    wrist_y = tip_y - 120
    if style == "grok":            # angular, faceted, with a spark at the fingertip
        d.polygon([(x - 34, -20), (x + 30, -20), (x + 26, wrist_y), (x - 30, wrist_y)], fill=col + (a,))
        d.polygon([(x - 44, wrist_y - 10), (x + 40, wrist_y - 10), (x + 34, wrist_y + 60), (x + 6, tip_y - 6),
                   (x - 8, tip_y - 6), (x - 40, wrist_y + 60)], fill=col + (a,))
        d.polygon([(x - 44, wrist_y + 10), (x - 60, wrist_y + 70), (x - 20, wrist_y + 60)], fill=mix(col, (90, 90, 100), 0.5) + (a,))
        sp = 10 + 4 * math.sin(t * 20)
        d.line([(x - sp, tip_y), (x + sp, tip_y)], fill=(255, 255, 255, a), width=3)
        d.line([(x, tip_y - sp), (x, tip_y + sp)], fill=(255, 255, 255, a), width=3)
    elif style == "chatgpt":       # rounded, soft
        d.rounded_rectangle([x - 32, min(-40, wrist_y + 9), x + 32, wrist_y + 10], radius=30, fill=col + (a,))
        d.ellipse([x - 48, wrist_y - 20, x + 48, wrist_y + 80], fill=col + (a,))
        for k, dx in enumerate((-24, -8, 8, 24)):
            d.rounded_rectangle([x + dx - 8, wrist_y + 50, x + dx + 8, tip_y - 2 + (k in (0, 3)) * -18],
                                radius=8, fill=mix(col, (255, 255, 255), 0.08) + (a,))
    elif style == "gemini":        # a constellation hand: faint gradient stars, never quite solid
        rng = np.random.default_rng(4)
        for k in range(700):
            u = rng.uniform(0, 1)
            if u < 0.55:           # forearm
                px, py = x + rng.normal(0, 18), -20 + u / 0.55 * (wrist_y + 20)
            elif u < 0.8:          # palm
                px, py = x + rng.normal(0, 26), wrist_y + rng.uniform(-10, 70)
            else:                  # fingers
                f = rng.integers(0, 4)
                px, py = x - 24 + 16 * f + rng.normal(0, 4), wrist_y + 60 + rng.uniform(0, tip_y - wrist_y - 60)
            c = mix((130, 110, 240), (120, 200, 255), py / max(tip_y, 1))
            tw = 0.5 + 0.5 * math.sin(t * 3 + k)
            r = rng.uniform(1.8, 4.2)
            d.ellipse([px - r, py - r, px + r, py + r], fill=c + (int(a * (0.5 + 0.45 * tw)),))
    else:                          # claude: warm terracotta, ink-outlined
        ink = (60, 34, 26, a)
        d.polygon([(x - 30, -20), (x + 28, -20), (x + 26, wrist_y + 4), (x - 30, wrist_y + 4)], fill=col + (a,), outline=ink)
        d.ellipse([x - 44, wrist_y - 12, x + 44, wrist_y + 76], fill=col + (a,), outline=ink, width=3)
        for k, dx in enumerate((-22, -7, 8, 23)):
            ln = tip_y - (wrist_y + 50) - (14 if k in (0, 3) else 0)
            d.rounded_rectangle([x + dx - 7, wrist_y + 48, x + dx + 7, wrist_y + 48 + ln], radius=7,
                                fill=col + (a,), outline=ink, width=2)
        d.line([(x - 26, 0), (x - 22, wrist_y - 20)], fill=(236, 160, 130, a // 2), width=4)   # highlight
    shadow = layer.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 0.35)
    img.paste((0, 0, 0), (10, 16), shadow)
    img.paste(layer, (0, 0), layer)


# ---------------------------------------------------------------- captions
def draw_caption(img, t, sec, light):
    order = ["claude", "grok", "chatgpt", "gemini", "last"]
    for i, h in enumerate(order):
        s = sec[h] + (5.0 if h == "claude" else 1.5)
        e = (sec[order[i + 1]] - 4.5) if i + 1 < len(order) else sec["round"] - 1
        a = clamp01((t - s) / 1.2) * clamp01((e - t) / 1.2)
        if a <= 0:
            continue
        name, quote = CAPTIONS[h]
        # v3: a soft band behind the caption so it reads on any sky (pale by day, dark by night)
        night = light > 0.5
        band = Image.new("L", img.size, 0)
        ImageDraw.Draw(band).rounded_rectangle([60, 868, 60 + 40 + max(F_NAME.getlength(name), F_QUOTE.getlength(quote)), 1012],
                                               radius=20, fill=int(255 * a * (0.55 if night else 0.5)))
        band = band.filter(ImageFilter.GaussianBlur(14))
        img.paste((10, 10, 22) if night else (246, 240, 228), (0, 0), band)
        d = ImageDraw.Draw(img)
        ink = (236, 230, 220) if night else (36, 30, 28)          # v3: full contrast against the band
        bg = img.getpixel((110, 950))
        d.text((90, 880), name, font=F_NAME, fill=mix(bg, ((150, 172, 255) if night else (60, 76, 180)) if h == "gemini" else HAND_COL[h] if h != "grok" else ink, a),
               stroke_width=2, stroke_fill=mix(bg, mix(bg, (255, 255, 255) if light < 0.5 else (0, 0, 0), 0.25), a))
        d.text((90, 956), quote, font=F_QUOTE, fill=mix(bg, ink, a * 0.95))


# ---------------------------------------------------------------- fog (Gemini)
def fog_amount(t, sec):
    s, e = sec["gemini"], sec["last"]
    return clamp01((t - (s - 4)) / 5) * clamp01((e + 2 - t) / 5)


def apply_fog(img, t, amount, rng_cache={}):
    if amount <= 0.01:
        return img
    if "n" not in rng_cache:
        r = np.random.default_rng(9)
        n = r.standard_normal((27, 96)).astype(np.float32)
        rng_cache["n"] = np.array(Image.fromarray(((n - n.min()) / (n.max() - n.min()) * 255).astype(np.uint8))
                                  .resize((1920 * 2, 1080), Image.BICUBIC)).astype(np.float32) / 255
    n = rng_cache["n"]
    off = int(t * 30) % 1920
    band = n[:, off:off + 1920]
    y = np.linspace(0, 1, 1080)[:, None]
    dens = amount * (0.25 + 0.5 * np.exp(-((y - 0.62) / 0.18) ** 2)) * (0.6 + 0.6 * band)
    arr = np.asarray(img).astype(np.float32)
    fogc = np.array([176, 184, 198], np.float32)
    arr = arr * (1 - dens[..., None]) + fogc * dens[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- the round: rings of lanterns
ROUND_ORDER = ["claude", "grok", "chatgpt", "gemini", "last"]


def ring_positions(t, sec, total):
    """Carousel of 5 rings: (hand, cx, cy, radius, alpha, depth)."""
    r0 = sec["round"]
    out = []
    merge = clamp01((t - (total - 9)) / 5)           # at the end all rings drift into one
    for j, h in enumerate(ROUND_ORDER):
        ang = j * 2 * math.pi / 5 + (t - r0) * 0.18 + math.pi / 2
        depth = 0.5 + 0.5 * math.sin(ang)             # 1 = front
        cx = 960 + 520 * math.cos(ang) * (1 - merge)
        cy = 400 + 70 * math.sin(ang) * (1 - merge)
        rad = (70 + 50 * depth) * (1 - merge) + 150 * merge
        enter = r0 + j * 6 * 60 / 84                  # each voice's entrance
        a = clamp01((t - enter + 1.0) / 1.5)
        if merge > 0 and h != "last":
            a *= 1 - merge
        out.append((h, cx, cy, rad, a, depth if merge < 1 else 1.0))
    return sorted(out, key=lambda r: r[5])


def lantern_ring_glow(t, events, hand, idx):
    g = 0.0
    for e in events:
        if e["hand"] == hand and e["idx"] == idx and e["t"] <= t and e["section"] == 6:
            g = max(g, math.exp(-(t - e["t"]) / 0.8))
    return g
