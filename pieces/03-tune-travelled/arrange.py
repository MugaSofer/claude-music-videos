"""The whole soundtrack: nine keepers in a row, each handing over to the next.

Writes E:\\Claude\\music-video-2-work\\03\\tune.wav and timeline.json (scene start and
end times plus every melody note, for the visuals' thread).
"""
import json
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

import instruments as I
import realhum
import realwhistle
from tune import semis
from versions import build

sys.path.insert(0, '../02-player-piano')
from piano import note as piano_note  # noqa: E402

SR = I.SR
V = {v['name']: v for v in build()}

# (name, how many beats of its version to use, gap after in seconds)
PLAN = [('shepherd', 25, 1.0), ('monks', 24, 0.8), ('sailors', None, 0.6), ('musicbox', 31, 1.2),
        ('parlour', None, 1.0), ('radio', 32, 0.6), ('phone', None, 1.6), ('kitchen', None, 2.0),
        ('child', None, 3.0)]
INTRO = 3.0


def notes_of(v, t0, max_beats, rng):
    out, t, acc = [], t0, 0.0
    spb = 60 / v['bpm']
    for n in v['notes']:
        d, b = n[0], n[1]
        if max_beats and acc >= max_beats:
            break
        jitter = rng.normal(0, v['free']) * b * spb if v['free'] else 0
        sec = b * spb * (1 + (v['free'] * 1.5 if b >= 2 else 0))   # free rhythm lingers on long notes
        out.append(dict(t=t + jitter * 0.5, f=v['do'] * 2 ** (semis(d, v['scale']) / 12), d=sec, deg=d,
                        crew=len(n) > 2))
        t += sec + (jitter if v['free'] else 0)
        acc += b
    return out, t


def mono(evs, vel=0.9, only=None):
    return [(e['t'], e['f'], e['d'] * 0.95, vel) for e in evs if only is None or e['crew'] == only]


def place(buf, x, t0):
    i = int(t0 * SR)
    if i < 0:
        x, i = x[-i:], 0
    j = min(i + len(x), len(buf))
    buf[i:j] += x[:j - i]


def reverb(x, seconds, mix, seed=1):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (seconds * SR / 6.9))
    ir[:int(0.015 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(x)]
    return x * (1 - mix) + wet * mix * 2.5


def wind(n, rng):
    w = sosfilt(butter(2, [150, 900], 'bandpass', fs=SR, output='sos'), rng.standard_normal(n))
    gust = 0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / SR / 5.3) * np.sin(2 * np.pi * np.arange(n) / SR / 2.1)
    return w * gust * 0.05


PARLOUR_CHORDS = ['I', 'IV', 'I', 'V', 'I', 'vi', 'ii', 'V', 'I', 'vi', 'IV', 'I', 'IV', 'ii', 'V', 'I']
CHORD_DEG = {'I': [0, 2, 4], 'IV': [3, 5, 7], 'V': [4, 6, 8], 'vi': [5, 7, 9], 'ii': [1, 3, 5]}


def main():
    rng = np.random.default_rng(11)
    t = INTRO
    scenes, all_notes, stems = [], [], []
    for name, beats, gap in PLAN:
        v = V[name]
        evs, t_end = notes_of(v, t, beats, rng)
        scenes.append(dict(name=name, t0=t, t1=t_end))
        all_notes += [dict(e, scene=name) for e in evs]
        stems.append((name, evs, t, t_end))
        t = t_end + gap
    total = t + 1.0
    out = np.zeros(int(total * SR))

    for name, evs, t0, t1 in stems:
        T = t1 - t0 + 3
        rel = [dict(e, t=e['t'] - t0) for e in evs]
        n = int(T * SR)
        if name == 'shepherd':
            # v7: the shepherd hums (Muga's idea), so the piece opens and closes on a hummed tune.
            # An octave down puts him in the kitchen parent's register; a slightly deeper voice and another take.
            synth = I.whistle(mono(rel), T) * 0.8
            x = realhum.hum([(t_, f_ / float(os.environ.get('SHEP_DIV', '2')), d_, v_) for t_, f_, d_, v_ in mono(rel)], T,
                            formant=float(os.environ.get('SHEP_FORMANT', '0.94')), seed=2)
            x *= np.sqrt(np.mean(synth ** 2) / np.mean(x ** 2))  # at the old whistle's level, so the mix holds
            x = reverb(x, 1.4, 0.16) + wind(n, rng)[:len(x)]
            place(out, np.concatenate([wind(int(INTRO * SR), rng), np.zeros(0)]), 0)
        elif name == 'monks':
            x = reverb(I.organ(mono(rel), T, drone_hz=V['monks']['do'] / 2), 4.5, 0.4, seed=4) * 0.9
        elif name == 'sailors':
            spb = 60 / V['sailors']['bpm']
            x = I.concertina(mono(rel, only=False), T) + 0.8 * I.concertina(
                [(a, f / 2, d, v) for a, f, d, v in mono(rel, only=True)], T)
            x += I.stomp(np.arange(0, t1 - t0, 2 * spb), T)
            x = reverb(x, 0.8, 0.1)
        elif name == 'musicbox':
            x = I.music_box(mono(rel, 0.8), T, wind_down=((t1 - t0) * 0.65, t1 - t0))
            ticks = np.zeros(n); ticks[(np.arange(0, T, 0.125) * SR).astype(int)[:-1]] = 0.08
            x += sosfilt(butter(2, 3000, 'high', fs=SR, output='sos'), ticks)
            x = reverb(x, 0.9, 0.15)
        elif name == 'parlour':
            x = np.zeros(n)
            for e in rel:
                m = 67 + semis(e['deg'])
                y = piano_note(m, 0.72, min(e['d'] * 1.3, 3.5), metal=0.0)
                place(x, y * 0.9, e['t'])
            spb = 60 / V['parlour']['bpm']
            first = spb                                           # after the pickup
            for bar, ch in enumerate(PARLOUR_CHORDS):
                b0 = first + bar * 3 * spb
                place(x, piano_note(43 + semis(CHORD_DEG[ch][0]), 0.55, 1.2 * spb, 0.0) * 0.7, b0)
                for beat in (1, 2):
                    for dg in CHORD_DEG[ch]:
                        place(x, piano_note(55 + semis(dg), 0.38, 0.8 * spb, 0.0) * 0.45, b0 + beat * spb)
            x = reverb(x, 1.6, 0.18)
        elif name == 'radio':
            spb = 60 / V['radio']['bpm']
            x = I.brass(mono(rel), T)
            oom = [(b, V['radio']['do'] / 4 * (1.5 if (i % 2) else 1), spb * 0.5, 0.7)
                   for i, b in enumerate(np.arange(0, t1 - t0, spb))]
            x += 0.8 * I.brass(oom, T)
            x = I.radio(x) * 1.4
        elif name == 'phone':
            x = I.square(mono(rel), T) * 0.7
        elif name == 'kitchen':
            x = realhum.hum(mono(rel), T)                     # v5: a real recorded hum, re-pitched (realhum.py)
            x = reverb(x, 0.6, 0.12)
        elif name == 'child':
            x = realhum.hum([(t_, f_ / 2, d_, v_) for t_, f_, d_, v_ in mono(rel)], T, formant=1.18, seed=1)
            # v6: the same voice made smaller, an octave down (G5 was 17 semitones above the recording: it sounded synthetic)
            x = reverb(x, 0.6, 0.12)
        # short fades so each keeper hands over cleanly
        f = int(0.4 * SR)
        x[:f] *= np.linspace(0, 1, f)
        x[-int(1.5 * SR):] *= np.linspace(1, 0, int(1.5 * SR))
        peak = np.sqrt((x ** 2).mean()) + 1e-9
        target = {'shepherd': 0.1, 'monks': 0.11, 'sailors': 0.13, 'musicbox': 0.09, 'parlour': 0.13,
                  'radio': 0.11, 'phone': 0.08, 'kitchen': 0.11, 'child': 0.08}[name]
        place(out, x * target / peak, t0)

    out = np.tanh(out * 1.2) / 1.2
    out = out / np.abs(out).max() * 0.9
    wavfile.write(os.environ.get('TUNE_OUT', r'E:\Claude\music-video-2-work\03\tune_v7.wav'), SR, (out * 32767).astype(np.int16))
    json.dump(dict(total=total, scenes=scenes, notes=all_notes), open('timeline.json', 'w'))
    for s in scenes:
        print(f"{s['name']:9s} {s['t0']:6.1f} -> {s['t1']:6.1f}")
    print(f'total {total:.1f}s')


if __name__ == '__main__':
    main()
