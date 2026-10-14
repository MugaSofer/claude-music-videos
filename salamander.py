"""A small sampler for the Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0; Yamaha C5).

Samples are every minor third from A0 with 16 velocity layers (44.1 kHz). note() picks the nearest
sampled pitch and velocity layer, then repitches it and resamples to 48 kHz in one linear
interpolation (the shifts are at most +/-1.5 semitones), and applies a damper fade at note-off.

    from salamander import render
    stereo = render([(t, midi, vel, dur), ...], total_seconds)
"""
import os

import numpy as np
from scipy.io import wavfile

SR = 48000
DIR = r"E:\Claude\music-video-2-research\salamander\SalamanderGrandPianoV3_44.1khz16bit\44.1khz16bit"
NAMES = {9: "A", 0: "C", 3: "D#", 6: "F#"}
_raw = {}
_out = {}


def _sample_name(m):
    """Nearest sampled midi note (A0=21 .. C8=108, every 3 semitones)."""
    s = int(round((m - 21) / 3)) * 3 + 21
    s = min(max(s, 21), 108)
    return s, f"{NAMES[s % 12]}{s // 12 - 1}"


def _load(name, layer):
    key = (name, layer)
    if key not in _raw:
        sr, x = wavfile.read(os.path.join(DIR, f"{name}v{layer}.wav"))
        x = x.astype(np.float32) / 32768.0
        if x.ndim == 1:
            x = np.stack([x, x], 1)
        _raw[key] = (sr, x)
    return _raw[key]


def note(m, vel=0.7, dur=1.0, release=0.35):
    """Stereo float32 array for one note at 48 kHz."""
    m = int(round(m))
    layer = int(np.clip(round(vel ** 0.8 * 15) + 1, 1, 16))
    key = (m, layer, round(dur, 2))
    if key in _out:
        return _out[key]
    s, name = _sample_name(m)
    sr, x = _load(name, layer)
    ratio = 2 ** ((m - s) / 12)                     # repitch factor
    step = ratio * sr / SR                          # source samples per output sample
    n_out = int(min(len(x) / step, (dur + release + 0.05) * SR))
    pos = np.arange(n_out) * step
    y = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
    k = int(dur * SR)
    if k < n_out:                                   # the damper comes down
        r = n_out - k
        y[k:] *= np.exp(-np.arange(r) / (release * SR / 4))[:, None]
    a = int(0.002 * SR)
    y[:a] *= np.linspace(0, 1, a)[:, None]
    _out[key] = y.astype(np.float32)
    return _out[key]


def render(events, total, gain=0.5):
    """events: [(t, midi, vel, dur)] -> stereo float array of `total` seconds."""
    out = np.zeros((int(total * SR) + SR, 2), np.float32)
    for t, m, v, d in events:
        y = note(m, v, d)
        i = int(t * SR)
        j = min(i + len(y), len(out))
        if j > i:
            out[i:j] += y[:j - i] * gain
    return out
