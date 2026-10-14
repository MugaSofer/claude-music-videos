"""Small Hours: the film, bound to the analysed song (sections.json + beats).

usage: python film.py SECTIONS.json OUT.mp4 [t0 t1]
"""
import json
import subprocess
import sys

import numpy as np

sys.path.insert(0, '../..')
import craft  # noqa: E402
import city  # noqa: E402

W, H, FPS = city.W, city.H, 24
LEAD = 0.3                                   # pushes begin a little before the sung line

S = json.load(open(sys.argv[1]))
BEATS = np.array(S['beats'])
DOWN = np.array(S['downbeats'])
SECT = S['sections']                          # [{kind, t0, t1, vignettes:[...]}]
TOTAL = S['total']

# ------------------------------------------------------------------ camera keys from the structure
VX = city.VX
# how each vignette wants to be framed: (x offset, world y at screen centre, zoom at the end of its push)
FRAMING = dict(baker=(0, 540, 2.1), bus=(0, 635, 2.0), nurse=(0, 560, 2.2), fox=(0, 730, 2.2),
               lorry=(0, 540, 2.1), dad=(0, 540, 2.1), lines=(0, 800, 2.1), tower=(60, 560, 3.0))
LEVEL = 540
KEYS = [(0.0, 1500, LEVEL, 0.72)]            # (time, world x at screen centre, world y at centre, zoom)
for s in SECT:
    k = s['kind']
    if k in ('verse', 'bridge'):
        vs = s['vignettes']
        span = (s['t1'] - s['t0']) / len(vs)
        for i, v in enumerate(vs):
            ox, cy, zf = FRAMING[v]
            t = s['t0'] + i * span - LEAD
            KEYS.append((t, VX[v] + ox, (cy + LEVEL) / 2, 1.1))
            KEYS.append((t + 1.2, VX[v] + ox, cy, zf * 0.93))
            KEYS.append((t + span - 0.8, VX[v] + ox + 50, cy, zf))
    elif k in ('chorus', 'final'):
        # the city breathing: a level, slow pan across the rooftops at ~1x, filling the frame
        x0 = 2600 if s['t0'] < 60 else (5400 if k == 'chorus' else 1800)
        KEYS.append((s['t0'] - LEAD, KEYS[-1][1], KEYS[-1][2], 1.25))
        KEYS.append((s['t0'] + 2.5, x0, 600, 1.0))
        KEYS.append((s['t1'] - 2.0, x0 + (s['t1'] - s['t0']) * 70, 580, 0.95))
    elif k == 'outro':
        ox, cy, zf = FRAMING['dad']
        KEYS.append((s['t0'] - 1.0, VX['dad'] + ox, cy, 1.4))
        KEYS.append((s['t0'] + 2.5, VX['dad'] + ox, cy, 2.8))
KEYS.append((TOTAL + 2, KEYS[-1][1], KEYS[-1][2], KEYS[-1][3] * 1.05))
KEYS.sort()
KT = np.array([k[0] for k in KEYS])


def camera(t):
    i = int(np.clip(np.searchsorted(KT, t, side='right') - 1, 0, len(KEYS) - 2))
    a = craft.ease_in_out((t - KEYS[i][0]) / max(KEYS[i + 1][0] - KEYS[i][0], 1e-3))
    x, y, z = (np.array(KEYS[i][1:]) + (np.array(KEYS[i + 1][1:]) - np.array(KEYS[i][1:])) * a)
    dx, dy = craft.drift(t, seed=3, amp=18)
    bob = 1 + 0.004 * craft.pulse(t, DOWN, decay=0.25)
    return x + dx, y + dy * 0.5, z * bob


def section_at(t):
    for s in SECT:
        if s['t0'] - LEAD <= t < s['t1'] + 2:
            return s
    return None


def dawn_at(t):
    fin = next((s for s in SECT if s['kind'] == 'final'), None)
    if not fin:
        return 0.0
    return float(craft.ease_in_out((t - fin['t0']) / (TOTAL - fin['t0'])))


# ------------------------------------------------------------------ windows breathe with the song
def window_states(layer_seed, t):
    s = section_at(t)
    kind = s['kind'] if s else 'intro'
    density = dict(intro=0.12, verse=0.16, chorus=0.3, bridge=0.14, final=0.28, outro=0.05).get(kind, 0.12)
    dawn = dawn_at(t)
    density *= (1 - 0.85 * dawn)                         # at dawn the keepers finally sleep
    grid = BEATS if kind in ('chorus', 'final') else DOWN
    k = int(np.searchsorted(grid, t + 0.02))             # changes only on beats (or downbeats)

    def f(n):
        idx = np.arange(n)
        base = craft._hash(idx + layer_seed * 100000, 11) * 0.5 + 0.5          # each window's own threshold
        flick = craft._hash(idx * 31 + k * 977 + layer_seed, 5) * 0.5 + 0.5    # reshuffled on each beat
        lit = (base < density * 1.4) & (flick < 0.85) | (base < density * 0.6)
        return lit.astype(float)
    return f


# ------------------------------------------------------------------ vignettes active at time t
def active(t):
    out = []
    for s in SECT:
        if s['kind'] in ('verse', 'bridge'):
            vs = s['vignettes']
            span = (s['t1'] - s['t0']) / len(vs)
            for i, v in enumerate(vs):
                a = s['t0'] + i * span - LEAD - 2
                b = s['t0'] + (i + 1) * span + 3
                if a <= t <= b:
                    out.append((v, t - (s['t0'] + i * span - LEAD)))
    for v in ('baker', 'nurse', 'dad', 'tower'):          # indoor keepers carry on quietly in the background
        if all(v != o[0] for o in out):
            out.append((v, 3.0 + (t % 8.0)))
    return out


FIN = craft.Finisher(W, H, seed=21, paper=0.05, grain=0.028, vignette=0.32, halation=0.5, bloom=0.14, lift=0.02,
                     warmth=0.05, contrast=0.1)


def render(i):
    t = i / FPS
    t2 = np.floor(t * 12) / 12                            # figures animate on twos (12 drawings/s)
    x, y, z = camera(t)
    for L, seed in ((city.FAR, 1), (city.MID, 2), (city.NEAR, 3)):
        L.window_state = window_states(seed, t)
    img = city.frame(x - W / 2, z, dawn_at(t), [(v, np.floor(tl * 12) / 12) for v, tl in active(t2)], cam_y=y)
    arr = np.asarray(img).astype(np.float32) / 255
    fade = min(1.0, t / 2.0, max(0.0, (TOTAL - t) / 2.5))
    return (FIN(arr, i) * fade * 255 + 0.5).astype(np.uint8)


if __name__ == '__main__':
    out = sys.argv[2]
    t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0, TOTAL)
    if out.endswith('.png'):
        frames = [render(int(tt * FPS)) for tt in np.arange(t0, t1, 0.5)]
        craft.contact_sheet(frames, out, cols=6, tile_w=320)
        sys.exit()
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-threads', '2', '-pix_fmt', 'yuv420p', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(t0 * FPS), int(t1 * FPS)):
        p.stdin.write(render(i).tobytes())
        if i % 240 == 0:
            print('frame', i, flush=True)
    p.stdin.close()
    p.wait()
