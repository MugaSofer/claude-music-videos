"""Murmuration v4: a real flocking simulation (Muga: "why aren't you using boids?" Fair: v1-v3 puppeteered
every bird toward a place in a target shape, and the motion floated because it was imposed, not emergent).

A 3D starling model in the spirit of Reynolds (boids), Ballerini et al. 2008 (each starling tracks its ~7 nearest
neighbours, not everyone within a radius) and Hemelrijk & Hildenbrandt's StarDisplay (cruise speed, roost
attraction, banked turns):
  * separation from very close neighbours; alignment with and cohesion toward the 7 nearest (topological);
  * a cruise speed the birds return to; turning limited, so the flock has momentum;
  * a horizontal pull toward the roost that grows with distance (keeps them over the reeds, in frame),
    and a soft altitude band;
  * the music steers, lightly: the roost drifts with the cello; on each chord change one edge of the flock
    is startled (a sharp turn away from a point), and the turn spreads by alignment: an agitation wave.
World units are metres; the camera projects to the 1920x1080 frame.
"""
import math

import numpy as np
from scipy.spatial import cKDTree

K = 7               # topological neighbours
CRUISE = 11.0       # m/s
SEP_R = 1.1         # m
W_SEP, W_ALI, W_COH = 6.0, 2.2, 0.9
W_ROOST, W_ALT = 0.010, 0.6
TURN_MAX = 3.2      # rad/s, so turns take time and the flock has momentum
ROOST_MAX = 7.0     # m/s^2


class Boids:
    def __init__(self, n, seed=13, centre=(0.0, 40.0, 0.0)):
        r = np.random.default_rng(seed)
        self.r = r
        self.n = n
        self.p = r.normal(0, 1, (n, 3)) * np.array([14.0, 4.0, 9.0]) + np.array(centre)
        d = np.array([1.0, 0.0, 0.25]) / np.linalg.norm([1.0, 0.0, 0.25])
        self.v = d * CRUISE + r.normal(0, 0.8, (n, 3))
        self.roll = np.zeros(n)
        self.startle = []          # (time, origin xyz, direction)

    def step(self, dt, t, roost, alt=40.0, alt_band=12.0, landing=None, coh=1.0, extra=None):
        p, v = self.p, self.v
        tree = cKDTree(p)
        dist, idx = tree.query(p, k=K + 1)
        dist, idx = dist[:, 1:], idx[:, 1:]
        nb_p = p[idx]                                   # (n, K, 3)
        nb_v = v[idx]
        # separation: away from neighbours closer than SEP_R, harder the closer
        off = p[:, None, :] - nb_p
        w = np.clip(SEP_R - dist, 0, None) / (dist + 1e-3)
        sep = (off * w[..., None]).sum(1)
        ali = nb_v.mean(1) - v
        cv = nb_p.mean(1) - p
        acc = W_SEP * sep + W_ALI * ali + W_COH * coh * cv          # coh: a gain the film can raise
        if extra is not None:
            acc += extra
        # roost: horizontal pull growing with distance; a soft altitude band
        roost = np.asarray(roost, float)
        h = (roost[..., [0, 2]] if roost.ndim == 2 else roost[[0, 2]]) - p[:, [0, 2]]   # one roost, or one per bird
        rp = W_ROOST * h * np.linalg.norm(h, axis=1, keepdims=True)
        rn = np.linalg.norm(rp, axis=1, keepdims=True)
        acc[:, [0, 2]] += rp * np.minimum(1, ROOST_MAX / (rn + 1e-9))   # capped: far birds don't sprint home
        dy = p[:, 1] - alt
        acc[:, 1] -= W_ALT * np.sign(dy) * np.clip(np.abs(dy) - alt_band, 0, None)
        # startles: birds near the origin turn hard away from it (the wave then spreads by alignment)
        for ts, o, dirn in self.startle:
            a = t - ts
            if 0 <= a < 0.6:
                d = np.linalg.norm(p - o, axis=1)
                g = np.exp(-(d / 6.0) ** 2) * (1 - a / 0.6)
                acc += g[:, None] * dirn * 28.0                  # v4c: softer (40 tore the flock up)
        if landing is not None:                          # at dusk: down into the reeds
            acc[:, 1] += landing * (-6.0 - 0.4 * (p[:, 1] - 2.0))
        # speed: back toward cruise
        sp = np.linalg.norm(v, axis=1, keepdims=True)
        acc += (CRUISE - sp) * v / (sp + 1e-6) * 1.5
        acc += self.r.normal(0, 0.6, acc.shape)
        nv = v + acc * dt
        # limit the turn rate (momentum)
        cosang = (nv * v).sum(1) / (np.linalg.norm(nv, axis=1) * np.linalg.norm(v, axis=1) + 1e-9)
        ang = np.arccos(np.clip(cosang, -1, 1))
        lim = TURN_MAX * dt
        k = np.where(ang > lim, lim / (ang + 1e-9), 1.0)[:, None]
        nv = v + (nv - v) * k
        # bank: roll with the horizontal turn rate (Hemelrijk's banking), for the drawing
        hv0, hv1 = v[:, [0, 2]], nv[:, [0, 2]]
        cross = hv0[:, 0] * hv1[:, 1] - hv0[:, 1] * hv1[:, 0]
        turn = cross / (np.linalg.norm(hv0, axis=1) * np.linalg.norm(hv1, axis=1) + 1e-9) / dt
        self.roll = 0.85 * self.roll + 0.15 * np.clip(turn * 0.5, -1.3, 1.3)
        self.v = nv
        self.p = p + nv * dt

    def add_startle(self, t, rng=None):
        """Startle the flock's edge: pick an outlying bird, push its neighbourhood away from the centre."""
        c = self.p.mean(0)
        far = np.argmax(np.linalg.norm(self.p - c, axis=1) * self.r.uniform(0.7, 1.0, self.n))
        o = self.p[far]
        d = o - c
        d[1] *= 0.3
        d = -d / (np.linalg.norm(d) + 1e-9)                # turn back in, across the flock
        d = d + np.array([0, self.r.uniform(-0.3, 0.3), 0])
        self.startle.append((t, o.copy(), d / np.linalg.norm(d)))


class Camera:
    """A fixed camera on the marsh, looking at the sky over the reeds."""
    def __init__(self, W=1920, H=1080, pos=(0.0, 2.0, -160.0), f=1250.0, horizon=860):
        self.W, self.H, self.pos, self.f, self.hz = W, H, np.array(pos), f, horizon

    def project(self, p, v=None):
        q = p - self.pos
        z = np.maximum(q[:, 2], 1.0)
        x = self.W / 2 + self.f * q[:, 0] / z
        y = self.hz - self.f * q[:, 1] / z + self.f * self.pos[1] / z * 0     # y up in the world, down on screen
        out = np.stack([x, y], 1)
        if v is None:
            return out, z
        q2 = q + v * 0.05
        z2 = np.maximum(q2[:, 2], 1.0)
        x2 = self.W / 2 + self.f * q2[:, 0] / z2
        y2 = self.hz - self.f * q2[:, 1] / z2
        return out, z, (np.stack([x2, y2], 1) - out) / 0.05
