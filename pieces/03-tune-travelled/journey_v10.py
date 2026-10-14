"""The Tune That Travelled: visuals.

One long sideways journey. World x advances with time; the pen that draws the thread
(the melody's contour: time = x, pitch = height) sits at the centre of the screen, so
everything left of centre has been sung and everything right is still to come.
Each keeper's scene is a pre-rendered background strip in its own style.

usage: python journey.py OUT.mp4 [t0 t1]
"""
import json
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import scenes
import scenes_mid

W, H, FPS = 1920, 1080, 30
LEAD = 0.03
PEN_X = W // 2
TL = json.load(open('timeline.json'))
SCENES = TL['scenes']
NOTES = TL['notes']

# pan speed per scene (px/s): faster music, faster travel
SPEED = dict(shepherd=150, monks=140, sailors=200, musicbox=210, parlour=170, radio=220, phone=320, kitchen=55,
             child=110)


def _speed_track():
    ts = np.arange(0, TL['total'] + 5, 1 / FPS)
    sp = np.full_like(ts, 150.0)
    for s in SCENES:
        sp[(ts >= s['t0'] - 0.5)] = SPEED[s['name']]
    k = int(1.5 * FPS)                                       # ease speed changes over 1.5 s
    sp = np.convolve(np.pad(sp, k, mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
    x = np.cumsum(sp) / FPS
    return ts, x


TS, XS = _speed_track()


def world_x(t):
    return float(np.interp(t, TS, XS))


# scene boundaries in world x (midpoints of the gaps between scenes)
def scene_ranges():
    out = []
    for i, s in enumerate(SCENES):
        a = world_x(s['t0']) - (0 if i else 2000)
        b = world_x(s['t1'])
        out.append((s['name'], a, b))
    rng = []
    for i, (n, a, b) in enumerate(out):
        lo = (out[i - 1][2] + a) / 2 if i else a - 1200
        hi = (b + out[i + 1][1]) / 2 if i + 1 < len(out) else b + 3000
        rng.append((n, lo + PEN_X * 0, hi))
    return rng


RANGES = scene_ranges()
# v10: back to a dissolve between kitchen and bedroom (v9 tried a hard cut at a cut-away wall); no hard joins.
HARD = set()
PAD = dict(child=400)        # render the bedroom strip from before its range, so the dissolve shows the room, not a smear

# pitch -> screen y, per scene (each keeper's register is mapped to the same band)
F_LO, F_HI = {}, {}
for s in SCENES:
    fs = [n['f'] for n in NOTES if n['scene'] == s['name']]
    F_LO[s['name']], F_HI[s['name']] = min(fs), max(fs)


def pitch_y(f, scene):
    lo, hi = F_LO[scene], F_HI[scene]
    k = (np.log2(f) - np.log2(lo)) / max(np.log2(hi) - np.log2(lo), 0.5)
    return scenes.THREAD_Y[scene] - k * scenes.THREAD_SPAN[scene]


STRIPS = {}


def strip(name):
    if name not in STRIPS:
        (_, lo, hi) = next(r for r in RANGES if r[0] == name)
        lo -= PAD.get(name, 0)
        STRIPS[name] = (lo, scenes.render_strip(name, int(hi - lo) + W, H, lambda t, lo=lo: world_x(t) - lo))
    return STRIPS[name]


def background(cam_x):
    """Compose the visible part of the world from the scene strips, blending at the joins."""
    img = np.zeros((H, W, 3), np.float32)
    wsum = np.zeros((1, W, 1), np.float32)
    xs = cam_x + np.arange(W)
    BLEND = 700
    for (name, lo, hi) in RANGES:
        if hi + BLEND < cam_x or lo - BLEND > cam_x + W:
            continue
        s0, arr = strip(name)
        bl = 1.0 if (name, 'lo') in HARD else BLEND
        bh = 1.0 if (name, 'hi') in HARD else BLEND
        w = np.clip(np.minimum((xs - (lo - bl / 2)) / bl, ((hi + bh / 2) - xs) / bh), 0, 1)
        w = (w * w * (3 - 2 * w)).astype(np.float32)[None, :, None]
        cols = np.clip((xs - s0).astype(int), 0, arr.shape[1] - 1)
        img += arr[:, cols].astype(np.float32) / 255 * w
        wsum += w
    return img / np.maximum(wsum, 1e-6)


def frame(t):
    tv = t + LEAD
    cam = world_x(tv) - PEN_X
    img = background(cam)
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    # the thread: every sung note so far, drawn in its keeper's material
    by_scene = {}
    for n in NOTES:
        if n['t'] > tv:
            continue
        x0 = world_x(n['t']) - cam
        x1 = world_x(min(n['t'] + n['d'], tv)) - cam
        if x1 < -50 or x0 > W + 50:
            continue
        by_scene.setdefault(n['scene'], []).append((x0, x1, pitch_y(n['f'], n['scene']), n))
    for name, segs in by_scene.items():
        scenes.draw_thread(pil, name, segs, tv, cam)
    # the pen (a small warm light) at the current note
    cur = [n for n in NOTES if n['t'] <= tv < n['t'] + n['d']]
    if cur:
        n = cur[-1]
        y = pitch_y(n['f'], n['scene'])
        if n['scene'] == 'parlour':                     # the notes sit on the staff, so the pen must too
            y = scenes.THREAD_Y['parlour'] - (n['deg'] + 2) * scenes_mid.STAFF_STEP
        glow = Image.new('L', (W, H), 0)
        ImageDraw.Draw(glow).ellipse([PEN_X - 9, y - 9, PEN_X + 9, y + 9], fill=255)
        glow = glow.filter(ImageFilter.GaussianBlur(10))
        pil = Image.composite(Image.new('RGB', (W, H), scenes.PEN_COLOR[n['scene']]), pil, glow)
    return np.asarray(pil)


if __name__ == '__main__':
    out = sys.argv[1]
    t0, t1 = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (0, TL['total'])
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-threads', '2', '-pix_fmt', 'yuv420p', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(t0 * FPS), int(t1 * FPS)):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 300 == 0:
            print('frame', i, flush=True)
    p.stdin.close()
    p.wait()
