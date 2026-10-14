"""Contact sheet of stills: python spot.py OUT.png t1 t2 ..."""
import sys
import time

from PIL import Image

import scene

ts = [float(a) for a in sys.argv[2:]]
tiles = []
for t in ts:
    t0 = time.time()
    tiles.append(Image.fromarray(scene.draw_frame(t)).resize((640, 360)))
    print(t, f'{time.time() - t0:.2f}s')
rows = (len(tiles) + 1) // 2
sheet = Image.new('RGB', (1280, 360 * rows))
for i, tl in enumerate(tiles):
    sheet.paste(tl, ((i % 2) * 640, (i // 2) * 360))
sheet.save(sys.argv[1])
