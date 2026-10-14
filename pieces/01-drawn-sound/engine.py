"""Layers for "Everything Here Is Heard". All sound comes from what these draw.

Periodic things are driven by Voices (phase accumulators over global sample time),
so a count of k per frame sounds at 24k Hz and stands still.
"""
import numpy as np

from optical import W, H, SR, FPS, TWO_PI

X = np.arange(W, dtype=np.float64)


# ---------------------------------------------------------------- curves
class Curve:
    """Piecewise-linear value over time (seconds). Keys: [(t, v), ...]."""

    def __init__(self, keys):
        keys = sorted(keys)
        self.t = np.array([k[0] for k in keys], dtype=np.float64)
        self.v = np.array([k[1] for k in keys], dtype=np.float64)

    def __call__(self, t):
        return np.interp(t, self.t, self.v)


def notes_curve(notes, start, beat, glide=0.08, hold_last=True):
    """notes: [(harmonic_k, beats), ...] -> Curve of k over time, with short glides."""
    keys, t = [], start
    prev = None
    for k, b in notes:
        if prev is None:
            keys.append((t, k))
        else:
            keys.append((t, prev))
            keys.append((t + glide, k))
        prev = k
        t += b * beat
    keys.append((t, prev))
    return Curve(keys), t


class Voice:
    """Unwrapped phase accumulator (cycles, float64) so stamps keep identities."""

    def __init__(self, k_curve, detune=None):
        self.k_curve = k_curve          # harmonic number over time (24 Hz units)
        self.detune = detune            # optional drift in px/frame over time
        self.cyc = 0.0

    def frame(self, frame):
        t = (frame * W + X) / SR
        f = 24.0 * self.k_curve(t)
        if self.detune is not None:
            v = self.detune(t)
            f = f * W / (W - v)
        inc = f / SR
        cyc = self.cyc + np.cumsum(inc) - inc
        self.cyc += inc.sum()
        return cyc, f


# ---------------------------------------------------------------- drawing
def blend_band(img, y0, cov, color):
    """cov: (h, W) alpha for rows y0..y0+h."""
    h = cov.shape[0]
    y0 = int(y0)
    a, b = max(y0, 0), min(y0 + h, H)
    if b <= a:
        return
    c = cov[a - y0:b - y0, :, None]
    region = img[a:b]
    region *= (1 - c)
    region += c * color


def fill_between(img, top, bottom, color, alpha=1.0):
    """Fill each column from fractional `top` down to fractional `bottom` (arrays or scalars)."""
    top = np.broadcast_to(np.asarray(top, np.float64), (W,))
    bottom = np.broadcast_to(np.asarray(bottom, np.float64), (W,))
    y0 = int(max(np.floor(top.min()), 0))
    y1 = int(min(np.ceil(bottom.max()) + 1, H))
    if y1 <= y0:
        return
    Y = np.arange(y0, y1, dtype=np.float64)[:, None]
    cov = np.clip(Y + 1 - top[None, :], 0, 1) * np.clip(bottom[None, :] - Y, 0, 1)
    blend_band(img, y0, (cov * alpha).astype(np.float32), color)


def soft_pulse(u, center, width, soft):
    """1 inside [center-width/2, center+width/2] (periodic u in [0,1)), soft edges."""
    d = np.abs(((u - center + 0.5) % 1.0) - 0.5)
    return np.clip((width / 2 - d) / max(soft, 1e-6) + 0.5, 0, 1)


def smooth_noise(x, seed, scale):
    """Deterministic smooth 1-D noise in [-1, 1]."""
    rng = np.random.default_rng(seed)
    n = int(W / scale) + 4
    pts = rng.uniform(-1, 1, n)
    xs = np.arange(n) * scale - scale
    return np.interp(x, xs, pts)


def hash_noise(i, seed):
    """Per-integer pseudo-random in [0,1)."""
    i = np.asarray(i, dtype=np.int64)
    h = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return (h & 0xFFFF) / 65536.0


def stamp_row(img, cyc, freq, stamp, y_of_center, color, alpha=1.0):
    """One stamp per waveform period, centred in its period, each at its own height.

    stamp: (h, w) float alpha. y_of_center(xc) -> top row per stamp, from the stamp's
    screen x centre, so heights are stable while the count stays the same.
    """
    h, w = stamp.shape
    period = SR / np.maximum(freq, 1e-6)
    u = cyc % 1.0
    d = u * period - (period - w) / 2            # column within stamp
    inside = (d >= 0) & (d < w - 1)
    xc = X - d + w / 2                            # this stamp's centre on screen
    ytop = np.round(y_of_center(xc)).astype(int)
    di = np.clip(d, 0, w - 1.001)
    i0 = di.astype(int)
    fr = (di - i0)[None, :]
    cols = (stamp[:, i0] * (1 - fr) + stamp[:, np.minimum(i0 + 1, w - 1)] * fr) * (inside * alpha)[None, :]
    cols = cols.astype(np.float32)
    rows = ytop[None, :] + np.arange(h)[:, None]
    ok = (rows >= 0) & (rows < H) & (cols > 0)
    r, c = rows[ok], np.broadcast_to(X.astype(int), rows.shape)[ok]
    a = cols[ok][:, None]
    img[r, c] = img[r, c] * (1 - a) + a * color


def bird_stamp(w, h, flap):
    x = np.linspace(-1, 1, w)[None, :]
    y = np.linspace(-1, 1, h)[:, None]
    wing_y = -0.15 + (0.6 - 1.0 * flap) * np.abs(x) ** 1.25
    wing = np.exp(-((y - wing_y) / 0.2) ** 2) * (1 - np.abs(x) ** 4)
    body = np.exp(-(x / 0.24) ** 2 - ((y - 0.05) / 0.34) ** 2)
    return np.clip(wing + body, 0, 1).astype(np.float32)


def dot_stamp(r, soft=1.0):
    s = int(2 * r + 3)
    x = np.arange(s) - (s - 1) / 2
    d = np.sqrt(x[None, :] ** 2 + x[:, None] ** 2)
    return np.clip((r - d) / soft + 0.5, 0, 1).astype(np.float32)


def rect_stamp(w, h, soft=0.8):
    x = np.arange(w) - (w - 1) / 2
    y = np.arange(h) - (h - 1) / 2
    ax = np.clip((w / 2 - np.abs(x)) / soft, 0, 1)
    ay = np.clip((h / 2 - np.abs(y)) / soft, 0, 1)
    return (ay[:, None] * ax[None, :]).astype(np.float32)


def silent_grain(rng, strength, h=H):
    g = rng.standard_normal((h, W)).astype(np.float32)
    g -= g.mean(axis=0, keepdims=True)
    return g * strength
