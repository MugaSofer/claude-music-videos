"""A real whistle (v7): the shepherd's tune read out of a recorded human whistle.

Muga: "is the tune meant to be synth at the start?" The v6 whistle was a sine with metronomic vibrato.
Source: "Aimless whistle" by WalliumVA (Freesound 790711, CC0), HQ preview in research/whistle/.
A whistle is close to a pure tone with no formants, so re-pitching by varispeed (reading the recording
faster or slower) sounds natural. Each tune note reads a held note of the recording at rate
target/source, so the whistler's own wobble, breath and attack ride along. Glides happen inside the
outgoing note; the hand-over to the next held note is a short crossfade once both are at the same pitch.
"""
import subprocess

import numpy as np
from scipy.signal import butter, sosfilt

import instruments as I

SR = 48000
SRC = r"E:\Claude\music-video-2-research\whistle\790711_13530059-hq.mp3"
HOP = 240
_SEGS = None


def _load():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', SRC, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    return sosfilt(butter(2, 300, 'high', fs=SR, output='sos'), x)        # handling rumble out


def _track(x, n=4096):
    win = np.hanning(n)
    f, a = [], []
    lo, hi = int(400 * n / SR), int(3000 * n / SR)
    for i in range(0, len(x) - n, HOP):
        s = np.abs(np.fft.rfft(x[i:i + n] * win))
        k = lo + int(np.argmax(s[lo:hi]))
        y0, y1, y2 = np.log(s[k - 1:k + 2] + 1e-12)
        f.append((k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)) * SR / n)
        a.append(s[k])
    c = n // 2
    return np.array(f), np.array(a), c


def segments():
    """Held notes: >= 0.22 s where the pitch stays within 45 cents of the run's median."""
    global _SEGS
    if _SEGS is None:
        x = _load()
        f, a, c = _track(x)
        loud = a > np.percentile(a, 95) * 0.06
        f = np.nan_to_num(f, nan=1.0)
        segs, i = [], 0
        while i < len(f):
            if not loud[i]:
                i += 1
                continue
            j = i
            while (j + 1 < len(f) and loud[j + 1] and abs(1200 * np.log2(f[j + 1] / f[j])) < 30
                   and np.ptp(1200 * np.log2(f[i:j + 2])) < 110):
                j += 1
            if (j - i) * HOP / SR >= 0.15:
                a0, b0 = i * HOP + c - HOP, j * HOP + c
                seg = x[a0:b0]
                segs.append(dict(f=float(np.median(f[i:j + 1])), x=seg / np.sqrt(np.mean(seg[len(seg) // 5:] ** 2))))
            i = j + 1
        _SEGS = segs
    return _SEGS


XF = int(0.04 * SR)


def _render(seg, start, step):
    cum = start + np.concatenate([[0.0], np.cumsum(step[:-1])])
    return np.interp(cum, np.arange(len(seg['x'])), seg['x']), cum


def _phrase(ft, bounds, rng):
    """One breath: a chain of real held notes, each read at rate target/source, handed over with a
    phase-aligned crossfade whenever a note runs out or the tune moves to its next note (bounds)."""
    L = len(ft)
    out = np.zeros(L)
    segs = segments()
    t, prev_tail, last = 0, None, None
    while t < L - 1:
        f_now = ft[min(t + XF, L - 1)]
        near = np.argsort([abs(np.log2(f_now / s['f'])) for s in segs])
        cands = [k for k in near[:4] if k != last]
        k = int(rng.choice(cands))
        last = k
        seg = segs[k]
        step = ft[t:] / seg['f']
        lo = 0 if prev_tail is None else int(0.04 * SR)
        hi = len(seg['x']) - int(0.02 * SR)
        start = lo
        if prev_tail is not None:                         # line the new note's phase up with the old one
            n = min(XF, L - t)
            P = int(SR / seg['f']) + 1
            best = -np.inf
            for lag in range(0, P):
                y, _ = _render(seg, lo + lag, step[:n])
                c = np.dot(y, prev_tail[:n])
                if c > best:
                    best, start = c, lo + lag
        piece, cum = _render(seg, start, step)
        m = int(np.searchsorted(cum, hi))
        nb = next((b for b in bounds if b > t + 2 * XF), None)
        if nb is not None:
            m = min(m, nb - t + XF)
        m = max(min(m, L - t), min(2 * XF + 1, L - t))
        piece = piece[:m]
        env = np.ones(m)
        if prev_tail is not None:
            env[:XF] = np.sin(np.linspace(0, np.pi / 2, XF)) ** 2
        if t + m < L:
            env[-XF:] = np.cos(np.linspace(0, np.pi / 2, XF)) ** 2
        out[t:t + m] += piece * env
        if t + m >= L:
            break
        prev_tail = piece[-XF:]
        t += m - XF
    return out


def whistle(notes, total, glide=0.07, seed=3):
    rng = np.random.default_rng(seed)
    ft, gate = I._glide_freq(notes, total, glide=glide)
    out = np.zeros(len(ft))
    notes = sorted(notes)
    i = 0
    while i < len(notes):                                 # group legato notes into breaths
        j = i
        while j + 1 < len(notes) and notes[j][0] + notes[j][2] >= notes[j + 1][0] - 1e-3:
            j += 1
        a = max(int((notes[i][0] - 0.01) * SR), 0)
        b = min(int((notes[j][0] + notes[j][2] + 0.1) * SR), len(ft))
        bounds = [int((notes[k][0] + glide) * SR) - a for k in range(i + 1, j + 1)]
        out[a:b] += _phrase(ft[a:b], bounds, rng)
        i = j + 1
    g = sosfilt(butter(1, 30, 'low', fs=SR, output='sos'), gate)            # rests still close cleanly
    return out * np.clip(g * 1.6, 0, 1) * 0.3
