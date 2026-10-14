"""Piece 2 v4 finishing: we watch the city through a rainy window, and the camera leans in
toward the convergence.

- camera(t): a slow push toward the convergence point, easing back out after it.
- rain(img, t): beads on the glass, each a small lens that shows a blurred, flipped view of the
  city behind it with a bright rim; a few drops run down leaving trails.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

W, H = 1920, 1080
R = np.random.default_rng(12)
N_BEADS = 520
BX = R.uniform(0, W, N_BEADS)
BY = R.uniform(0, H, N_BEADS)
BR = R.uniform(3, 11, N_BEADS) * R.choice([1, 1, 1, 1.8], N_BEADS)
RUNNERS = [(R.uniform(80, W - 80), R.uniform(0, 60), R.uniform(9, 14), R.uniform(30, 90), R.uniform(0, 140))
           for _ in range(14)]          # (x, start y, radius, speed px/s, start time)


def camera(t, t_conv, total, focus):
    """Zoom and focus point: a slow lean in toward the convergence, then easing back."""
    if t < t_conv:
        k = (t / t_conv) ** 1.8
    else:
        k = max(0.0, 1 - (t - t_conv) / (total - t_conv)) ** 0.7
    z = 1.0 + 0.32 * k
    fx = W / 2 + (focus[0] - W / 2) * k
    fy = H / 2 + (focus[1] - H / 2) * k
    return z, fx, fy


def apply_camera(img, z, fx, fy):
    if z <= 1.001:
        return img
    cw, ch = W / z, H / z
    x0 = np.clip(fx - cw / 2, 0, W - cw)
    y0 = np.clip(fy - ch / 2, 0, H - ch)
    im = Image.fromarray(img).crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BICUBIC)
    return np.asarray(im)


def _bead(out, src_blur, x, y, r):
    x, y, r = int(x), int(y), max(int(r), 2)
    if x - 3 * r < 0 or x + 3 * r >= W or y - 3 * r < 0 or y + 3 * r >= H:
        return
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    d = np.sqrt(xx * xx + yy * yy) / r
    m = d <= 1
    # a lens: sample a wider, vertically flipped patch of the blurred city
    sy = np.clip((y - yy * 2.2).astype(int), 0, H - 1)
    sx = np.clip((x - xx * 2.2).astype(int), 0, W - 1)
    lens = src_blur[sy, sx]
    rim = np.clip((d - 0.72) / 0.28, 0, 1)[..., None] * 0.35
    shade = (0.85 + 0.15 * (1 - d))[..., None]
    patch = lens * shade + rim * 255
    hi = (np.abs(xx + r * 0.35) < r * 0.22) & (np.abs(yy + r * 0.4) < r * 0.18)   # a specular glint
    patch[hi] = patch[hi] * 0.3 + 255 * 0.7
    region = out[y - r:y + r + 1, x - r:x + r + 1]
    region[m] = np.clip(patch[m], 0, 255)


def rain(img, t):
    src_blur = gaussian_filter(img.astype(np.float32), (6, 6, 0))
    out = img.astype(np.float32).copy()
    for x, y, r in zip(BX, BY, BR):
        _bead(out, src_blur, x, y, r)
    for (x, y0, r, v, ts) in RUNNERS:
        age = (t - ts) % 40
        y = y0 + age * v * (1 + 0.3 * np.sin(age))
        if y > H + 20:
            continue
        # the trail: a faint wet streak above the running drop
        top = int(max(y0, y - 260))
        xi = int(x + 4 * np.sin(y / 40))
        if 0 < xi < W - 4 and int(y) > top:
            out[top:int(y), xi - 2:xi + 2] = out[top:int(y), xi - 2:xi + 2] * 0.85 + src_blur[top:int(y), xi - 2:xi + 2] * 0.15 + 6
        _bead(out, src_blur, xi, y, r)
    return np.clip(out, 0, 255).astype(np.uint8)
