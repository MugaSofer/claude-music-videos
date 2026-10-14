"""Stills: python spot.py OUT.png t1 t2 ..."""
import sys

from PIL import Image

import journey

ts = [float(a) for a in sys.argv[2:]]
tiles = [Image.fromarray(journey.frame(t)).resize((640, 360)) for t in ts]
rows = (len(tiles) + 1) // 2
sheet = Image.new('RGB', (1280, 360 * rows))
for i, tl in enumerate(tiles):
    sheet.paste(tl, ((i % 2) * 640, (i // 2) * 360))
sheet.save(sys.argv[1])
