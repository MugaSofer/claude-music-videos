"""Clockwork: the film. python film.py still OUT.png T [T ...] | smoke x | video OUT.mp4 [T0 T1]

Gear sizes follow their revolution times (teeth = 12 per beat of revolution) and meshing gears sit at
the sum of their radii, turning opposite ways. Pins are placed so each passes the top exactly on its
strike beat, where a steel tongue flashes.
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, "../..")
from craft import Finisher, PRESETS, back_out, clamp01, ease_in_out  # noqa: E402
from gears import BEATS, GEARS, RUN_DOWN, STOP, TS, beat_at, tempo  # noqa: E402

W, H, FPS, SS = 1920, 1080, 24, 2
E = json.load(open("events.json"))
EV = E["events"]
TOTAL = E["total"] + 1
MOD = 2.6                                     # px per tooth of pitch radius (world units)
TEETH = {g: 12 * rev for g, (rev, *_rest) in GEARS.items()}
RAD = {g: MOD * n for g, n in TEETH.items()}

# layout: A at the centre; each other gear meshes with a parent at an angle (degrees, screen coords)
PARENT = {"B": ("A", -35), "C": ("A", 195), "D": ("C", 150), "E": ("B", 25)}
POS = {"A": (0.0, 0.0)}
DIR = {"A": 1}
for g in ["B", "C", "D", "E"]:
    p, ang = PARENT[g]
    d = RAD[p] + RAD[g]
    a = math.radians(ang)
    POS[g] = (POS[p][0] + d * math.cos(a), POS[p][1] + d * math.sin(a))
    DIR[g] = -DIR[p]
# centre on the train's visual bounding box (the mean of the centres is pulled toward the small gears)
CX = (min(POS[g][0] - RAD[g] for g in POS) + max(POS[g][0] + RAD[g] for g in POS)) / 2
CY = (min(POS[g][1] - RAD[g] for g in POS) + max(POS[g][1] + RAD[g] for g in POS)) / 2
BRASS = {"A": (196, 150, 70), "B": (210, 168, 86), "C": (186, 138, 64), "D": (176, 128, 58), "E": (222, 182, 100)}

PIN_HITS = {g: [e["t"] for e in EV if e["kind"] == "pin" and e["gear"] == g] for g in GEARS}
ESC = [e["t"] for e in EV if e["kind"] == "esc"]


def angle(g, t):
    """Rotation of gear g (radians, screen-clockwise positive) so pin j is at the top at beat j*rev/pins."""
    rev = GEARS[g][0]
    return DIR[g] * 2 * math.pi * beat_at(t) / rev


def mix(a, b, u):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


def gear_poly(cx, cy, r, n, rot, s):
    """Toothed outline: n trapezoid teeth around pitch radius r (scaled by s)."""
    pts = []
    ro, ri = (r + MOD * 1.1) * s, (r - MOD * 1.3) * s
    for k in range(n):
        a0 = rot + 2 * math.pi * k / n
        w = 2 * math.pi / n
        for (aa, rr) in ((a0, ri), (a0 + w * 0.18, ro), (a0 + w * 0.48, ro), (a0 + w * 0.66, ri)):
            pts.append((cx + rr * math.sin(aa), cy - rr * math.cos(aa)))
    return pts


def velvet():
    r = np.random.default_rng(3)
    n = r.standard_normal((H // 4, W // 4)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n - n.min()) / (n.max() - n.min()) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
                   .filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255
    y, x = np.mgrid[0:H, 0:W]
    lamp = np.clip(1.25 - np.hypot((x - 900) / 1100, (y - 420) / 800), 0.2, 1.1)
    base = np.array([22, 28, 58], np.float32)
    arr = base[None, None] * (0.75 + 0.35 * n[..., None]) * lamp[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


VELVET = velvet()


def camera(t):
    """(world x, world y, zoom): overview drift, pushing in on each gear as it arrives."""
    zx, zy, z = CX, CY, 0.92
    for g, (rev, pins, enter, inst) in GEARS.items():
        u = clamp01((t - (enter - 1.5)) / 2.5) * clamp01((enter + 7 - t) / 3)
        u = ease_in_out(u)
        gx, gy = POS[g]
        zx, zy, z = zx + (gx - zx) * u * 0.55, zy + (gy - zy) * u * 0.55, z + 0.35 * u
    rd = ease_in_out(clamp01((t - RUN_DOWN) / (STOP - RUN_DOWN)))
    z *= 1 - 0.12 * rd
    return zx + 30 * math.sin(t * 0.05), zy + 18 * math.sin(t * 0.04), z


def frame(t):
    img = VELVET.copy()
    cx, cy, z = camera(t)
    S = z * SS

    def P(x, y):
        return ((x - cx) * S + W * SS / 2, (y - cy) * S + H * SS / 2)

    rd = clamp01((t - RUN_DOWN) / (STOP - RUN_DOWN + 6))
    cool = rd * 0.45
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # the back plate (soft, engraved rings)
    px, py = P(CX, CY)
    pr = 560 * S
    plate = mix((120, 92, 50), (70, 74, 96), cool)
    d.ellipse([px - pr, py - pr * 0.8, px + pr, py + pr * 0.8], fill=plate + (255,))
    for k in range(6):
        rr = pr * (0.3 + 0.12 * k)
        d.ellipse([px - rr, py - rr * 0.8, px + rr, py + rr * 0.8], outline=mix(plate, (60, 44, 24), 0.4) + (255,), width=max(1, int(2 * SS)))
    back = layer.filter(ImageFilter.GaussianBlur(6 * SS))           # shallow depth of field
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    glow = Image.new("RGB", (W // 2, H // 2))
    gd = ImageDraw.Draw(glow)
    for g in ["D", "C", "A", "B", "E"]:
        rev, pins, enter, inst = GEARS[g]
        drop = clamp01((t - (enter - 0.9)) / 0.9)
        if drop <= 0:
            continue
        gx, gy = POS[g]
        gy -= (1 - back_out(drop)) * 420                              # dropping onto its arbor
        rot = angle(g, t)
        x, y = P(gx, gy)
        col = mix(BRASS[g], (150, 150, 170), cool)
        shade = mix(col, (40, 26, 10), 0.45)
        sx, sy = x + 10 * SS, y + 14 * SS                            # cast shadow
        d.polygon(gear_poly(sx, sy, RAD[g], TEETH[g], rot, S), fill=(0, 0, 0, 110))
        d.polygon(gear_poly(x, y, RAD[g], TEETH[g], rot, S), fill=col + (255,), outline=shade + (255,))
        # spokes: cut-outs between arms, drawn in the plate colour behind
        arms = 5 if RAD[g] > 100 else 4
        ri, ro = RAD[g] * 0.3 * S, RAD[g] * 0.78 * S
        for k in range(arms):
            a0 = rot + 2 * math.pi * k / arms + 0.25
            a1 = a0 + 2 * math.pi / arms - 0.5
            poly = [(x + ri * math.sin(a), y - ri * math.cos(a)) for a in np.linspace(a0, a1, 6)]
            poly += [(x + ro * math.sin(a), y - ro * math.cos(a)) for a in np.linspace(a1, a0, 10)]
            d.polygon(poly, fill=mix(shade, (20, 20, 40), 0.55) + (255,))
        d.ellipse([x - ro, y - ro, x + ro, y + ro], outline=mix(col, (255, 240, 200), 0.25) + (255,), width=max(1, int(3 * SS)))
        # bevel: lamp light on the upper-left rim, shadow on the lower-right
        rb = (RAD[g] - MOD * 2.5) * S
        wb = max(2, int(RAD[g] * 0.07 * S))
        d.arc([x - rb, y - rb, x + rb, y + rb], start=165, end=285, fill=mix(col, (255, 244, 210), 0.45) + (255,), width=wb)
        d.arc([x - rb, y - rb, x + rb, y + rb], start=345, end=105, fill=mix(col, (40, 24, 8), 0.4) + (255,), width=wb)
        hr = RAD[g] * 0.16 * S
        d.ellipse([x - hr, y - hr, x + hr, y + hr], fill=mix(col, (255, 240, 200), 0.3) + (255,))
        jr = hr * 0.45
        d.ellipse([x - jr, y - jr, x + jr, y + jr], fill=(150, 20, 40, 255))            # jewel bearing
        d.ellipse([x - jr * 0.4, y - jr * 0.6, x + jr * 0.1, y - jr * 0.1], fill=(255, 190, 200, 255))
        # pins, and the steel tongue at the top that they strike
        npins = len(pins)
        pr_ = RAD[g] * 0.88 * S
        for j in range(npins):
            a = rot - DIR[g] * 2 * math.pi * j / npins
            qx, qy = x + pr_ * math.sin(a), y - pr_ * math.cos(a)
            r0 = 8 * S
            d.ellipse([qx - r0, qy - r0, qx + r0, qy + r0], fill=(236, 232, 224, 255), outline=(90, 80, 70, 255))
        hit = max([math.exp(-(t - h) / 0.25) for h in PIN_HITS[g] if h <= t] or [0.0])
        tx, ty = x, y - (RAD[g] + MOD * 4) * S
        bend = 6 * S * hit
        d.line([(tx - 62 * S, ty - 20 * S), (tx - 2 * S, ty - 2 * S + bend)], fill=(190, 196, 210, 255), width=max(2, int(8 * S)))
        if hit > 0.03 and drop >= 1:
            rr = 18 * hit + 5
            gd.ellipse([tx / SS / 2 - rr, ty / SS / 2 - rr, tx / SS / 2 + rr, ty / SS / 2 + rr],
                       fill=tuple(int(c * hit * 0.6) for c in mix((255, 220, 150), (200, 220, 255), cool)))
    # winding key on gear A's arbor (0.5-7 s), turning in steps with the ratchet
    if t < 8.5:
        ka = 0.0 if t < 0.5 else (min(t, 7) - 0.5) * 5.2
        kx, ky = P(*POS["A"])
        a = clamp01((8.5 - t) / 1.2)
        kl = 70 * S
        d.line([(kx - kl * math.cos(ka), ky - kl * math.sin(ka)), (kx + kl * math.cos(ka), ky + kl * math.sin(ka))],
               fill=(210, 200, 180, int(255 * a)), width=max(2, int(16 * S)))
    # balance wheel (top right), swinging with the escapement
    bx, by = P(POS["B"][0] + 200, POS["B"][1] - 230)
    last = max([e for e in ESC if e <= t] or [0.0])
    k = sum(1 for e in ESC if e <= t)
    swing = (1 if k % 2 else -1) * (1 - math.exp(-(t - last) / 0.12)) * 0.9 * min(1.0, tempo(t) / 100 + 0.05)
    br = 70 * S
    d.ellipse([bx - br, by - br, bx + br, by + br], outline=(210, 170, 90, 255), width=max(2, int(6 * S)))
    d.line([(bx - br * math.cos(swing), by - br * math.sin(swing)), (bx + br * math.cos(swing), by + br * math.sin(swing))],
           fill=(210, 170, 90, 255), width=max(2, int(4 * S)))
    for q in range(8):   # hairspring
        rr = br * (0.1 + 0.08 * q)
        d.arc([bx - rr, by - rr, bx + rr, by + rr], start=q * 40 + math.degrees(swing), end=q * 40 + 300 + math.degrees(swing),
              fill=(170, 176, 190, 255), width=1)

    big = Image.alpha_composite(back, layer).resize((W, H), Image.LANCZOS)
    img.paste(big, (0, 0), big)
    glow = glow.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)
    img = ImageChops.add(img, glow)
    if rd > 0:                                                        # the evening cools and dims
        arr = np.asarray(img).astype(np.float32) * (1 - 0.3 * rd)
        img = Image.fromarray(arr.astype(np.uint8))
    return img


FIN = None


def finished(t, i):
    global FIN
    if FIN is None:
        FIN = Finisher(W, H, seed=10, **dict(PRESETS["night"], paper=0.02, grain=0.02))
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
