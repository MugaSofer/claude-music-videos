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
            grains, pers = [], []
            for j in range(1, len(mk) - 1):
                c = mk[j]
                grains.append(seg[c - P:c + P].copy())                  # raw; windowed at synthesis
                pers.append((mk[j + 1] - mk[j - 1]) / 2)                # her actual period here
            rms = np.sqrt(np.mean([np.mean((g * np.hanning(2 * P)) ** 2) for g in grains]))
            pers = np.array(pers)
            _BANKS.append(dict(m=m, f0=f0, grains=[g / rms for g in grains], wob=pers / np.median(pers)))
    return _BANKS


def sung_pitch(notes, total):
    """A sung pitch track: each change of note is a damped spring (about 45 ms, a slight overshoot), and a
    note begun from silence scoops up from about 50 cents flat, instead of v5's perfect cosine glides."""
    n = int(total * SR)
    f = np.zeros(n)
    gate = np.zeros(n)
    cents = 0.0
    vel = 0.0
    prev_end, prev_hz = -1.0, None
    w0, zeta = 2 * np.pi / 0.09, 0.6
    for (t0, hz, du, v) in notes:
        i0, i1 = int(t0 * SR), min(int((t0 + du) * SR), n)
        if i1 <= i0:
            continue
        if prev_hz is None or t0 - prev_end > 0.06:
            cents, vel = -50.0, 0.0                       # a scoop from below
        else:
            cents, vel = 1200 * np.log2(prev_hz / hz) + cents, vel
        seg = np.empty(i1 - i0)
        dt = 1 / SR
        for k in range(i1 - i0):                          # spring toward 0 cents
            acc = -w0 * w0 * cents - 2 * zeta * w0 * vel
            vel += acc * dt
            cents += vel * dt
            seg[k] = cents
        f[i0:i1] = hz * 2 ** (seg / 1200)
        gate[i0:i1] = v
        prev_end, prev_hz = t0 + du, hz
    idx = np.where(f > 0, np.arange(n), 0)
    np.maximum.accumulate(idx, out=idx)
    f = f[idx]
    f[f == 0] = notes[0][1]
    return f, gate


def hum(notes, total, formant=1.0, seed=0):
    """notes: (t, hz, dur, vel). Returns mono audio of length total*SR."""
    f, gate = sung_pitch(notes, total)
    g = sosfilt(butter(1, 7, "low", fs=SR, output="sos"), gate)      # breathy onsets and releases
    B = banks()
    ms = np.array([b["m"] for b in B])
    rng = np.random.default_rng(seed)
    out = np.zeros(len(f) + SR)
    pos = [int(rng.integers(0, len(b["grains"]))) for b in B]
    dirn = [1] * len(B)
    shift = 12 * np.log2(formant)
    t = 0.0
    n = len(f)
    while True:
        i = int(t)
        if i >= n:
            break
        if g[i] < 0.004:
            t += SR / 200
            continue
        fm = 69 + 12 * np.log2(f[i] / 440) - shift
        # the two nearest source notes, cross-faded by pitch, so glides morph instead of switching
        order = np.argsort(np.abs(ms - fm))
        a, b2 = order[0], order[1]
        if abs(ms[a] - ms[b2]) < 0.5:
            wa = 1.0
        else:
            wa = float(np.clip(1 - abs(fm - ms[a]) / abs(ms[b2] - ms[a]), 0, 1)) ** 0.5
        wob = 1.0
        for k, w in ((a, wa), (b2, 1 - wa)):
            if w < 0.02:
                continue
            bk = B[k]
            raw = bk["grains"][pos[k]]
            P = len(raw) // 2
            half = min(P, int(1.25 * SR / f[i] * formant))             # narrower windows for big upward shifts
            gr = raw[P - half:P + half] * np.hanning(2 * half) * np.sqrt(P / half)
            if formant != 1.0:                                         # shrink the grain: higher formants
                L = max(8, int(len(gr) / formant))
                gr = np.interp(np.linspace(0, len(gr) - 1, L), np.arange(len(gr)), gr)
            s0 = i - len(gr) // 2
            if s0 >= 0:
                out[s0:s0 + len(gr)] += gr * g[i] * w
            if k == a:
                wob = bk["wob"][pos[k]]
            pos[k] += dirn[k]
            if pos[k] >= len(bk["grains"]) - 1 or pos[k] <= 0:
                dirn[k] *= -1
        t += SR / f[i] * wob                                           # her own wobble rides on the tune
    out = out[:n]
    return sosfilt(butter(2, 70, "high", fs=SR, output="sos"), out) * 0.15
