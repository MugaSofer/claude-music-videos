"""Shared craft toolkit for all the pieces: the finishing pass, easing, boil, contact sheets, sync checks.

Built after studying how the stronger code-made music videos were made (see research-craft.md):
a textured surface beats flat shapes, secondary motion makes it feel alive, and sync is verified
by script, not by eye.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, zoom

# ------------------------------------------------------------------ easing and motion
def clamp01(x):
    return np.clip(x, 0.0, 1.0)


def ease_in_out(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out_cubic(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def back_out(x, s=1.70158):
    """Overshoots a little and settles: things arrive with life."""
    x = clamp01(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def elastic_out(x, p=0.35):
    x = clamp01(x)
    return np.where(x <= 0, 0.0, np.where(x >= 1, 1.0, 2 ** (-10 * x) * np.sin((x - p / 4) * 2 * np.pi / p) + 1))


def pulse(t, hits, decay=0.18, lead=0.0):
    """Sum of exponential pulses at the given hit times (seconds): a 'kick' envelope for beats."""
    hits = np.asarray(hits)
    d = t + lead - hits
    d = d[(d >= 0) & (d < decay * 8)]
    return float(np.exp(-d / decay).sum())


def drift(t, seed=0, amp=1.0, speed=0.07):
    """A slow, organic 2-D wander (for a camera that is never quite still)."""
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 2 * np.pi, 6)
    x = np.sin(t * speed * 2 * np.pi + ph[0]) + 0.5 * np.sin(t * speed * 4.3 + ph[1]) + 0.25 * np.sin(t * speed * 9.1 + ph[2])
    y = np.sin(t * speed * 1.7 * np.pi + ph[3]) + 0.5 * np.sin(t * speed * 3.7 + ph[4]) + 0.25 * np.sin(t * speed * 8.3 + ph[5])
    return amp * x / 1.75, amp * y / 1.75


# ------------------------------------------------------------------ boil (hand-drawn line jitter)
def _hash(ix, seed):
    ix = np.asarray(ix, dtype=np.int64)
    h = (ix * 374761393 + seed * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return (h & 0xFFFF) / 65535.0 * 2 - 1


def boil(pts, t, amp=1.5, rate=12, seed=0):
    """Jitter polygon points, reseeded `rate` times a second, as if redrawn by hand each drawing."""
    k = int(t * rate)
    pts = np.asarray(pts, float)
    n = len(pts)
    idx = np.arange(n) + seed * 1000
    dx = _hash(idx * 2 + k * 7919, seed + 1) * amp
    dy = _hash(idx * 2 + 1 + k * 7919, seed + 2) * amp
    return np.stack([pts[:, 0] + dx, pts[:, 1] + dy], 1)


# ------------------------------------------------------------------ the finishing pass
class Finisher:
    """Film/paper finishing for float RGB frames in [0,1].

    grade: lift blacks, warm highlights, gentle S-curve. halation: bright areas bleed a warm red
    glow (as on film). bloom: a soft white glow. paper: a fixed fibrous texture multiplied in.
    grain: fresh every frame, strongest in the midtones. vignette.
    """

    def __init__(self, W=1920, H=1080, seed=7, paper=0.06, grain=0.035, vignette=0.28, halation=0.35,
                 bloom=0.18, lift=0.03, warmth=0.04, contrast=0.12, paper_tint=(1.0, 0.985, 0.95)):
        self.W, self.H = W, H
        self.opts = dict(paper=paper, grain=grain, vignette=vignette, halation=halation, bloom=bloom, lift=lift,
                         warmth=warmth, contrast=contrast)
        r = np.random.default_rng(seed)
        # paper: low-frequency mottling + fine fibres
        low = gaussian_filter(r.standard_normal((H // 8 + 1, W // 8 + 1)), 3)
        low = zoom(low, 8, order=1)[:H, :W]
        fine = gaussian_filter(r.standard_normal((H, W)), 0.7)
        fib = np.zeros((H, W))
        for _ in range(900):
            x, y = r.uniform(0, W), r.uniform(0, H)
            a, L = r.uniform(0, np.pi), r.uniform(8, 40)
            xs = np.clip((x + np.cos(a) * np.linspace(0, L, 24)).astype(int), 0, W - 1)
            ys = np.clip((y + np.sin(a) * np.linspace(0, L, 24)).astype(int), 0, H - 1)
            fib[ys, xs] += 1
        tex = low * 0.6 + fine * 0.3 + gaussian_filter(fib, 0.6) * 0.8
        tex = (tex - tex.mean()) / (tex.std() + 1e-9)
        self.paper = (1 + paper * tex)[..., None] * np.array(paper_tint)[None, None, :]
        self.paper = self.paper.astype(np.float32)
        Y, X = np.ogrid[:H, :W]
        v = ((X - W / 2) / (W / 2)) ** 2 + ((Y - H / 2) / (H / 2)) ** 2
        self.vig = (1 - vignette * v ** 1.2).clip(0.3, 1).astype(np.float32)[..., None]

    def __call__(self, img, frame_index=0):
        o = self.opts
        x = np.clip(img.astype(np.float32), 0, 1)
        # halation + bloom from highlights, computed at quarter resolution
        lum = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        hi = np.clip((lum - 0.72) / 0.28, 0, 1) ** 1.5              # only genuinely bright light halates
        small = hi[::4, ::4]
        hal = gaussian_filter(small, 10)
        blm = gaussian_filter(small, 4)
        hal = zoom(hal, 4, order=1)[:self.H, :self.W, None]
        blm = zoom(blm, 4, order=1)[:self.H, :self.W, None]
        x = x + o['halation'] * hal * np.array([1.0, 0.42, 0.22], np.float32) + o['bloom'] * blm
        # grade: S-curve, lifted blacks, warm highlights
        x = np.clip(x, 0, 1)
        x = x + o['contrast'] * (x - x * x) * (2 * x - 1) * 2
        x = o['lift'] + x * (1 - o['lift'])
        x = x + o['warmth'] * x * x * np.array([1.0, 0.35, -0.6], np.float32)
        # paper, vignette, grain
        x = x * self.paper * self.vig
        r = np.random.default_rng(frame_index * 7 + 3)
        g = r.standard_normal((self.H // 2, self.W // 2)).astype(np.float32)
        g = zoom(g, 2, order=0)[:self.H, :self.W]
        mid = 4 * x.mean(-1) * (1 - x.mean(-1))
        x = x + o['grain'] * g[..., None] * (0.35 + 0.65 * mid[..., None])
        return np.clip(x, 0, 1)


PRESETS = {
    # dark scenes lit from within: halation only where it's genuinely bright, keep the colour
    'night': dict(paper=0.04, grain=0.03, vignette=0.26, halation=0.45, bloom=0.12, lift=0.015, warmth=0.03,
                  contrast=0.06),
    # pale paper/parchment scenes: no halation (it blows out the paper), more texture, gentle grade
    'paper': dict(paper=0.07, grain=0.022, vignette=0.2, halation=0.0, bloom=0.03, lift=0.0, warmth=0.02,
                  contrast=0.05),
    # daylight / mid-tone scenes
    'day': dict(paper=0.05, grain=0.028, vignette=0.24, halation=0.2, bloom=0.08, lift=0.02, warmth=0.04,
                contrast=0.08),
}


def finisher(preset, W=1920, H=1080, seed=7):
    return Finisher(W, H, seed=seed, **PRESETS[preset])


def finish_u8(finisher, img_u8, frame_index=0):
    out = finisher(img_u8.astype(np.float32) / 255, frame_index)
    return (out * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ review and verification
def contact_sheet(frames, path, cols=4, tile_w=480):
    ims = [Image.fromarray(f) if not isinstance(f, Image.Image) else f for f in frames]
    th = int(tile_w * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tile_w, rows * th))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tile_w, th)), ((i % cols) * tile_w, (i // cols) * th))
    sheet.save(path)


def verify_sync(event_times, grid_times, fps=30, tol_frames=1.0):
    """Every event should land within tol_frames of a grid time (beat/onset). Returns list of misses."""
    grid = np.asarray(grid_times)
    misses = []
    for e in event_times:
        d = np.min(np.abs(grid - e)) * fps
        if d > tol_frames:
            misses.append((e, d))
    return misses
