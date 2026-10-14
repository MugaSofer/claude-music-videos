"""Quick layout check: draw the network at time t to a PNG. Usage: python spot.py OUT.png [t]"""
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from netmap import GRID, NET, interchanges

BG = (14, 18, 34)


def px(p):
    return (p[0] * GRID, p[1] * GRID)


def draw(t, out):
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    # faint grid
    for x in range(0, 1920, GRID):
        d.line([(x, 0), (x, 1080)], fill=(20, 26, 46))
    for y in range(0, 1080, GRID):
        d.line([(0, y), (1920, y)], fill=(20, 26, 46))
    for L in NET:
        d.line([px(p) for p in L.path], fill=L.colour, width=14, joint="curve")
    for L in NET:
        for s in L.stations:
            x, y = px(s)
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(240, 236, 224), outline=L.colour, width=3)
    for s in interchanges():
        x, y = px(s)
        d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(240, 236, 224), outline=(20, 20, 20), width=5)
    glow = Image.new("RGB", im.size, (0, 0, 0))
    g = ImageDraw.Draw(glow)
    for L in NET:
        x, y = px(L.pos(t))
        g.ellipse([x - 26, y - 26, x + 26, y + 26], fill=L.colour)
        d.ellipse([x - 11, y - 11, x + 11, y + 11], fill=(255, 255, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    im = ImageChops.add(im, glow)
    im.save(out)


if __name__ == "__main__":
    draw(float(sys.argv[2]) if len(sys.argv) > 2 else 100.0, sys.argv[1])
