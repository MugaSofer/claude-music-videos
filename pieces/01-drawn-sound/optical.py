"""Core of the optical-sound rule.

Every frame is 1920x1080 at 24 fps. The soundtrack runs at 46080 Hz, so each
frame holds exactly 1920 samples: one per pixel column. A sample's value is the
mean luminance of its column. Nothing else produces sound.
"""
import numpy as np

W, H = 1920, 1080
FPS = 24
SR = W * FPS  # 46080
TWO_PI = 2 * np.pi

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def luma(rgb):
    """rgb: float array in [0,1], shape (..., 3)."""
    return rgb @ LUMA


def columns_to_samples(frame_u8):
    """The decoder's core: one frame (H, W, 3) uint8 -> W audio samples."""
    y = frame_u8.astype(np.float32) @ LUMA / 255.0
    return y.mean(axis=0)


def hex_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


class Voice:
    """A phase accumulator over global sample time, so frames join without clicks.

    freq_fn(t) returns frequency in Hz for an array of times in seconds.
    """

    def __init__(self, freq_fn, phase=0.0):
        self.freq_fn = freq_fn
        self.phase = phase

    def frame_phase(self, frame):
        t = (frame * W + np.arange(W)) / SR
        f = self.freq_fn(t)
        inc = TWO_PI * f / SR
        ph = self.phase + np.cumsum(inc) - inc  # phase at each column's own sample
        self.phase = (self.phase + inc.sum()) % TWO_PI
        return ph, f


def fill_below(img, top, bottom, color, alpha=1.0):
    """Paint columns from fractional `top` (per column) down to `bottom`.

    Anti-aliased at the top edge so column sums vary smoothly with height.
    """
    Y = np.arange(H, dtype=np.float32)[:, None]
    cov = np.clip(Y + 1 - top[None, :], 0, 1)
    if np.isscalar(bottom):
        cov *= (Y < bottom)
    else:
        cov *= np.clip(bottom[None, :] - Y, 0, 1)
    cov *= alpha
    img *= (1 - cov[..., None])
    img += cov[..., None] * color
    return img


def stamp_row(img, phase, freq, stamp, y0, color, center=True):
    """Repeat a stamp (h, w alpha) once per waveform period along the row.

    The stamp keeps its pixel width; the period (= spacing) is SR / freq.
    """
    h, w = stamp.shape
    period = SR / np.maximum(freq, 1e-6)
    u = (phase / TWO_PI) % 1.0
    d = u * period
    if center:
        d = d - (period - w) / 2
    inside = (d >= 0) & (d < w - 1)
    di = np.clip(d, 0, w - 1.001)
    i0 = di.astype(int)
    fr = di - i0
    cols = stamp[:, i0] * (1 - fr) + stamp[:, np.minimum(i0 + 1, w - 1)] * fr
    cols *= inside[None, :]
    region = img[y0:y0 + h]
    region *= (1 - cols[..., None])
    region += cols[..., None] * color
    return img


def silent_grain(rng, strength, h=H, w=W):
    """Texture whose every column sums to zero, so it makes no sound."""
    g = rng.standard_normal((h, w)).astype(np.float32)
    g -= g.mean(axis=0, keepdims=True)
    return g * strength
