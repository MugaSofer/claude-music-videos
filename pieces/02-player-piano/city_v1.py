"""Player Piano City: visuals.

Four translucent copies of the same piano roll (one per canon voice) scroll upward
at speeds proportional to their tempi. In subject-beat coordinates each layer is the
same drawing, offset by how far that voice has got, so at the convergence instant all
four coincide exactly and their colours add up to white.

x = pitch (degree within the voice's octave span; each octave is one building),
y = subject beat. Windows below the reading line are unlit punched holes; they flash
as they cross it (the note sounds) and keep a slowly fading afterglow above it.

usage: python city.py OUT.mkv [t0 t1]
"""
import json
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, zoom

W, H, FPS = 1920, 1080, 30
LEAD = 0.03                       # picture ~30 ms ahead of the sound (Muga's preference)
K = 64.0                          # px per subject beat
BAR_Y = 690                       # the reading line
AFTERGLOW = 12.0                   # seconds
MODE = [0, 2, 3, 5, 7, 9, 10]
ROOTS = [38, 50, 62, 74]
COLS = np.array([[1.00, 0.52, 0.16],   # voice 0 (bass, slowest): amber
                 [0.20, 0.85, 0.62],   # voice 1: jade
                 [0.35, 0.40, 1.00],   # voice 2: cobalt
                 [1.00, 0.36, 0.62]],  # voice 3 (fastest): rose
                dtype=np.float32)
COLS *= (np.array([1, 1, 1]) / COLS.sum(0))[None, :] * 1.0   # the four sum to white

E = json.load(open('events.json'))
INFO = E['info']
RATES, STARTS = INFO['rates'], INFO['starts']
NOTES = [e for e in E['events'] if e['voice'] < 4]
SWEEP = [e for e in E['events'] if e['voice'] == 4]


def degree_of(e):
    semi = e['m'] - ROOTS[e['voice']]
    o, r = divmod(semi, 12)
    return 7 * o + MODE.index(r)


DEG = np.array([degree_of(e) for e in NOTES])
BEAT = np.array([e['beat'] for e in NOTES])
DUR_B = np.array([e['d'] / 0.92 * RATES[e['voice']] for e in NOTES])   # duration back in beats
VOICE = np.array([e['voice'] for e in NOTES])
TSTART = np.array([e['t'] for e in NOTES])
VEL = np.array([e['v'] for e in NOTES])

# x layout: each octave of degrees is a building; small alleys between them
DMIN, DMAX = DEG.min(), DEG.max()
N_OCT = (DMAX - DMIN) // 7 + 1
COL_W, WIN_W, ALLEY = 62, 38, 70
BLD_W = 7 * COL_W
X0 = (W - (N_OCT * BLD_W + (N_OCT - 1) * ALLEY)) / 2


def x_of(deg):
    k = deg - DMIN
    o, r = k // 7, k % 7
    return X0 + o * (BLD_W + ALLEY) + r * COL_W + (COL_W - WIN_W) / 2


XS = np.array([x_of(d) for d in DEG])


def position(v, t):
    """Subject beat that voice v is reading at time t (may be <0 before entry)."""
    return RATES[v] * (t - STARTS[v])


def sky(t):
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top, low = np.array([0.012, 0.014, 0.035]), np.array([0.05, 0.045, 0.09])
    return np.broadcast_to(top * (1 - g) + low * g, (H, W, 3)).astype(np.float32).copy()


def _towers():
    """Static tower silhouettes (one per octave) with a faint grid of unlit window slots."""
    img = np.zeros((H, W, 3), np.float32)
    rng = np.random.default_rng(4)
    for o in range(N_OCT):
        x0 = int(X0 + o * (BLD_W + ALLEY) - 16)
        x1 = int(x0 + BLD_W + 32)
        top = int(rng.uniform(40, 160))
        img[top:, x0:x1] = np.array([0.055, 0.06, 0.10])
        img[top:top + 6, x0 - 6:x1 + 6] = np.array([0.08, 0.085, 0.13])     # cornice
        for c in range(7):
            xs = int(X0 + o * (BLD_W + ALLEY) + c * COL_W + (COL_W - WIN_W) / 2)
            for y in range(top + 24, H, 30):
                img[y:y + 16, xs:xs + WIN_W] = np.array([0.035, 0.038, 0.065])
    # distant skyline behind, very dark
    for i in range(40):
        x = int(rng.uniform(0, W)); w = int(rng.uniform(40, 140)); h = int(rng.uniform(250, 700))
        img[H - h:, max(x, 0):min(x + w, W)] = np.maximum(img[H - h:, max(x, 0):min(x + w, W)], np.array([0.03, 0.032, 0.06]))
    return img


TOWERS = None


def facades(img, t):
    global TOWERS
    if TOWERS is None:
        TOWERS = _towers()
    np.maximum(img, TOWERS, out=img)


def frame(t):
    tv = t + LEAD
    img = sky(t)
    facades(img, t)
    lit = np.zeros((H // 2, W // 2, 3), np.float32)      # glow buffer (half res)
    core = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(core)
    base = (img * 255).astype(np.uint8)
    core = Image.fromarray(base)
    d = ImageDraw.Draw(core, 'RGBA')
    bloom = float(np.exp(-(tv - INFO['t_conv']) / 0.6)) if tv >= INFO['t_conv'] else 0.0
    for v in range(4):
        p = position(v, tv)
        if p < -30:
            continue
        sel = VOICE == v
        y_top = BAR_Y + (BEAT[sel] - p) * K                # note start sits here
        y_bot = y_top + np.maximum(DUR_B[sel] * K - 6, 8)
        vis = (y_bot > -40) & (y_top < H + 40)
        if not vis.any():
            continue
        col = COLS[v]
        for yt, yb, x, b0, vel, ts in zip(y_top[vis], y_bot[vis], XS[sel][vis], BEAT[sel][vis], VEL[sel][vis],
                                          TSTART[sel][vis]):
            age = tv - ts
            if age < 0:            # upcoming: an unlit punched hole
                c = tuple(int(255 * (0.10 + 0.45 * cc)) for cc in col) + (150,)
                d.rectangle([x, yt, x + WIN_W, yb], outline=c, width=2)
                if bloom > 0.02:
                    d.rectangle([x, yt, x + WIN_W, yb], fill=(255, 250, 240, int(200 * bloom)))
                    y0, y1 = int(max(yt, 0) // 2), int(min(yb, H - 1) // 2) + 1
                    if y1 > y0:
                        lit[y0:y1, int(x // 2):int((x + WIN_W) // 2) + 1] += 0.5 * bloom
            else:                  # sounded: a flash, then afterglow
                flash = np.exp(-age / 0.18)
                glow = np.exp(-age / AFTERGLOW)
                bright = min(1.0, 0.5 + 0.5 * flash) * (0.5 + 0.5 * glow) * (0.7 + 0.4 * vel)
                c = tuple(int(255 * min(1, cc * bright * 1.6)) for cc in col) + (int(255 * min(1, 0.55 + 0.4 * flash)),)
                d.rectangle([x, yt, x + WIN_W, yb], fill=c)
                if flash > 0.02 or glow > 0.3:
                    y0, y1 = int(max(yt, 0) // 2), int(min(yb, H - 1) // 2) + 1
                    x0i, x1i = int(x // 2), int((x + WIN_W) // 2) + 1
                    if y1 > y0:
                        lit[y0:y1, x0i:x1i] += col * (1.6 * flash + 0.45 * glow + 2.5 * bloom) * vel
    out = np.asarray(core, np.float32) / 255
    # the Nancarrow sweep: a streak of light racing up the keyboard
    for e in SWEEP:
        age = tv - e['t']
        if 0 <= age < 0.6:
            x = W * (e['m'] - 38) / 52
            a = np.exp(-age / 0.12)
            lit[BAR_Y // 2 - 40:BAR_Y // 2 + 10, int(x // 2):int(x // 2) + 6] += np.array([1, 1, 1]) * a * 1.5
    glow = gaussian_filter(lit, sigma=(7, 7, 0)) + 0.5 * gaussian_filter(lit, sigma=(22, 22, 0))
    glow = zoom(glow, (2, 2, 1), order=1)[:H, :W]
    out += glow * 1.3
    # the reading line
    out[BAR_Y - 1:BAR_Y + 1] += 0.10
    out = 1 - np.exp(-out * 1.7)                          # gentle tone map so sums go to white, not clip
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    out = sys.argv[1]
    t0, t1 = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (0, INFO['total'] + 3)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-threads', '2', '-pix_fmt', 'yuv420p', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n0, n1 = int(t0 * FPS), int(t1 * FPS)
    for i in range(n0, n1):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 300 == 0:
            print('frame', i, '/', n1, flush=True)
    p.stdin.close()
    p.wait()
