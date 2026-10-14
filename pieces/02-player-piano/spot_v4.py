"""Stills of the v4 look: city → camera lean → rain on glass → night finish."""
import sys

import numpy as np

sys.path.insert(0, '../..')
import craft  # noqa: E402
import city  # noqa: E402
import glass  # noqa: E402

FIN = craft.finisher('night')
FOCUS = (1450, 600)
frames = []
for t in [float(a) for a in sys.argv[2:]]:
    img = city.frame(t)
    z, fx, fy = glass.camera(t, city.INFO['t_conv'], city.INFO['total'], FOCUS)
    img = glass.apply_camera(img, z, fx, fy)
    frames.append(craft.finish_u8(FIN, img, int(t * 30)))
craft.contact_sheet(frames, sys.argv[1], cols=2, tile_w=960)
print('ok')
