"""Stills of each vignette: python spot.py OUT.png"""
import sys

from PIL import Image

import city

tiles = []
for name, x in city.VIGNETTES:
    im = city.frame(x - city.W / 2, 1.0, 0.0, [(name, 3.0)])
    tiles.append(im.resize((640, 360)))
wide = city.frame(4000, 0.6, 0.0, [(n, 3.0) for n, _ in city.VIGNETTES])
tiles.append(wide.resize((640, 360)))
dawn = city.frame(4000, 0.6, 0.8, [])
tiles.append(dawn.resize((640, 360)))
sheet = Image.new('RGB', (1280, 360 * 5))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 2) * 640, (i // 2) * 360))
sheet.save(sys.argv[1])
