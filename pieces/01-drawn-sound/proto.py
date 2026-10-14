"""10-second prototype: sky, city, hills, birds. Writes a lossless FFV1 video."""
import subprocess
import sys

import numpy as np

from optical import W, H, FPS, SR, TWO_PI, Voice, fill_below, stamp_row, silent_grain, hex_rgb

OUT = sys.argv[1] if len(sys.argv) > 1 else r'E:\Claude\music-video-2-work\01\proto.mkv'
SECONDS = 10
rng = np.random.default_rng(1)

# --- palette
SKY_TOP, SKY_LOW = hex_rgb('#1b2140'), hex_rgb('#e0a27a')
CITY = hex_rgb('#2a2238')
GROUND = hex_rgb('#3b3a4a')
HILLS = hex_rgb('#6d7f6a')
BIRD = hex_rgb('#fff2dc')


def steps(notes, dur, glide=0.1, base=24.0):
    """Frequency function: a list of harmonic numbers, each held `dur` seconds."""
    notes = np.asarray(notes, dtype=float)

    def f(t):
        i = np.clip((t // dur).astype(int), 0, len(notes) - 1)
        prev = notes[np.maximum(i - 1, 0)]
        into = t - i * dur
        w = np.clip(into / glide, 0, 1)
        w = w * w * (3 - 2 * w)
        return base * (prev + (notes[i] - prev) * w)
    return f


def bird_stamp(w=110, h=64, flap=0.0):
    x = np.linspace(-1, 1, w)[None, :]
    y = np.linspace(-1, 1, h)[:, None]
    wing_y = -0.1 + (0.55 - 0.9 * flap) * np.abs(x) ** 1.3
    wing = np.exp(-((y - wing_y) / 0.22) ** 2) * (np.abs(x) < 0.98)
    body = np.exp(-(x / 0.3) ** 2 - ((y - 0.05) / 0.4) ** 2)
    return np.clip(wing * (1 - np.abs(x) ** 3) + body, 0, 1).astype(np.float32)


sky = np.linspace(0, 1, H, dtype=np.float32)[:, None] ** 1.6
sky_img = (SKY_TOP[None, None] * (1 - sky[..., None]) + SKY_LOW[None, None] * sky[..., None])
sky_img = np.broadcast_to(sky_img, (H, W, 3)).copy()
grain = silent_grain(rng, 0.012)

birds = Voice(steps([10, 12, 9, 8, 10, 12, 15, 16], 1.25))
city = Voice(lambda t: np.full_like(t, 24 * 6))
hills = Voice(lambda t: np.full_like(t, 24 * 4))


def skyline(ph):
    """A cluster of three towers per period: a stepped, square-ish waveform."""
    u = (ph / TWO_PI) % 1.0
    h = np.where(u < 0.18, 150, np.where(u < 0.30, 95, np.where(u < 0.46, 125, np.where(u < 0.55, 40, 20))))
    return h.astype(np.float32)


def render(frame):
    img = sky_img.copy()
    t = frame / FPS
    ph_c, _ = city.frame_phase(frame)
    fill_below(img, 800 - skyline(ph_c), 800, CITY)
    fill_below(img, np.full(W, 800, np.float32), H, GROUND)
    ph_h, _ = hills.frame_phase(frame)
    fill_below(img, 900 - 70 * np.sin(ph_h), H, HILLS)
    ph_b, fb = birds.frame_phase(frame)
    flap = 0.5 + 0.5 * np.sin(TWO_PI * 3 * t)
    stamp_row(img, ph_b, fb, bird_stamp(flap=flap), 230, BIRD)
    img += grain[..., None]
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'ffv1', '-level', '3', '-threads', '2', '-pix_fmt', 'rgb24', OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in range(SECONDS * FPS):
        p.stdin.write(render(fr).tobytes())
    p.stdin.close()
    p.wait()
    print('wrote', OUT)
