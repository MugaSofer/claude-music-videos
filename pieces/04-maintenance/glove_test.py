import time
import numpy as np
from PIL import Image, ImageDraw
from growth import Growth, sample_mask

W, H = 960, 540
rng = np.random.default_rng(3)


def glove_mask(ox, oy, s=1.0):
    im = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([ox, oy, ox + 150 * s, oy + 120 * s], radius=int(30 * s), fill=255)      # palm
    for k, (L, a) in enumerate([(120, 0), (140, 0), (130, 0), (100, 0)]):
        fx = ox + (12 + k * 34) * s
        d.rounded_rectangle([fx, oy - L * s, fx + 28 * s, oy + 20 * s], radius=int(14 * s), fill=255)
    d.rounded_rectangle([ox - 60 * s, oy + 20 * s, ox + 10 * s, oy + 60 * s], radius=int(20 * s), fill=255)  # thumb
    d.rectangle([ox + 5 * s, oy + 120 * s, ox + 145 * s, oy + 190 * s], fill=255)                # cuff
    return np.asarray(im) > 0


real = glove_mask(250, 260)
replica = glove_mask(560, 260)
g = Growth(roots=[(480, 540), (700, 540)], attractors=np.vstack([
    sample_mask(replica, 900, rng), rng.uniform([420, 460], [820, 540], (60, 2))]), step=4, influence=80, kill=6)
t0 = time.time(); k = 0
while g.grow() and k < 400:
    k += 1
print(k, 'iterations', len(g.pos), 'nodes', f'{time.time() - t0:.1f}s')
im = Image.new('RGB', (W, H), (34, 38, 30))
d = ImageDraw.Draw(im)
rm = Image.fromarray((real * 255).astype(np.uint8))
im.paste((190, 170, 130), mask=rm)
th = g.thickness(0.6, 0.45)
for i, p in enumerate(g.parent):
    if p >= 0:
        a, b = g.pos[p], g.pos[i]
        d.line([tuple(a), tuple(b)], fill=(90, 150, 70), width=max(1, int(th[i])))
for i in range(0, len(g.pos), 3):
    x, y = g.pos[i]
    if th[i] < 1.2:
        d.ellipse([x - 3, y - 2, x + 3, y + 2], fill=(120, 180, 90))
im.save(r'E:\Claude\music-video-2-work\04\glove_test.png')
