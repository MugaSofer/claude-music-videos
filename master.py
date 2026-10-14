"""A shared mastering pass: high-pass, gentle bus compression, loudness to -14 LUFS, peak limit.

Loudness is ITU-R BS.1770 (K-weighting, 400 ms blocks with 75% overlap, -70 LUFS absolute and
-10 LU relative gates), with the standard 48 kHz filter coefficients.

    python master.py IN.wav OUT.wav [target_lufs]
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, sosfilt

SR = 48000
K1 = ([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585])
K2 = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])


def lufs(x):
    z = lfilter(*K2, lfilter(*K1, x, axis=0), axis=0)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([np.mean(z[i:i + blk] ** 2, axis=0).sum() for i in range(0, len(z) - blk, hop)])
    ld = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[ld > -70]
    if len(g) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = ms[(ld > -70) & (ld > rel)]
    return float(-0.691 + 10 * np.log10(g.mean()))


def compress(x, thresh_db=-20.0, ratio=2.0, attack=0.02, release=0.25):
    """A gentle RMS bus compressor (stereo-linked)."""
    lvl = np.sqrt(np.convolve(np.mean(x ** 2, axis=1), np.ones(480) / 480, mode="same")) + 1e-9
    db = 20 * np.log10(lvl)
    over = np.maximum(db - thresh_db, 0)
    target = -over * (1 - 1 / ratio)
    g = np.empty_like(target)
    a, r = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    cur = 0.0
    for i, v in enumerate(target):                 # smoothing: fast down, slow up
        c = a if v < cur else r
        cur = c * cur + (1 - c) * v
        g[i] = cur
    return x * (10 ** (g / 20))[:, None]


def limit(x, ceiling=10 ** (-1 / 20)):
    """Look-ahead peak limiter to -1 dBFS."""
    from scipy.ndimage import minimum_filter1d
    pk = np.max(np.abs(x), axis=1)
    need = np.minimum(1.0, ceiling / np.maximum(pk, 1e-9))
    win = int(0.005 * SR)
    need = minimum_filter1d(need, size=2 * win)               # look-ahead and hold
    need = np.convolve(need, np.ones(win) / win, mode="same")  # smooth the gain changes
    need = minimum_filter1d(need, size=win)                    # smoothing must never under-attenuate
    y = x * need[:, None]
    return np.clip(y, -ceiling, ceiling)                       # final safety on any stray sample


def master(x, target=-14.0):
    x = sosfilt(butter(2, 28, "high", fs=SR, output="sos"), x, axis=0)
    x = compress(x)
    gain = 10 ** ((target - lufs(x)) / 20)
    x = limit(x * gain)
    return x


if __name__ == "__main__":
    sr, x = wavfile.read(sys.argv[1])
    assert sr == SR, f"expected {SR} Hz, got {sr}"
    x = x.astype(np.float64) / 32768.0
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    target = float(sys.argv[3]) if len(sys.argv) > 3 else -14.0
    before = lufs(x)
    y = master(x, target)
    wavfile.write(sys.argv[2], SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    print(f"{before:.1f} LUFS -> {lufs(y):.1f} LUFS, peak {20 * np.log10(np.abs(y).max()):.1f} dBFS")
