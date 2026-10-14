"""Murmuration: the film (v3: a 3D sheet; lobes follow the pianos' phase; ripples on chord changes). python film.py still OUT.png T [T ...] | smoke x | video OUT.mp4

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
# v3: each bird's place in a thin 3D sheet (an ellipsoid 1 x 0.55 x 0.1), uniform so the edges are sharp
_u = rng.uniform(-1, 1, (NB * 3, 3))
_u = _u[(_u ** 2).sum(1) <= 1][:NB]
OFF3 = _u * np.array([1.0, 0.55, 0.1])
OFF = OFF3[:, :2]                                                # (lag ordering still runs along the long axis)
WANDER = rng.uniform(0, 2 * math.pi, (NB, 2)), rng.uniform(0.3, 0.9, (NB, 2))
T_IN = np.sort(rng.uniform(0.5, 24, NB))                      # arrival times during the gather
T_LAND = SEC["dusk"] + 4 + rng.uniform(0, 20, NB)              # landing times at dusk
DOWNBEATS = np.array([e["t"] for e in EV if e["kind"] == "downbeat"])
WAVE_T = DOWNBEATS[::4]                                         # v3: a ripple on each chord change
CELLO = [(e["t"], e["t"] + e["d"], e["m"]) for e in EV if e["kind"] == "cello"]
WAVES = [(rng.uniform(0.002, 0.006), rng.uniform(0, 6.28), rng.uniform(0.1, 0.4), rng.uniform(0, 6.28), rng.uniform(40, 90))
         for _ in range(6)]


def cello_pitch(t):
    for a, b, m in CELLO:
        if a <= t < b:
            return m
    return None


def attractor(t):
    """(centre x, y, scale px, in-plane angle, roll, yaw, fold, piano phase offset)."""
    cx = 960 + 380 * math.sin(0.13 * t) + 120 * math.sin(0.31 * t + 1)
    cy = 400 + 90 * math.sin(0.19 * t + 2)
    # v2: collective swerves, a square-ish wave so the whole flock reverses quickly every few bars
    sw = math.tanh(4 * math.sin(2 * math.pi * t / (8 * 6 * E8)))
    sw2 = math.tanh(3 * math.sin(2 * math.pi * t / (5 * 6 * E8) + 1.3))
    cx += 240 * sw
    cy += 70 * sw2
    m = cello_pitch(t)
    if m is not None:
        cy -= (m - 45) * 9
    k = int(t / E8)
    ph = phase_offset(k)
    since = t - DOWNBEATS[DOWNBEATS <= t].max() if (DOWNBEATS <= t).any() else 9
    breathe = 1 - 0.12 * math.exp(-since / 0.25)
    R = 300 * breathe
    ang = 0.35 * math.sin(0.07 * t) + 0.25 * sw2
    roll = 0.55 * math.sin(0.21 * t + 0.5) + 0.85 * sw         # the sheet rolls edge-on as it swerves: a dark band
    yaw = 0.6 * math.sin(0.09 * t) + 0.35 * sw2
    fold = 0.55 * math.sin(0.11 * t + 2.0)
    if t > SEC["dusk"]:
        u = ease_in_out(clamp01((t - SEC["dusk"]) / 18))
        cx += (1100 - cx) * u
        cy += (HORIZON - 30 - cy) * u
        R *= 1 - 0.5 * u
        roll *= 1 - u
        ph *= 1 - u
    return cx, cy, R, ang, roll, yaw, fold, ph


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


LAG = 0.05 + 0.11 * (OFF[:, 0] - OFF[:, 0].min()) / (np.ptp(OFF[:, 0]) + 1e-9)   # turns ripple across the flock
FLAP_F = rng.uniform(8.5, 12.0, NB)
FLAP_P = rng.uniform(0, 2 * math.pi, NB)
DEPTH = rng.uniform(0.6, 1.25, NB)


def place3d(t):
    """Every bird's target on screen, and how face-on its wings are to us (|normal . view|)."""
    cx, cy, R, ang, roll, yaw, fold, ph = attractor(t)
    X, Y, Z = OFF3[:, 0].copy(), OFF3[:, 1].copy(), OFF3[:, 2].copy()
    sep = 0.95 * ph                                              # two lobes, as far apart as the pianos are
    Y *= 1 - 0.8 * sep * np.exp(-(X / 0.22) ** 2)                # the neck between them thins
    X = X + 0.5 * sep * np.tanh(X / 0.12)
    Z += fold * (X ** 2 - 0.35)                                  # the sheet bends into a crescent
    tilt = np.zeros(NB)
    for k, tw in enumerate(WAVE_T[(WAVE_T <= t) & (WAVE_T > t - 1.2)]):
        front = (-1.7 + (t - tw) / 0.7 * 3.4) * (1 if int(tw / E8) % 2 else -1)   # crosses in 0.7 s
        g = np.exp(-((X - front) / 0.13) ** 2)
        Z += 0.22 * g
        tilt = np.maximum(tilt, g)
    cr, sr_ = math.cos(roll), math.sin(roll)
    Y2, Z2 = Y * cr - Z * sr_, Y * sr_ + Z * cr
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    X3, Z3 = X * cy_ + Z2 * sy_, -X * sy_ + Z2 * cy_
    persp = 4.0 / (4.0 + Z3)
    u, v = X3 * persp, Y2 * persp
    ca, sa = math.cos(ang), math.sin(ang)
    tgt = np.stack([cx + R * (u * ca - v * sa), cy + R * (u * sa + v * ca)], 1)
    nz = abs(cr * cy_) * (1 - 0.7 * tilt)                       # wings edge-on in a roll or a ripple
    return tgt, nz


class Flock:
    def __init__(self):
        self.p = np.stack([np.full(NB, -200.0) - rng.uniform(0, 400, NB), rng.uniform(200, 600, NB)], 1)
        self.v = np.zeros((NB, 2))
        self.t = 0.0
        self.nz = np.ones(NB)

    def step(self, dt):
        t = self.t
        tgt, self.nz = place3d(t)
        tgt += 10 * np.sin(WANDER[0] + WANDER[1] * t)
        active = t >= T_IN
        landed = t >= T_LAND
        tgt[landed, 1] = HORIZON + 10                          # into the reeds
        pull = np.where(active[:, None], (tgt - self.p) * 1.3, np.array([[60.0, 0.0]]))
        want = pull + 0.45 * curl(self.p, t) * np.where(landed, 0.2, 1.0)[:, None]   # v3: less noise, crisper shapes
        k = LAG[:, None] * 1.6                                # each bird steers with its own lag
        self.v = (1 - k) * self.v + k * want
        sp = np.linalg.norm(self.v, axis=1, keepdims=True)
        self.v *= np.minimum(1, 1100 / np.maximum(sp, 1e-6))
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
    a = np.clip(d * 0.9, 0, 0.7)[..., None]                 # v2: a fainter mass underneath the birds
    arr = arr * (1 - a) + bird * a
    # the first star, at the very end
    if t > TOTAL - 6:
        s = clamp01((t - (TOTAL - 6)) / 3)
        arr[200:203, 1500:1503] = arr[200:203, 1500:1503] * (1 - s) + 250 * s
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw_birds(img, flock, t, vis)
    arr = np.asarray(img).astype(np.float32)
    reed_col = np.array([14, 12, 18], np.float32)
    arr = arr * (1 - REEDS[..., None]) + reed_col * REEDS[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def draw_birds(img, flock, t, vis):
    """Each bird: a small swept-wing silhouette along its heading, flapping (or gliding when slow)."""
    dr = ImageDraw.Draw(img)
    idx = np.nonzero(vis)[0]
    p, v = flock.p[idx], flock.v[idx]
    sp = np.linalg.norm(v, axis=1) + 1e-6
    hx, hy = v[:, 0] / sp, v[:, 1] / sp                       # heading
    nx, ny = -hy, hx                                          # wing direction
    s = 3.2 * DEPTH[idx]
    face = 0.3 + 0.7 * flock.nz[idx]                          # v3: edge-on wings are thin dashes
    flap = np.sin(2 * math.pi * FLAP_F[idx] * t + FLAP_P[idx])
    flap = np.where(sp > 160, flap, 0.15)                     # slow birds glide
    sweep = s * (0.15 + 0.55 * (0.5 + 0.5 * flap))            # wingtips sweep back on the downstroke
    span = s * (1.0 - 0.35 * np.abs(flap)) * face
    for i in range(len(idx)):
        bx, by = p[i]
        l = (bx + nx[i] * span[i] - hx[i] * sweep[i], by + ny[i] * span[i] - hy[i] * sweep[i])
        r = (bx - nx[i] * span[i] - hx[i] * sweep[i], by - ny[i] * span[i] - hy[i] * sweep[i])
        dr.line([l, (bx, by), r], fill=(22, 18, 26), width=1 if s[i] < 3.5 else 2)


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
        t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0       # v2: chunkable; the sim fast-forwards to t0
        t1 = float(sys.argv[4]) if len(sys.argv) > 4 else TOTAL
        i0 = int(round(t0 * FPS))
        for _ in range(i0 * 2):
            f.step(1 / FPS / 2)
        n = int(round(t1 * FPS))
        for i in range(i0, n):
            ff.stdin.write(finish(render(f, f.t), i).tobytes())
            f.step(1 / FPS / 2)
            f.step(1 / FPS / 2)
            if i % 240 == 0:
                print(f"{i / FPS:.0f}s", flush=True)
        ff.stdin.close()
        ff.wait()
