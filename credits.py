"""End cards with credits for the posted pieces (Muga's suggestion, 2026-10-12).

Each card is styled for its piece (a palette and one small motif from it): the piece's final frame, blurred and
darkened (Journey: its own lithograph paper), with the title, a one-line description, the credits, and a line for
Muga. It cross-fades in over the end of the piece and holds; the audio is padded with silence.

    python credits.py card NAME      ->  WORK/cards/NAME.png  (to check the design)
    python credits.py video NAME     ->  WORK/NN/NAME_final-1080p.mp4
    python credits.py all
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

WORK = "E:/Claude/music-video-2-work"
HOLD = 6.0          # seconds of card after the cross-fade starts
XF = 1.2            # cross-fade length
MADE = "Made in code by Claude (Opus 5.5)"
PURE = "no samples, no image models"
FOR = "For Muga, who said \u201csurprise me\u201d"
# name: (file, fps, title, description, credits, Muga's lines, style)
PIECES = {
    "passacaglia": ("12/passacaglia_v2-1080p.mp4", 24, "Passacaglia",
                    "an eight-bar ground under ten variations, drawn as tree rings",
                    [MADE, "Synthesised piano; " + PURE], [FOR], "rings"),
    "murmuration": ("13/murmuration_v4-1080p.mp4", 24, "Murmuration",
                    "two pianos drift out of phase; the starlings part and rejoin with them",
                    [MADE, "A flocking simulation after Reynolds, Ballerini et al. and Hemelrijk", "No samples, no image models"],
                    [FOR + ",", "and suggested boids after three floaty drafts"], "flock"),
    "journey": ("03/journey_v12-1080p.mp4", 30, "The Tune That Travelled",
                "one folk tune, handed down the centuries",
                [MADE, "Figures painted by a Claude subagent (Opus 5.5)",
                 "Hum: \u201cHumming C D A\u201d by drotzruhn (Freesound, CC0), re-pitched"],
                [FOR + ",", "then asked for a real hum and a better piano,",
                 "had the shepherd hum too, and caught what I missed"], "contour"),
    "signal": ("11/signal_v3-1080p.mp4", 24, "Signal",
               "a lighthouse and a small boat, talking in Morse",
               [MADE, "The melody is the Morse; " + PURE],
               [FOR + ",", "then found the first score slow and dull (it was)"], "morse"),
    "relay": ("07/relay_v3-1080p.mp4", 24, "Relay",
              "one tune, passed between four AIs",
              [MADE, "With changes by Grok and ChatGPT; Gemini let it pass"],
              [FOR + ",", "and spotted the bulrushes floating off their stems"], "relay"),
    "small_hours": ("05/small_hours_v5-1080p.mp4", 24, "Small Hours",
                    "the people who keep a city going through the night",
                    ["Lyrics and city by Claude (Opus 5.5); music: Suno",
                     "Vignettes painted by four Claude subagents (Opus 5.5)"],
                    [FOR + ",", "and caught a lorry appearing out of thin air,",
                     "then a legless baker and a hole in the dawn"], "windows"),
    "maintenance": ("04/maint_v5-1080p.mp4", 30, "Maintenance",
                    "an abandoned glasshouse, still keeping its gardener\u2019s routines",
                    ["Idea: Grok", MADE],
                    [FOR + ",", "then asked for a real score and better gloves"], "leaves"),
}
# the pieces made without Muga's notes: full-resolution masters (their phone copies were all Muga had), with
# loudness-matched audio from hd_audio/ (Drawn Sound: untouched, its picture IS its waveform)
SOLO = [FOR + ",", "then went travelling; this one I made solo"]
PURE_ALL = [MADE, "No samples, no image models"]
PIECES.update({
    "drawn_sound": ("01/v4.mkv", 24, "Drawn Sound",
                    "optical sound: the picture\u2019s columns are the waveform", PURE_ALL, SOLO, "wave",
                    "hd_audio/01_hd.wav"),
    "city": ("02/city_v4.mp4", 30, "Player Piano City",
             "a four-voice tempo canon, drawn as piano-roll towers that converge", PURE_ALL, SOLO, "roll",
             "hd_audio/02_hd.wav"),
    "transit": ("06/transit_v1.mp4", 24, "Transit Canon",
                "a metro map where every line is a looping voice; the trains all meet at Central", PURE_ALL, SOLO,
                "metro", "hd_audio/06_hd.wav"),
    "tidal": ("08/tidal_v1.mp4", 24, "Tidal Clock",
              "a harbour where the boats ring as the waves lift them", PURE_ALL, SOLO, "tide", "hd_audio/08_hd.wav"),
    "typewriter": ("09/typewriter_v1.mp4", 24, "Typewriter Weather",
                   "a letter typed at night; the keys are the drums", PURE_ALL, SOLO, "type", "hd_audio/09_hd.wav"),
    "clockwork": ("10/clockwork_v3.mp4", 24, "Clockwork",
                  "a gear train of rhythms that winds down to a stop", PURE_ALL, SOLO, "gear", "hd_audio/10_hd.wav"),
})
F_TYPE = ImageFont.truetype("C:/Windows/Fonts/courbd.ttf", 92)
F_TITLE = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf", 96)
F_SUB = ImageFont.truetype("C:/Windows/Fonts/georgiai.ttf", 40)
F_CRED = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 34)
F_MUGA = ImageFont.truetype("C:/Windows/Fonts/georgiai.ttf", 32)
F_TINY = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 24)
CREAM = (238, 230, 212)
DIM = (196, 188, 172)
MORSE = {"S": "...", "I": "..", "G": "--.", "N": "-.", "A": ".-", "L": ".-.."}
# the parlour's version of Journey's tune (from timeline.json), for its contour
TUNE_F = [293.7, 392.0, 493.9, 587.3, 659.3, 587.3, 493.9, 392.0, 440.0, 493.9, 440.0, 392.0, 329.6, 293.7, 329.6,
          392.0, 440.0, 392.0, 587.3, 493.9, 587.3, 784.0, 740.0, 659.3]
TUNE_D = [0.65, 1.42, 0.65, 1.42, 0.65, 0.65, 0.65, 0.65, 2.13, 1.42, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 1.42,
          0.65, 1.42, 0.65, 1.42, 0.65, 0.65]


def motif(style, im, y):
    """One small motif from each piece, drawn on an RGBA layer over the background."""
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(7)
    if style == "rings":                                   # tree rings behind the title, gold
        for k, r in enumerate(range(150, 620, 38)):
            a = max(8, int(44 - k * 2.4))
            ts = np.linspace(0, 2 * np.pi, 240)
            rr = r + 6 * np.sin(5 * ts + k)
            pts = list(zip(960 + rr * np.cos(ts), 470 + rr * np.sin(ts) * 0.92))
            d.line(pts + [pts[0]], fill=(226, 184, 104, a), width=2)
    elif style == "flock":                                 # a small flock, dark against the dusk
        c = np.array([1430.0, 170.0])
        for _ in range(260):
            q = rng.normal(0, 1, 2)
            p = c + q * np.array([120, 34]) + np.array([0, 18 * q[0] ** 2])
            s = rng.uniform(3, 6)
            d.line([(p[0] - s, p[1] - s * 0.5), (p[0], p[1]), (p[0] + s, p[1] - s * 0.5)], fill=(22, 18, 26, 230), width=2)
    elif style == "contour":                               # the tune's own contour, in ink
        xs = np.cumsum([0] + TUNE_D[:-1])
        xs = 560 + xs / xs[-1] * 800
        ys = y + 196 - np.log2(np.array(TUNE_F) / 293.7) * 34
        d.line(list(zip(xs, ys)), fill=(70, 48, 32, 255), width=3, joint="curve")
        for x_, y_ in zip(xs, ys):
            d.ellipse([x_ - 5, y_ - 4, x_ + 5, y_ + 4], fill=(70, 48, 32, 255))
    elif style == "morse":                                 # SIGNAL in Morse, lighthouse-warm and boat-cool by turns
        units = []
        for k, ch in enumerate("SIGNAL"):
            for sym in MORSE[ch]:
                units.append((1 if sym == "." else 3, k % 2))
                units.append((1, None))
            units.append((2, None))
        x = 960 - sum(u for u, _ in units) * 9 / 2
        for u, who in units:
            if who is not None:
                col = (255, 210, 140) if who == 0 else (170, 200, 255)
                for g, a in ((10, 40), (6, 90), (0, 255)):
                    d.rounded_rectangle([x - g, y + 140 - 4 - g, x + u * 9 - 2 + g, y + 140 + 4 + g], radius=4 + g,
                                        fill=col + (a,))
            x += u * 9
    elif style == "relay":                                 # the hand-offs: four coloured hands on one line
        cols = [("Claude", (204, 120, 92)), ("Grok", (190, 190, 200)), ("ChatGPT", (16, 163, 127)),
                ("Gemini", (120, 140, 235))]
        xs = [690 + k * 180 for k in range(4)]
        d.line([(xs[0], y + 142), (xs[-1], y + 142)], fill=(150, 142, 128, 200), width=2)
        for (nm, col), x in zip(cols, xs):
            d.ellipse([x - 13, y + 129, x + 13, y + 155], fill=col + (255,))
            d.text((x, y + 182), nm, font=F_TINY, fill=DIM + (255,), anchor="mm")
    elif style == "windows":                               # a paper-cut row of houses, some windows lit
        x = -20
        while x < 1940:
            w = int(rng.uniform(110, 200))
            h = int(rng.uniform(90, 190))
            d.rectangle([x, 1080 - h, x + w, 1080], fill=(26, 30, 60, 255))
            for wy in range(1080 - h + 18, 1080 - 24, 34):
                for wx in range(x + 14, x + w - 24, 30):
                    if rng.random() < 0.28:
                        d.rectangle([wx, wy, wx + 14, wy + 18], fill=(255, 200, 120, 255))
            x += w + int(rng.uniform(4, 16))
    elif style == "leaves":                                # sprigs either side of the title
        for side in (-1, 1):
            x0 = 960 + side * 430
            path = [(x0 + side * 120 * t, y + 10 - 50 * np.sin(np.pi * t * 0.8)) for t in np.linspace(0, 1, 20)]
            d.line(path, fill=(70, 110, 64, 255), width=3)
            for k in range(1, 5):
                t = k / 4
                cx, cy = x0 + side * 120 * t, y + 10 - 50 * np.sin(np.pi * t * 0.8)
                for flip in (-1, 1):
                    ang = -np.pi / 2 * flip + side * 0.5
                    L, Wd = 40 - 8 * t, 13 - 3 * t
                    us = np.linspace(0, np.pi, 16)
                    pts = [(cx + np.cos(ang) * L * (1 - np.cos(u)) / 2 - np.sin(ang) * Wd * np.sin(u) * s_,
                            cy + np.sin(ang) * L * (1 - np.cos(u)) / 2 + np.cos(ang) * Wd * np.sin(u) * s_)
                           for s_ in (1, -1) for u in (us if s_ == 1 else us[::-1])]
                    d.polygon(pts, fill=(96, 150, 88, 235))
    elif style in ("wave", "tide"):                        # a drawn waveform / a swell
        xs = np.linspace(620, 1300, 500)
        u = (xs - 620) / 680
        if style == "wave":
            ys = y + 172 + 18 * np.sin(u * 2 * np.pi * 9) * np.sin(u * np.pi) * (0.6 + 0.4 * np.sin(u * 2 * np.pi * 2.3))
            col = (238, 214, 160, 255)
        else:
            ys = y + 168 + 12 * np.sin(u * 2 * np.pi * 2.2) + 6 * np.sin(u * 2 * np.pi * 5.1 + 1)
            col = (150, 190, 220, 255)
        d.line(list(zip(xs, ys)), fill=col, width=3, joint="curve")
    elif style == "roll":                                  # four voices' piano-roll bars, converging to a chord
        cols = [(240, 176, 80), (90, 196, 150), (90, 130, 230), (230, 120, 150)]
        for k, col in enumerate(cols):
            for j in range(6):
                x0 = 640 + j * 108 + (5 - j) * (k - 1.5) * 9
                d.rounded_rectangle([x0, y + 148 + k * 10, x0 + 70 + 6 * j, y + 155 + k * 10], radius=3, fill=col + (230,))
    elif style == "metro":                                 # three lines meeting at Central
        cols = [(220, 70, 60), (60, 140, 220), (70, 170, 90)]
        cx, cy = 960, y + 178
        for k, col in enumerate(cols):
            a = (k - 1) * 0.42
            p0 = (cx - 330 * np.cos(a), cy - 70 * np.sin(a))
            p1 = (cx + 330 * np.cos(a), cy + 70 * np.sin(a))
            d.line([p0, (cx, cy), p1], fill=col + (255,), width=7)
            for t in (0.3, 0.65):
                for p in (p0, p1):
                    qx, qy = cx + (p[0] - cx) * t, cy + (p[1] - cy) * t
                    d.ellipse([qx - 7, qy - 7, qx + 7, qy + 7], fill=(238, 230, 212, 255), outline=col + (255,), width=3)
        d.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill=(238, 230, 212, 255), outline=(40, 40, 50, 255), width=4)
    elif style == "gear":                                  # a brass gear behind the title
        cx, cy, n = 960, 360, 18
        pts = []
        for k in range(n * 4):
            a = 2 * np.pi * k / (n * 4)
            r = 300 if (k % 4) in (1, 2) else 262
            pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
        d.polygon(pts, outline=(196, 156, 82, 70), width=3)
        d.ellipse([cx - 210, cy - 210, cx + 210, cy + 210], outline=(196, 156, 82, 50), width=3)
        d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], outline=(196, 156, 82, 60), width=3)
    im.alpha_composite(lay)


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                          "csv=p=0", path]).decode().strip())


def card(name):
    src, fps, title, sub, creds, muga, style = PIECES[name][:7]
    path = f"{WORK}/{src}"
    last = f"{WORK}/cards/{name}_last.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.5", "-i", path, "-frames:v", "1", last], check=True)
    if style == "contour":                                  # Journey: ink on its own lithograph paper
        g = np.random.default_rng(3).normal(0, 1, (270, 480, 1)).astype(np.float32)
        base = np.array([227, 213, 180], np.float32) * (1 + 0.025 * g)
        im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((1920, 1080), Image.BICUBIC).convert("RGBA")
        ink, ink2 = (60, 42, 30), (110, 86, 64)
    elif style == "flock":                                  # Murmuration ends in night; its card is the dusk
        t = np.linspace(0, 1, 1080)[:, None, None]
        top, bot = np.array([52, 44, 86], np.float32), np.array([178, 104, 108], np.float32)
        im = Image.fromarray(np.broadcast_to(top * (1 - t) + bot * t, (1080, 1920, 3)).astype(np.uint8)).convert("RGBA")
        ink, ink2 = CREAM, (232, 214, 206)
    else:
        im = Image.open(last).convert("RGB").filter(ImageFilter.GaussianBlur(14))
        im = ImageEnhance.Brightness(im).enhance(0.2 if style in ("metro", "type") else 0.32).convert("RGBA")
        ink, ink2 = CREAM, DIM
    y = 330
    motif(style, im, y)
    d = ImageDraw.Draw(im)
    d.text((960, y), title, font=F_TYPE if style == "type" else F_TITLE, fill=ink, anchor="mm")
    d.text((960, y + 88), sub, font=F_SUB, fill=ink2, anchor="mm")
    own = style in ("contour", "morse", "relay", "wave", "tide", "roll", "metro")            # these motifs sit where the divider would
    yy = y + (220 if own else 150)
    if not own:
        d.line([(860, yy), (1060, yy)], fill=(150, 142, 128), width=2)
    yy += 60
    for c in creds:
        d.text((960, yy), c, font=F_CRED, fill=ink, anchor="mm")
        yy += 50
    yy += 26
    for c in muga:
        d.text((960, yy), c, font=F_MUGA, fill=ink2, anchor="mm")
        yy += 44
    out = f"{WORK}/cards/{name}.png"
    im.convert("RGB").save(out)
    return out


def video(name):
    src, fps = PIECES[name][:2]
    audio = f"{WORK}/{PIECES[name][7]}" if len(PIECES[name]) > 7 else None
    path = f"{WORK}/{src}"
    png = card(name)
    dur = duration(path)
    out = f"{WORK}/{src.split('/')[0]}/{name}_final-1080p.mp4"
    off = dur - 0.15                                     # the card fades in over the very end of the piece
    total = off + HOLD
    fc = (f"[1:v]format=yuv420p,fps={fps},settb=AVTB,setsar=1[c];[0:v]format=yuv420p,fps={fps},settb=AVTB,setsar=1,"
          f"tpad=stop_mode=clone:stop_duration={XF}[v0];"
          f"[v0][c]xfade=transition=fade:duration={XF}:offset={off:.3f},format=yuv420p[v];"   # xfade may output 4:4:4
          f"[{2 if audio else 0}:a]apad=whole_dur={total:.3f}[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-loop", "1", "-framerate", str(fps), "-t", str(HOLD + XF),
                    "-i", png] + (["-i", audio] if audio else []) + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
                    "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-threads", "3", "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-level", "4.2", "-c:a", "aac", "-b:a", "256k",
                    "-movflags", "+faststart", out], check=True)
    print(name, "->", out, f"{total:.1f}s", flush=True)


if __name__ == "__main__":
    import os
    os.makedirs(f"{WORK}/cards", exist_ok=True)
    mode = sys.argv[1]
    names = list(PIECES) if mode == "all" else [sys.argv[2]]
    for n in names:
        (card if mode == "card" else video)(n)
