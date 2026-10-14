"""Murmuration v4: the film, from a real flocking simulation (boids.py). Same sky, reeds, birds and score as
v1-v3; only the motion source changed. python film4.py still OUT.png T [T ...] | video OUT.mp4 [t0 t1]

The music steers lightly instead of puppeteering: the roost drifts with the cello and a slow sway; every chord
change (each 4th downbeat) startles one edge of the flock; the gather is a stream arriving from the left;
at dusk the altitude band sinks and the birds pour down into the reeds.
"""
import math
import subprocess
import sys

import numpy as np
from PIL import Image

import boids as Bd
import film as F

W, H, FPS = F.W, F.H, F.FPS
NB = F.NB
CAM = Bd.Camera(W, H, pos=(0.0, 2.0, -115.0), f=1600.0, horizon=F.HORIZON)   # longer lens: less size swing
STARTLES = F.DOWNBEATS[::4]
DUSK = F.SEC["dusk"]


class Sim:
    def __init__(self):
        self.b = Bd.Boids(NB, centre=(-150.0, 40.0, 0.0))
        r = np.random.default_rng(4)
        self.b.p[:, 0] = -110 - r.exponential(60, NB)              # a long stream, arriving through the gather
        self.b.v[:] = np.array([Bd.CRUISE, 0, 0]) + r.normal(0, 0.8, (NB, 3))
        self.t = 0.0
        self.landed = np.zeros(NB, bool)
        self.next_s = 0

    def roost(self, t):
        x = 22 * math.sin(0.11 * t) + 10 * math.sin(0.29 * t + 1.0)
        m = F.cello_pitch(t)
        if m is not None:
            x += (m - 45) * 0.8
        z = 8 * math.sin(0.07 * t + 2.0)
        if t > DUSK:
            u = F.ease_in_out(F.clamp01((t - DUSK) / 12))
            x = x * (1 - u) + 12 * u
        return np.array([x, 0.0, z])

    def step(self, dt):
        t = self.t
        while self.next_s < len(STARTLES) and STARTLES[self.next_s] <= t:
            if STARTLES[self.next_s] > 30:
                self.b.add_startle(t)
            self.next_s += 1
        alt, band, land = 36.0, 7.0, None
        if t > DUSK:
            u = F.clamp01((t - DUSK) / 14)
            alt, band = 36 - 26 * u, 7 - 4 * u
            land = F.clamp01((t - DUSK - 15) / 9)
        self.b.step(dt, t, self.roost(t), alt=alt, alt_band=band, landing=land)
        self.landed |= (self.b.p[:, 1] < 2.5) & (t > DUSK)
        self.t += dt

    def view(self):
        """Screen positions, screen velocities, perspective scale, wing visibility."""
        b = self.b
        xy, z, sv = CAM.project(b.p, b.v)
        f = b.v / (np.linalg.norm(b.v, axis=1, keepdims=True) + 1e-9)
        up = np.array([0.0, 1.0, 0.0])
        side = np.cross(f, up)
        side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-9
        upb = np.cross(side, f)
        n = upb * np.cos(b.roll)[:, None] + side * np.sin(b.roll)[:, None]     # the wing plane's normal, banked
        c = b.p - CAM.pos
        c /= np.linalg.norm(c, axis=1, keepdims=True)
        face = np.abs((n * c).sum(1))
        return xy, sv, 115.0 / z, face


class View:
    """What film.draw_birds expects: p, v (screen), nz."""
    def __init__(self, p, v, nz):
        self.p, self.v, self.nz = p, v, nz


def render(sim, t):
    arr, top, bot = F.sky(t)
    arr[F.HORIZON:F.HORIZON + 60] = (np.array(bot) * 0.8)[None, None] * (0.9 + 0.1 * np.sin(np.arange(W) / 23 + t)[None, :, None])
    xy, sv, scale, face = sim.view()
    vis = (xy[:, 0] > 0) & (xy[:, 0] < W - 1) & (xy[:, 1] > 0) & (xy[:, 1] < H - 1) & ~sim.landed
    dens = np.zeros((H // 2, W // 2), np.float32)
    q = (xy[vis] / 2).astype(int)
    np.add.at(dens, (q[:, 1], q[:, 0]), 1.0)
    d = np.asarray(Image.fromarray(np.clip(dens * 120, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
    a = np.clip(d * 0.8, 0, 0.6)[..., None]
    arr = arr * (1 - a) + np.array([20, 16, 22], np.float32) * a
    if t > F.TOTAL - 6:
        s = F.clamp01((t - (F.TOTAL - 6)) / 3)
        arr[200:203, 1500:1503] = arr[200:203, 1500:1503] * (1 - s) + 250 * s
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    F.DEPTH = np.clip(scale * 0.95, 0.35, 2.2)                     # perspective size for film.draw_birds
    F.draw_birds(img, View(xy, sv, np.clip(face * 1.3, 0, 1)), t, vis)
    arr = np.asarray(img).astype(np.float32)
    arr = arr * (1 - F.REEDS[..., None]) + np.array([14, 12, 18], np.float32) * F.REEDS[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def advance(sim, t):
    while sim.t < t - 1e-9:
        sim.step(1 / FPS / 2)


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "still":
        ts = sorted(float(x) for x in sys.argv[3:])
        sim, ims = Sim(), []
        for t in ts:
            advance(sim, t)
            ims.append(Image.fromarray(F.finish(render(sim, sim.t), int(t * FPS))))
        cols, tw, th = 3, 640, 360
        sheet = Image.new("RGB", (tw * cols, th * math.ceil(len(ims) / cols)))
        for k, im in enumerate(ims):
            sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
        sheet.save(out)
    else:
        t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        t1 = float(sys.argv[4]) if len(sys.argv) > 4 else F.TOTAL
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                               "-pix_fmt", "yuv420p", "-threads", "2", out], stdin=subprocess.PIPE)
        sim = Sim()
        i0 = int(round(t0 * FPS))
        advance(sim, i0 / FPS)                                         # chunkable: the sim fast-forwards
        for i in range(i0, int(round(t1 * FPS))):
            ff.stdin.write(F.finish(render(sim, sim.t), i).tobytes())
            advance(sim, (i + 1) / FPS)
            if i % 240 == 0:
                print(f"{i / FPS:.0f}s", flush=True)
        ff.stdin.close()
        ff.wait()
