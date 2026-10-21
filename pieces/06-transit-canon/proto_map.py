"""Transit Canon v2 on v1's map (stills). python proto_map.py OUT.png T [T ...]

v1's routes and look (parallel lanes, names, legend, glowing trains), with v2's score: each line is one statement of
the tune per lap, its 12 stops spaced by the tune's rhythm from Central. The whole network starts as pencil; a
phrase's stretch of track is inked, and its stations stamped, the first time the line sings it.
"""
import math
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import canon
import film as V1
from craft import clamp01

W, H, SS = V1.W, V1.H, V1.SS
PAPER, GHOST, INK, GRID = V1.PAPER, V1.GHOST, V1.INK, V1.GRID
TR = V1.TR
BEAT_AT = [0, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 14]
PHRASES = [canon.P1, canon.P2, canon.P3, canon.P4]
S_C = {n: T.L.st_s[T.L.stations.index(V1.CENTRAL)] for n, T in TR.items()}     # Central's arc on each route


def state(name, s):
    upb, octv, enter, laps = canon.LINES[name]
    lap_s = canon.LAP_U[name] * canon.U
    e = enter * canon.U
    if s < e:
        return False, 0, 0.0, set()
    x = s - e
    conv = canon.T_CONV_U * canon.U
    if s > conv:
        x -= min(s - conv, canon.DWELL_S)
    lap = int(x // lap_s)
    frac = (x % lap_s) / lap_s
    learned = set()
    for j in range(min(lap + 1, laps)):
        sung = canon.LEVELS[canon.LEARN[name][j]]
        for ph in PHRASES:
            if ph <= sung and (j < lap or frac >= BEAT_AT[min(ph)] / 16):
                learned |= ph
    if lap >= laps:
        learned = set(range(12))
    final = (enter + (laps + 1) * canon.LAP_U[name] + canon.DWELL_U) * canon.U
    return s <= final + 0.5, lap, frac, learned


def arc(name, f):
    T = TR[name]
    return S_C[name] + f * T.length


def frame(s, z=1.0, centre=(16 * GRID, 9 * GRID)):
    cx, cy = centre
    S = z * SS

    def P(p):
        return ((p[0] - cx) * S + W * SS / 2, (p[1] - cy) * S + H * SS / 2)

    im = Image.new("RGB", (W * SS, H * SS), PAPER)
    d = ImageDraw.Draw(im)
    glow = Image.new("RGB", (W * SS // 4, H * SS // 4), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    lw = max(2, int(V1.LW * S))
    for T in TR.values():                                       # the whole network in pencil, from the start
        d.line([P(p) for p in T.pv], fill=GHOST, width=max(1, int(3 * S)), joint="curve")
    st = {n: state(n, s) for n in TR}
    for n, T in TR.items():                                     # learned phrases in ink
        learned = st[n][3]
        for ph in PHRASES:
            if ph <= learned:
                f0 = BEAT_AT[min(ph)] / 16
                f1 = (BEAT_AT[max(ph)] + canon.RHYTHM[max(ph)]) / 16
                pts = T.sub(arc(n, f0), arc(n, f1))
                d.line([P(p) for p in pts], fill=INK[n], width=lw, joint="curve")
    font = ImageFont.truetype(V1.FONT, max(8, int(15 * S)))
    k_name = 0
    for n, T in TR.items():                                     # stops: stamped when learned, pencil ticks before
        learned = st[n][3]
        for k, b in enumerate(BEAT_AT):
            if k == 0:
                continue
            x, y = P(T.at(arc(n, b / 16)))
            if k in learned:
                r = 7 * S
                d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=INK[n], width=max(1, int(3 * S)))
                d.text((x + 11 * S, y - 22 * S), V1.NAMES[(hash(n) % 7 + k * 3) % len(V1.NAMES)], font=font,
                       fill=(90, 86, 80))
            else:
                r = 4 * S
                d.ellipse([x - r, y - r, x + r, y + r], outline=GHOST, width=max(1, int(2 * S)))
    x, y = P((V1.CENTRAL[0] * GRID, V1.CENTRAL[1] * GRID))
    r = 20 * S
    d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 246, 236), outline=(40, 38, 44), width=max(2, int(5 * S)))
    d.text((x + 26 * S, y - 40 * S), "CENTRAL", font=ImageFont.truetype(V1.FONT, max(8, int(19 * S))), fill=(40, 38, 36))
    for n, T in TR.items():                                     # trains
        present, lap, frac, learned = st[n]
        if not present:
            continue
        sa_ = arc(n, frac)
        p, back = T.at(sa_), T.at(sa_ - 0.35)
        gx, gy = P(p)
        gd.ellipse([gx / 4 - 4 * S, gy / 4 - 4 * S, gx / 4 + 4 * S, gy / 4 + 4 * S], fill=(90, 70, 30))
        x, y = P(p)
        bx, by = P(back)
        ang = math.atan2(y - by, x - bx)
        ca, sa = math.cos(ang), math.sin(ang)

        def box(ln, wd):
            return [(x + ca * ln / 2 - sa * wd, y + sa * ln / 2 + ca * wd), (x + ca * ln / 2 + sa * wd, y + sa * ln / 2 - ca * wd),
                    (x - ca * ln / 2 + sa * wd, y - sa * ln / 2 - ca * wd), (x - ca * ln / 2 - sa * wd, y - sa * ln / 2 + ca * wd)]
        d.polygon(box(30 * S, 9 * S), fill=INK[n], outline=tuple(int(v * 0.55) for v in INK[n]))
        d.polygon(box(22 * S, 3.2 * S), fill=(255, 244, 205))
    # legend and title, as v1
    lf = ImageFont.truetype(V1.FONT, max(8, int(14 * S)))
    tf = ImageFont.truetype(V1.FONT, max(8, int(20 * S)))
    x0, y0 = P((0.45 * GRID, 14.7 * GRID))
    x1, y1 = P((4.9 * GRID, 17.55 * GRID))
    d.rectangle([x0, y0, x1, y1], outline=(60, 56, 50), width=max(1, int(2 * S)))
    d.text((x0 + 10 * S, y0 + 8 * S), "NIGHT NETWORK", font=tf, fill=(40, 38, 36))
    for k, n in enumerate(["teal", "rose", "amber", "violet"]):
        yy = y0 + (40 + 30 * k) * S
        d.line([(x0 + 12 * S, yy + 8 * S), (x0 + 52 * S, yy + 8 * S)], fill=INK[n], width=lw)
        d.text((x0 + 62 * S, yy), f"{n.title()} Line  ·  every {canon.LAP_U[n] * canon.U:.1f} s", font=lf, fill=(50, 48, 44))
    tx, ty = P((26.9 * GRID, 0.35 * GRID))
    d.text((tx, ty), "TRANSIT CANON", font=tf, fill=(40, 38, 36))
    d.text((tx, ty + 26 * S), "four loops, one song", font=lf, fill=(90, 86, 80))
    d.text((W * SS - 260 * SS, H * SS - 40 * SS), f"t={s:.0f}s", font=tf, fill=(150, 140, 130))
    glow = glow.filter(ImageFilter.GaussianBlur(3)).resize(im.size, Image.BILINEAR)
    return ImageChops.add(im, glow).resize((W, H), Image.LANCZOS)


if __name__ == "__main__":
    out = sys.argv[1]
    ts = [float(x) for x in sys.argv[2:]]
    ims = [frame(t) for t in ts]
    cols, tw, th = 3, 640, 360
    sheet = Image.new("RGB", (tw * cols, th * math.ceil(len(ims) / cols)), (255, 255, 255))
    for k, im in enumerate(ims):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
    sheet.save(out)
    for k, im in enumerate(ims):
        im.save(out.replace(".png", f"_{ts[k]:.0f}.png"))
