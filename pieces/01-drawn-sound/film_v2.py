"""Everything Here Is Heard: the full film.

usage: python film.py OUT.mkv [start_bar end_bar] [--only LAYER ...]
Renders sequentially from bar 0 (voices need their phase history), but only
writes frames inside [start_bar, end_bar).
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from optical import W, H, FPS, SR, hex_rgb
from engine import (Curve, Voice, notes_curve, fill_between, soft_pulse, smooth_noise, hash_noise,
                    stamp_row, bird_stamp, dot_stamp, rect_stamp, silent_grain, X)

BEAT = 2 / 3            # 90 bpm
BAR = 4 * BEAT
B = lambda bars: bars * BAR
TOTAL_BARS = 68
HORIZON = 800

# ------------------------------------------------------------------ palette
MOODS = {
    'black':   dict(sky_top='#000000', sky_low='#000000', far='#000000', town='#000000', ground='#000000',
                    hills='#000000', bird='#000000', line='#000000'),
    'dawn':    dict(sky_top='#1d2347', sky_low='#eeac78', far='#8d7ea0', town='#3a2f4a', ground='#4a4658',
                    hills='#9aac80', bird='#2a2436', line='#fff0dc'),
    'morning': dict(sky_top='#5f93c8', sky_low='#f7e4c2', far='#a3b3cb', town='#46506e', ground='#7b976a',
                    hills='#afca84', bird='#262838', line='#fff0dc'),
    'storm':   dict(sky_top='#2c3236', sky_low='#6b7674', far='#4a5250', town='#22282a', ground='#3a473e',
                    hills='#7a8f6c', bird='#16181a', line='#fff0dc'),
    'clear':   dict(sky_top='#1d2768', sky_low='#86f0da', far='#6b60aa', town='#2a1f4f', ground='#352a63',
                    hills='#62d4b2', bird='#fff6d4', line='#fff0dc'),
    'night':   dict(sky_top='#04050d', sky_low='#1a2240', far='#1c2137', town='#0b0c17', ground='#0f131e',
                    hills='#34496a', bird='#fff6d4', line='#fff0dc'),
}
MOOD_KEYS = [(0, 'black'), (5.5, 'black'), (10, 'dawn'), (15, 'dawn'), (18, 'morning'), (31, 'morning'),
             (35, 'storm'), (43, 'storm'), (46, 'clear'), (51, 'clear'), (55, 'night'), (64, 'night'),
             (67, 'black'), (68, 'black')]


def palette(t):
    tb = t / BAR
    for (b0, m0), (b1, m1) in zip(MOOD_KEYS, MOOD_KEYS[1:]):
        if b0 <= tb <= b1:
            w = 0 if b1 == b0 else (tb - b0) / (b1 - b0)
            w = w * w * (3 - 2 * w)
            return {k: hex_rgb(MOODS[m0][k]) * (1 - w) + hex_rgb(MOODS[m1][k]) * w for k in MOODS[m0]}
    return {k: hex_rgb(v) for k, v in MOODS['black'].items()}


# ------------------------------------------------------------------ harmony
def chord_curve(chords, glide=0.35):
    """chords: [(bar, value)] held until next, gliding over `glide` seconds."""
    keys, prev = [], None
    for bar, v in chords:
        t = B(bar)
        if prev is None:
            keys.append((t, v))
        else:
            keys += [(t, prev), (t + glide, v)]
        prev = v
    keys.append((B(TOTAL_BARS) + 10, prev))
    return Curve(keys)


# hills / intro line: harmonic number
HILL_K = chord_curve([(0, 1), (2, 2), (3, 3), (4, 4), (5, 6), (6, 8), (7.5, 4),
                      (16, 4), (18, 5), (20, 6), (22, 4), (24, 4), (26, 5), (28, 6), (30, 4),
                      (32, 7), (44, 7), (45, 5), (52, 5), (54, 4), (68, 4)])
# town components (three rows of buildings)
TOWN = [chord_curve([(0, 8), (18, 10), (20, 9), (22, 8), (26, 10), (28, 9), (30, 8), (32, 7), (45, 10), (54, 8)]),
        chord_curve([(0, 10), (18, 12), (20, 12), (22, 10), (26, 12), (28, 12), (30, 10), (32, 14), (45, 15), (54, 12)]),
        chord_curve([(0, 12), (18, 15), (20, 15), (22, 12), (26, 15), (28, 15), (30, 12), (32, 21), (45, 20), (54, 16)])]
FAR_K = chord_curve([(0, 6)])

# birds' melody
MEL = [(12, 4),                                                       # bar 17
       (15, 2), (12, 2), (10, 1), (12, 1), (15, 2),                   # Bm 18
       (18, 2), (15, 1), (12, 1), (15, 4),                            # D 20
       (16, 3), (15, 1), (12, 2), (10, 2),                            # G 22
       (12, 2), (12, 1), (15, 1), (16, 2), (15, 1), (12, 1),          # G 24
       (10, 3), (12, 1), (15, 4),                                     # Bm 26
       (12, 1), (15, 1), (18, 2), (15, 2), (12, 2),                   # D 28
       (10, 2), (9, 1), (10, 1), (8, 4),                              # G 30
       (14, 4), (12, 2), (14, 2), (16, 8)]                            # storm 32-36
BIRD_K, _ = notes_curve(MEL, B(17), BEAT)
MEL2 = [(15, 2), (20, 2), (25, 4), (20, 2), (25, 2), (20, 4), (15, 4), (20, 4)]  # B major 46-52
BIRD2_K, _ = notes_curve(MEL2, B(46), BEAT)
FIRE = [(8, 4), (10, 4), (12, 8), (10, 4), (9, 4), (8, 8)]                     # night 54-62
FIRE_K, _ = notes_curve(FIRE, B(54), BEAT, glide=0.2)

# wind: drift in px/frame (motion = detune)
WIND = Curve([(0, 0), (B(33), 0), (B(35), 1), (B(43), 1), (B(46), 0), (B(70), 0)])


def wind_px(t):
    return WIND(t) * (14 * np.sin(2 * np.pi * t / 3.1) + 7 * np.sin(2 * np.pi * t / 1.3))


# ------------------------------------------------------------------ amplitudes
LINE_A = Curve([(0, 0), (B(1), 0), (B(1.6), 1), (B(7.5), 1), (B(9.5), 0), (B(70), 0)])   # intro lines
HILL_A = Curve([(0, 0), (B(7.5), 0), (B(9.5), 85), (B(16), 85), (B(18), 70), (B(32), 70), (B(34), 120), (B(44), 120), (B(46), 150),
                (B(52), 150), (B(55), 90), (B(62), 90), (B(66), 0), (B(70), 0)])
TOWN_A = Curve([(0, 0), (B(15.5), 0), (B(18), 1), (B(62), 1), (B(65), 0), (B(70), 0)])
FAR_A = Curve([(0, 0), (B(9), 0), (B(12), 1), (B(44), 1), (B(45), 0), (B(53), 0), (B(56), 0.6), (B(62), 0.6),
               (B(64), 0), (B(70), 0)])
BIRD_A = Curve([(0, 0), (B(16.8), 0), (B(17.5), 1), (B(34), 1), (B(36), 0), (B(45.8), 0), (B(46.3), 1),
                (B(52), 1), (B(53), 0), (B(70), 0)])
FIRE_A = Curve([(0, 0), (B(53.8), 0), (B(54.3), 1), (B(61.5), 1), (B(62.5), 0), (B(70), 0)])
RAIN_N = Curve([(0, 0), (B(35), 0), (B(37), 150), (B(40), 420), (B(43), 320), (B(44.5), 0), (B(70), 0)])
WIN_A = Curve([(0, 0), (B(55), 0), (B(58), 1), (B(62), 1), (B(64.5), 0), (B(70), 0)])
STAR_A = Curve([(0, 0), (B(54), 0), (B(57), 1), (B(63), 1), (B(65.5), 0), (B(70), 0)])
END_LINE_A = Curve([(0, 0), (B(63), 0), (B(64), 1), (B(65.5), 1), (B(67), 0), (B(70), 0)])
TEXT_A = Curve([(0, 0), (B(65), 0), (B(65.5), 1), (B(67.2), 1), (B(67.9), 0), (B(70), 0)])
LIGHTNING = [B(38.5), B(41.25), B(42.5)]
SHAPE_SHARP = Curve([(0, 0), (B(32), 0), (B(34), 1), (B(44), 1), (B(46), 0), (B(70), 0)])


# ------------------------------------------------------------------ scene
class Film:
    def __init__(self, only=None):
        self.only = set(only) if only else None
        self.rng = np.random.default_rng(7)
        self.v_hill = Voice(HILL_K, detune=wind_px)
        self.v_town = [Voice(c) for c in TOWN]
        self.v_far = Voice(FAR_K)
        self.v_bird = Voice(BIRD_K, detune=lambda t: 1.6 * wind_px(t))
        self.v_bird2 = Voice(BIRD2_K)
        self.v_fire = Voice(FIRE_K)
        self.v_end = Voice(Curve([(0, 1)]))
        self.v_end.cyc = 0.5
        self.v_hill.cyc = 0.5
        self.v_win = [Voice(Curve([(0, k), (B(53), k)])) for k in (24, 30, 36)]
        self.v_star = [Voice(Curve([(0, k)])) for k in (40, 50, 60)]
        self.grain = silent_grain(self.rng, 0.010)
        self.text = self._text_mask('everything here is heard')
        Yf = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        self.sky_w = Yf ** 1.5

    def on(self, name):
        return self.only is None or name in self.only

    @staticmethod
    def _text_mask(s):
        im = Image.new('L', (W, H), 0)
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/georgiai.ttf', 54)
        except OSError:
            font = ImageFont.load_default()
        d = ImageDraw.Draw(im)
        bw = d.textlength(s, font=font)
        d.text(((W - bw) / 2, H / 2 - 40), s, fill=255, font=font)
        return np.asarray(im, np.float32) / 255

    def render(self, frame):
        t = frame / FPS
        tt = (frame * W + X) / SR          # per-column sample times
        p = palette(t)
        img = (p['sky_top'] * (1 - self.sky_w) + p['sky_low'] * self.sky_w)
        img = np.broadcast_to(img, (H, W, 3)).astype(np.float32).copy()

        # everything advances its phase every frame, drawn or not
        cyc_h, f_h = self.v_hill.frame(frame)
        town = [v.frame(frame) for v in self.v_town]
        cyc_far, _ = self.v_far.frame(frame)
        cyc_b, f_b = self.v_bird.frame(frame)
        cyc_b2, f_b2 = self.v_bird2.frame(frame)
        cyc_f, f_f = self.v_fire.frame(frame)
        cyc_e, f_e = self.v_end.frame(frame)
        wins = [v.frame(frame) for v in self.v_win]
        stars = [v.frame(frame) for v in self.v_star]

        # stars (high chord, twinkling)
        sa = STAR_A(t)
        if sa > 0 and self.on('stars'):
            for i, (c, f) in enumerate(stars):
                tw = sa * (0.55 + 0.45 * np.sin(2 * np.pi * (0.7 + 0.37 * i) * t + i))
                seed = 11 + i
                stamp_row(img, c, f, dot_stamp(1.6 + 0.5 * i),
                          lambda xc, s=seed: 40 + 460 * hash_noise(np.round(xc / 7), s), hex_rgb('#fff6e0'), tw)

        # far mountains: a quiet fifth
        fa = FAR_A(t)
        if fa > 0 and self.on('far'):
            u = cyc_far % 1.0
            g = 1 - np.abs(2 * u - 1)
            fill_between(img, HORIZON - 30 - fa * 110 * g ** 1.4, HORIZON, p['far'])

        # town: stacked building rows = a chord
        ta = TOWN_A(t)
        if self.on('town'):
            height = np.full(W, 38.0) * min(ta * 3, 1)
            if ta > 0:
                spec = [(0.42, 70), (0.26, 52), (0.18, 40)]
                for j, ((c, f), (wf, hgt)) in enumerate(zip(town, spec)):
                    grow = np.clip(ta * 3 - j * 0.6, 0, 1)
                    height += grow * hgt * soft_pulse(c % 1.0, 0.5, wf, 0.03)
            if height.max() > 0:
                fill_between(img, HORIZON - height, HORIZON + 1, p['town'])
            wa = WIN_A(t)
            if wa > 0:
                for i, (c, f) in enumerate(wins):
                    stamp_row(img, c, f, rect_stamp(9, 12),
                              lambda xc, s=i: HORIZON - 34 + 22 * hash_noise(np.round(xc / 5), 90 + s),
                              hex_rgb('#ffd27a'), wa * (0.8 + 0.2 * np.sin(t * (1 + i))))

        # ground
        fill_between(img, HORIZON, H, p['ground'])

        # hills (and the intro's vertical lines, which become the hills)
        la, ha = LINE_A(t), HILL_A(t)
        if self.on('hills'):
            u = cyc_h % 1.0
            sharp = SHAPE_SHARP(t)
            hill_g = 0.5 - 0.5 * np.cos(2 * np.pi * u)
            hill_g = hill_g * (1 - sharp) + sharp * (1 - np.abs(2 * u - 1)) ** 0.8
            if ha > 0:
                base = H - 60
                fill_between(img, base - ha * hill_g, H, p['hills'])
            if la > 0:
                period = SR / f_h
                width_px = 26
                line = np.exp(-(((((u + 0.5) % 1.0) - 0.5) * period) / width_px) ** 2)
                fill_between(img, H - 60 - 150 * la, H - 60, hex_rgb('#fff0dc'), alpha=0.4 * la * line)

        # rain: fresh random streaks every frame = noise
        n = int(RAIN_N(t))
        if n > 0 and self.on('rain'):
            xs = self.rng.integers(0, W, n)
            top = np.full(W, H + 1.0)
            bot = np.zeros(W)
            y0 = self.rng.uniform(-100, H, n)
            ln = self.rng.uniform(60, 220, n)
            top[xs], bot[xs] = y0, y0 + ln
            fill_between(img, top, bot, hex_rgb('#c8d4dc'), alpha=0.45)

        # lightning: a jagged bright bolt for a few frames = a crack
        for lt in LIGHTNING:
            age = t - lt
            if 0 <= age < 4 / FPS and self.on('rain'):
                rng = np.random.default_rng(int(lt * 100))
                ys = np.arange(0, HORIZON)
                xs = 400 + 1100 * rng.random() + np.cumsum(rng.normal(0, 3.2, len(ys)))
                bright = 1 - age * FPS / 4
                for dx in range(-3, 4):
                    xi = np.clip((xs + dx).astype(int), 0, W - 1)
                    img[ys, xi] = img[ys, xi] * (1 - bright) + bright * hex_rgb('#f4f7ff')
                img += 0.12 * bright  # the sky flash is uniform, so it is silent

        # birds: their count is the melody
        ba = BIRD_A(t)
        flap = 0.5 + 0.5 * np.sin(2 * np.pi * 2.2 * t)
        bird_y = lambda xc: 190 + 70 * smooth_noise(xc, 3, 260) + 25 * np.sin(t * 0.9 + xc / 300)
        if ba > 0 and self.on('birds'):
            if t < B(40):
                stamp_row(img, cyc_b, f_b, bird_stamp(76, 44, flap), bird_y, p['bird'], ba)
            else:
                stamp_row(img, cyc_b2, f_b2, bird_stamp(64, 40, flap), bird_y, p['bird'], ba)

        # fireflies at night carry the last tune
        fa2 = FIRE_A(t)
        if fa2 > 0 and self.on('fire'):
            blink = 0.75 + 0.25 * np.sin(2 * np.pi * 1.7 * t)
            stamp_row(img, cyc_f, f_f, dot_stamp(9, 3.0),
                      lambda xc: 720 + 150 * smooth_noise(xc, 5, 150) + 12 * np.sin(t * 1.3 + xc / 90),
                      hex_rgb('#e4ff9a'), fa2 * blink)

        # coda: one line again, then words (which buzz, because they're pictures)
        ea = END_LINE_A(t)
        if ea > 0 and self.on('end'):
            u = cyc_e % 1.0
            line = np.exp(-((((u + 0.5) % 1.0) - 0.5) * W / 22) ** 2)
            fill_between(img, H - 60 - 190 * ea, H - 60, hex_rgb('#fff0dc'), alpha=0.55 * ea * line)
        xa = TEXT_A(t)
        if xa > 0 and self.on('end'):
            a = self.text[..., None] * xa
            img = img * (1 - a) + a * hex_rgb('#fff0dc')

        img += self.grain[..., None]
        return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    args = [a for a in sys.argv[1:]]
    only = None
    if '--only' in args:
        i = args.index('--only')
        only = args[i + 1:]
        args = args[:i]
    out = args[0]
    b0, b1 = (float(args[1]), float(args[2])) if len(args) >= 3 else (0, TOTAL_BARS)
    f0, f1 = int(round(B(b0) * FPS)), int(round(B(b1) * FPS))
    film = Film(only)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-c:v', 'ffv1', '-level', '3', '-threads', '2', '-pix_fmt', 'rgb24', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in range(f1):
        if fr < f0:
            film.render_phases_only(fr)
            continue
        p.stdin.write(film.render(fr).tobytes())
        if fr % 240 == 0:
            print(f'frame {fr}/{f1}', flush=True)
    p.stdin.close()
    p.wait()


def _phases_only(self, frame):
    self.v_hill.frame(frame)
    for v in self.v_town + [self.v_far, self.v_bird, self.v_bird2, self.v_fire, self.v_end] + self.v_win + self.v_star:
        v.frame(frame)


Film.render_phases_only = _phases_only

if __name__ == '__main__':
    main()
