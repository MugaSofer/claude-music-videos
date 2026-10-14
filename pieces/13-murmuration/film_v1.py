"""Murmuration: the film. python film.py still OUT.png T [T ...] | smoke x | video OUT.mp4

A sequential particle flock (state carries frame to frame, so stills replay the sim from 0):
each bird is pulled toward its own place in a moving, rotating ellipse, plus an analytic curl-noise
flow for swirls and density waves. The ellipse follows the cello's contour, contracts on each downbeat
(the flock breathes) and stretches into a ribbon as the pianos drift out of phase. The birds arrive
in the gather and spiral down into the reeds at dusk.
"""
import json
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, "../..")
from craft import Finisher, PRESETS, clamp01, ease_in_out  # noqa: E402
from compose import phase_offset  # noqa: E402

W, H, FPS = 1920, 1080, 24
S = json.load(open("score.json"))
EV = S["events"]
SEC = S["sections"]
E8 = S["e8"]
TOTAL = S["total"]
NB = 3500
HORIZON = 860
rng = np.random.default_rng(13)
OFF = rng.normal(0, 0.5, (NB, 2))                               # a dense core thinning outward
OFF *= np.minimum(1, 1.3 / np.maximum(np.linalg.norm(OFF, axis=1, keepdims=True), 1e-6))
T_IN = np.sort(rng.uniform(0.5, 24, NB))                      # arrival times during the gather
T_LAND = SEC["dusk"] + 4 + rng.uniform(0, 20, NB)              # landing times at dusk
DOWNBEATS = np.array([e["t"] for e in EV if e["kind"] == "downbeat"])
CELLO = [(e["t"], e["t"] + e["d"], e["m"]) for e in EV if e["kind"] == "cello"]
WAVES = [(rng.uniform(0.002, 0.006), rng.uniform(0, 6.28), rng.uniform(0.1, 0.4), rng.uniform(0, 6.28), rng.uniform(40, 90))
         for _ in range(6)]


def cello_pitch(t):
    for a, b, m in CELLO:
        if a <= t < b:
            return m
    return None


def attractor(t):
    """(centre x, y, rx, ry, angle)."""
    cx = 960 + 430 * math.sin(0.09 * t) + 120 * math.sin(0.23 * t + 1)
    cy = 400 + 90 * math.sin(0.15 * t + 2)
    m = cello_pitch(t)
    if m is not None:
        cy -= (m - 45) * 9
    k = int(t / E8)
    ph = phase_offset(k)
    since = t - DOWNBEATS[DOWNBEATS <= t].max() if (DOWNBEATS <= t).any() else 9
    breathe = 1 - 0.14 * math.exp(-since / 0.25)
    rx = 230 * (1 + 1.3 * ph) * breathe
    ry = 120 * (1 - 0.45 * ph) * breathe
    ang = 0.4 * math.sin(0.07 * t) + 0.3 * ph
    if t > SEC["dusk"]:
        u = ease_in_out(clamp01((t - SEC["dusk"]) / 18))
        cx += (1100 - cx) * u
        cy += (HORIZON - 30 - cy) * u
        rx *= 1 - 0.5 * u
        ry *= 1 - 0.6 * u
    return cx, cy, rx, ry, ang


def curl(p, t):
    """Velocity from a divergence-free field: v = (dpsi/dy, -dpsi/dx), psi = sum of travelling sines."""
    vx = np.zeros(len(p))
    vy = np.zeros(len(p))
    for k, th, w, ph, a in WAVES:
        kx, ky = k * math.cos(th), k * math.sin(th)
        c = np.cos(kx * p[:, 0] + ky * p[:, 1] + w * t + ph) * a
        vx += c * ky
        vy -= c * kx
    return np.stack([vx, vy], 1) * 160


class Flock:
    def __init__(self):
        self.p = np.stack([np.full(NB, -200.0) - rng.uniform(0, 400, NB), rng.uniform(200, 600, NB)], 1)
        self.v = np.zeros((NB, 2))
        self.t = 0.0

    def step(self, dt):
        t = self.t
        cx, cy, rx, ry, ang = attractor(t)
        ca, sa = math.cos(ang), math.sin(ang)
        tgt = np.stack([cx + OFF[:, 0] * rx * ca - OFF[:, 1] * ry * sa, cy + OFF[:, 0] * rx * sa + OFF[:, 1] * ry * ca], 1)
        active = t >= T_IN
        landed = t >= T_LAND
        tgt[landed, 1] = HORIZON + 10                          # into the reeds
        pull = np.where(active[:, None], (tgt - self.p) * 0.8, np.array([[60.0, 0.0]]))
        want = pull + curl(self.p, t) * np.where(landed, 0.2, 1.0)[:, None]
        self.v = 0.9 * self.v + 0.1 * want
        sp = np.linalg.norm(self.v, axis=1, keepdims=True)
        self.v *= np.minimum(1, 520 / np.maximum(sp, 1e-6))
        self.p += self.v * dt
        self.t += dt


# ---------------------------------------------------------------- picture
def sky(t):
    u = clamp01(t / TOTAL)
    keys = [(0.0, (250, 196, 120), (252, 228, 180)), (0.5, (214, 120, 110), (246, 186, 140)),
            (0.8, (70, 60, 110), (180, 110, 110)), (1.0, (14, 16, 40), (60, 50, 80))]
    for (a, t0, b0), (b, t1, b1) in zip(keys, keys[1:]):
        if a <= u <= b:
            f = (u - a) / (b - a)
            top = [x + (y - x) * f for x, y in zip(t0, t1)]
            bot = [x + (y - x) * f for x, y in zip(b0, b1)]
            break
    y = np.linspace(0, 1, HORIZON)[:, None, None]
    arr = np.zeros((H, W, 3), np.float32)
    arr[:HORIZON] = np.array(top) * (1 - y) + np.array(bot) * y
    arr[HORIZON:] = (np.array(bot) * 0.55)[None, None]
    return arr, top, bot


def reeds_mask():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    r = np.random.default_rng(2)
    d.rectangle([0, HORIZON + 60, W, H], fill=255)
    for _ in range(900):
        x = r.uniform(0, W)
        top = HORIZON - r.uniform(-10, 90)
        d.line([(x, H), (x + r.uniform(-14, 14), top)], fill=255, width=int(r.uniform(2, 4)))
        if r.random() < 0.12:
            d.ellipse([x - 3, top - 14, x + 4, top + 6], fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255


REEDS = reeds_mask()


def render(flock, t):
    arr, top, bot = sky(t)
    # water: a reflected sky strip with shimmer
    water = slice(HORIZON, HORIZON + 60)
    arr[water] = (np.array(bot) * 0.8)[None, None] * (0.9 + 0.1 * np.sin(np.arange(W) / 23 + t)[None, :, None])
    dens = np.zeros((H // 2, W // 2), np.float32)
    p = flock.p
    vis = (p[:, 0] > 0) & (p[:, 0] < W - 1) & (p[:, 1] > 0) & (p[:, 1] < H - 1) & (t < T_LAND + 2.5)
    q = (p[vis] / 2).astype(int)
    np.add.at(dens, (q[:, 1], q[:, 0]), 1.0)
    d = np.asarray(Image.fromarray(np.clip(dens * 170, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
                   .filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    bird = np.array([20, 16, 22], np.float32)
    a = np.clip(d * 1.6, 0, 0.94)[..., None]
    arr = arr * (1 - a) + bird * a
    # the first star, at the very end
    if t > TOTAL - 6:
        s = clamp01((t - (TOTAL - 6)) / 3)
        arr[200:203, 1500:1503] = arr[200:203, 1500:1503] * (1 - s) + 250 * s
    reed_col = np.array([14, 12, 18], np.float32)
    arr = arr * (1 - REEDS[..., None]) + reed_col * REEDS[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


FIN = None


def finish(img, i):
    global FIN
    if FIN is None:
        FIN = Finisher(W, H, seed=13, **dict(PRESETS["day"], paper=0.03, grain=0.02, halation=0.1))
    return (np.clip(FIN(np.asarray(img).astype(np.float32) / 255.0, i), 0, 1) * 255).astype(np.uint8)


def run(t_end, every=None, callback=None, sub=2):
    f = Flock()
    i = 0
    dt = 1 / FPS
    while f.t < t_end - 1e-9:
        for _ in range(sub):
            f.step(dt / sub)
        i += 1
        if callback:
            callback(f, i)
    return f


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "still":
        ts = sorted(float(x) for x in sys.argv[3:])
        ims = []
        f = Flock()
        for t in ts:
            while f.t < t - 1e-9:
                f.step(1 / FPS / 2)
            ims.append(Image.fromarray(finish(render(f, f.t), int(t * FPS))))
        if len(ims) == 1:
            ims[0].save(out)
        else:
            cols, tw, th = 3, 640, 360
            sheet = Image.new("RGB", (tw * cols, th * math.ceil(len(ims) / cols)))
            for k, im in enumerate(ims):
                sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
            sheet.save(out)
    elif mode == "smoke":
        f = Flock()
        while f.t < TOTAL:
            for _ in range(12):
                f.step(1 / FPS / 2)
            render(f, f.t)
        print("smoke OK")
    else:
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                               "-pix_fmt", "yuv420p", "-threads", "2", out], stdin=subprocess.PIPE)
        f = Flock()
        n = int(TOTAL * FPS)
        for i in range(n):
            ff.stdin.write(finish(render(f, f.t), i).tobytes())
            f.step(1 / FPS / 2)
            f.step(1 / FPS / 2)
            if i % 240 == 0:
                print(f"{i / FPS:.0f}s", flush=True)
        ff.stdin.close()
        ff.wait()
