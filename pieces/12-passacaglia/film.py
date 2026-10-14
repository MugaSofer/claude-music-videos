"""Passacaglia: tree rings. python film.py still OUT.png T [T ...] | smoke x | video OUT.mp4 [T0 T1]

Angle = position within the 8-bar ground (clockwise from the top); each variation draws its own ring
outward; pitch nudges a note in or out of its ring; each note is an arc spanning its duration, which
flares when it sounds and then stays as a trace. A clock hand sweeps round. The final D major chord
washes the whole mandala gold.
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, "../..")
from craft import Finisher, PRESETS, clamp01, ease_in_out  # noqa: E402

W, H, FPS, SS = 1920, 1080, 24, 2
E = json.load(open("events.json"))
EV = E["events"]
BAR = E["bar"]
CYCLE = 8 * BAR
T0 = 1.0
TOTAL = E["total"] + 2
CX, CY = W / 2, H / 2
PAL = [(200, 170, 120), (226, 196, 140), (214, 150, 90), (240, 220, 180), (120, 190, 190), (230, 130, 80),
       (160, 120, 170), (250, 200, 110), (255, 236, 200), (200, 210, 230), (255, 214, 120)]
GOLD = (255, 206, 110)
T_FINAL = max(e["t"] for e in EV if e["var"] == 10)


def ring_r(var):
    return 64 + var * 40 if var < 10 else 64


def angle(t):
    return ((t - T0) % CYCLE) / CYCLE * 360 - 90          # PIL degrees, 0 = 3 o'clock, so -90 = top


def mix(a, b, u):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


def make_bg():
    y, x = np.mgrid[0:H, 0:W]
    r = np.hypot(x - CX, y - CY)
    grain = 0.5 + 0.5 * np.sin(r / 6.5 + 2 * np.sin(np.arctan2(y - CY, x - CX) * 3))
    base = np.array([22, 16, 14], np.float32)
    arr = base[None, None] * (0.85 + 0.25 * grain[..., None]) * np.clip(1.3 - r / 900, 0.35, 1.2)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


BG = make_bg()


def camera(t):
    """Zoom so the newest ring fits comfortably; settle at 1.0 when all ten are drawn."""
    var_now = min(9.0, max(0.0, (t - T0) / CYCLE))
    outer = ring_r(var_now) + 60
    return float(np.clip(500 / outer, 1.0, 3.0)) * (1 - 0.04 * ease_in_out(clamp01((t - T_FINAL) / 6)))


def frame(t):
    z = camera(t)
    S = z * SS
    big = Image.new("RGB", (W * SS, H * SS), (0, 0, 0))
    d = ImageDraw.Draw(big)
    glow = Image.new("RGB", (W // 2, H // 2))
    gd = ImageDraw.Draw(glow)
    gold = ease_in_out(clamp01((t - T_FINAL) / 3.0))
    cx, cy = W * SS / 2, H * SS / 2
    # the ground's spokes: 8 faint bar lines
    for b in range(8):
        a = math.radians(b * 45 - 90)
        d.line([(cx, cy), (cx + 470 * S * math.cos(a), cy + 470 * S * math.sin(a))], fill=(34, 26, 22), width=max(1, int(S)))
    for e in EV:
        if e["t"] > t:
            break
        var = e["var"]
        r = (ring_r(var) + (e["m"] - 62) * 0.75) * S
        if var == 10:                                         # the final chord: a full circle
            r = (ring_r(9) + 40 + (e["m"] - 62) * 1.2) * S
        a0 = angle(e["t"])
        span = e["d"] / CYCLE * 360 if var != 10 else 359.9
        a1 = a0 + max(span * min(1.0, (t - e["t"]) / max(e["d"], 0.05)), 1.2)
        age = t - e["t"]
        flare = math.exp(-age / 0.6)
        base = PAL[min(var, 10)]
        col = mix(mix(base, (30, 22, 18), 0.55), base, flare)
        col = mix(col, GOLD, gold * 0.75)
        w = max(1, int((1.5 + 5 * e["v"]) * S * (1 + 0.8 * flare)))
        d.arc([cx - r, cy - r, cx + r, cy + r], start=a0, end=a1, fill=col, width=w)
        if flare > 0.05:
            am = math.radians(a0)
            gx, gy = (cx + r * math.cos(am)) / SS / 2, (cy + r * math.sin(am)) / SS / 2
            rr = 6 + 10 * flare
            gd.ellipse([gx - rr, gy - rr, gx + rr, gy + rr], fill=tuple(int(c * flare * 0.8) for c in base))
    # the clock hand
    if t < T_FINAL:
        a = math.radians(angle(t))
        L = (ring_r(min(9, int((t - T0) / CYCLE))) + 50) * S
        d.line([(cx, cy), (cx + L * math.cos(a), cy + L * math.sin(a))], fill=(120, 100, 80), width=max(1, int(1.5 * S)))
        gd.line([(W / 4, H / 4), (W / 4 + L / SS / 2 * math.cos(a), H / 4 + L / SS / 2 * math.sin(a))], fill=(60, 46, 30), width=3)
    hub = 18 * S
    d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=mix((80, 60, 44), GOLD, gold))
    img = BG.copy()
    img = ImageChops.add(img, big.resize((W, H), Image.LANCZOS))
    img = ImageChops.add(img, glow.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR))
    return img


FIN = None


def finished(t, i):
    global FIN
    if FIN is None:
        FIN = Finisher(W, H, seed=12, **dict(PRESETS["night"], paper=0.03, grain=0.02))
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
