"""Preview one vignette as the film will frame it: python preview_vignette.py NAME OUT.png

Renders 8 moments (tl = -1 .. 7 s) at zoom 2.1 on the vignette, plus one wide shot, through the
same city + finishing pass the film uses, as a contact sheet.
"""
import sys

import numpy as np

sys.path.insert(0, '../..')
import craft  # noqa: E402
import city  # noqa: E402

name, out = sys.argv[1], sys.argv[2]
cx = city.VX[name]
fin = craft.Finisher(city.W, city.H, seed=21, paper=0.05, grain=0.028, vignette=0.32, halation=0.5, bloom=0.14,
                     lift=0.02, warmth=0.05, contrast=0.1)
frames = []
for i, tl in enumerate(np.linspace(-1, 7, 8)):
    tl2 = np.floor(tl * 12) / 12
    img = city.frame(cx - city.W / 2, 2.1, 0.0, [(name, tl2)])
    frames.append((fin(np.asarray(img).astype(np.float32) / 255, i) * 255).astype(np.uint8))
img = city.frame(cx - city.W / 2, 0.8, 0.0, [(name, 3.0)])
frames.append((fin(np.asarray(img).astype(np.float32) / 255, 99) * 255).astype(np.uint8))
craft.contact_sheet(frames, out, cols=3, tile_w=640)
print('wrote', out)
