"""Vignette painters for Small Hours. One module per keeper of the night.

API (each module, e.g. vignettes/baker.py):

    def set_items(cx, ground):
        '''The static set: the building/room/place. Always drawn, even when the vignette is not active.'''
        return [items...]

    def action_items(tl, cx, ground):
        '''The living part (people, animals, vehicles, steam, light). tl = local seconds since the
        vignette's line began (may be negative a little before, and run ~8 s). Called on twos.'''
        return [items...]

Items are world-space shapes, drawn in list order (later = on top):
    ('poly', [(x, y), ...], (r, g, b) or (r, g, b, a))
    ('ell',  (x0, y0, x1, y1), colour)
World: y grows downward; the pavement top is `ground` (880); the road runs from 880 to ~1080.
Each vignette owns roughly cx-330 .. cx+330 horizontally and y 180 .. 1000.
The camera frames the vignette at zoom ~2.1 (so ~900 x 510 world px fills the screen).
"""
import importlib

NAMES = ['baker', 'bus', 'nurse', 'fox', 'lorry', 'dad', 'lines', 'tower']


def load(name):
    try:
        return importlib.import_module(f'vignettes.{name}')
    except ModuleNotFoundError:
        return None
