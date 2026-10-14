"""Before/after stills of the finishing pass on existing pieces, with a preset per look."""
import subprocess

import numpy as np
from PIL import Image

from craft import finisher, finish_u8

SRC = [('E:/Claude/music-video-2-work/02/city_v3.mp4', 104.5, 'night'),
       ('E:/Claude/music-video-2-work/03/journey_v3.mp4', 30, 'paper'),
       ('E:/Claude/music-video-2-work/03/journey_v3.mp4', 150, 'night'),
       ('E:/Claude/music-video-2-work/04/maint_v2.mp4', 100, 'day')]


def grab(path, t):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', path, '-frames:v', '1', '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3)


tiles = []
for path, t, preset in SRC:
    a = grab(path, t)
    b = finish_u8(finisher(preset), a, int(t * 30))
    tiles += [Image.fromarray(a).resize((800, 450)), Image.fromarray(b).resize((800, 450))]
sheet = Image.new('RGB', (1600, 450 * len(SRC)))
for i, tl in enumerate(tiles):
    sheet.paste(tl, ((i % 2) * 800, (i // 2) * 450))
sheet.save('E:/Claude/music-video-2-work/before_after2.png')
print('ok')
