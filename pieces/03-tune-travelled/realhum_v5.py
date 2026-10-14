"""A real hum (v5): a recorded human hum, re-pitched to the tune by TD-PSOLA.

Muga: "the most human part is the most synthetic". So the kitchen and child voices now come from a real
recording: "Humming C D A for alexggqs" by drotzruhn (Freesound 439504, CC0), whose dry first half holds
long hummed A3, C4 and D4. Each source note is cut into pitch-synchronous grains (two periods, Hann
windowed, centred on the glottal peaks); the tune's pitch track then re-spaces them at the new period,
which keeps the singer's own nasal resonance, shimmer and breath. Grains are read in recorded order (with
ping-pong looping) so the natural wobble survives; `formant` > 1 shrinks each grain for a smaller (child)
voice.
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
SRC = r"E:\Claude\music-video-2-research\hum\hum48.wav"
NOTES = [(57.25, 40.9, 43.0), (57.25, 51.1, 54.1), (60.1, 7.3, 12.1), (62.3, 24.6, 29.2), (62.3, 104.8, 109.5)]
_BANKS = None


def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _marks(x, f0):
    """Pitch marks on the glottal peaks of a steady note: step a period at a time, snap to the local max."""
    P = SR / f0
    lp = sosfilt(butter(2, f0 * 1.8, "low", fs=SR, output="sos"), x)
    i = int(P) + int(np.argmax(lp[int(P):int(2 * P)]))
    out = []
    while i + 2 * P < len(x):
        out.append(i)
        c = int(i + P)
        w = int(P * 0.2)
        i = c - w + int(np.argmax(lp[c - w:c + w]))
    return np.array(out)


def banks():
    global _BANKS
    if _BANKS is None:
        sr, x = wavfile.read(SRC)
        x = x.astype(np.float64) / 32768
        _BANKS = []
        for m, a, b in NOTES:
            seg = x[int(a * SR):int(b * SR)]
            f0 = _hz(m)
            mk = _marks(seg, f0)
            P = int(SR / f0)
            grains = []
            for c in mk[1:-1]:
                grains.append(seg[c - P:c + P].copy())                  # raw; windowed at synthesis
            rms = np.sqrt(np.mean([np.mean((g * np.hanning(2 * P)) ** 2) for g in grains]))
            _BANKS.append(dict(m=m, f0=f0, grains=[g / rms for g in grains]))
    return _BANKS


def hum(notes, total, formant=1.0, seed=0):
    """notes: (t, hz, dur, vel). Returns mono audio of length total*SR."""
    from instruments import _glide_freq
    f, gate = _glide_freq(notes, total, glide=0.14)
    g = sosfilt(butter(1, 7, "low", fs=SR, output="sos"), gate)      # breathy onsets and releases
    B = banks()
    rng = np.random.default_rng(seed)
    out = np.zeros(len(f) + SR)
    pos = {i: rng.integers(0, len(b["grains"])) for i, b in enumerate(B)}
    dirn = {i: 1 for i in range(len(B))}
    t = 0.0
    n = len(f)
    while True:
        i = int(t)
        if i >= n:
            break
        if g[i] < 0.004:
            t += SR / 200
            continue
        fm = 69 + 12 * np.log2(f[i] / 440)
        k = min(range(len(B)), key=lambda j: abs(B[j]["m"] - (fm - 12 * np.log2(formant))))   # the nearest source note
        b = B[k]
        raw = b["grains"][pos[k]]
        P = len(raw) // 2
        half = min(P, int(1.25 * SR / f[i] * formant))                 # narrower windows for big upward shifts
        gr = raw[P - half:P + half] * np.hanning(2 * half) * np.sqrt(P / half)
        if formant != 1.0:                                             # shrink the grain: higher formants
            L = max(8, int(len(gr) / formant))
            gr = np.interp(np.linspace(0, len(gr) - 1, L), np.arange(len(gr)), gr)
        a = i - len(gr) // 2
        if a >= 0:
            out[a:a + len(gr)] += gr * g[i]
        # advance through the recording, ping-pong at the ends
        pos[k] += dirn[k]
        if pos[k] >= len(b["grains"]) - 1 or pos[k] <= 0:
            dirn[k] *= -1
        t += SR / f[i]
    out = out[:n]
    return sosfilt(butter(2, 70, "high", fs=SR, output="sos"), out) * 0.15
