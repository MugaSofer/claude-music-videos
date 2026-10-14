"""A synthesised player piano (no samples).

Modal synthesis: each note is a bank of slightly inharmonic partials (stiff-string
stretch), sounded by 2-3 slightly detuned strings (the beating that makes pianos
shimmer), with a two-stage decay (prompt sound, then aftersound) and a short
felt-and-wood hammer thump. `metal` > 0 brightens the attack the way Nancarrow's
tacked hammers did.
"""
import numpy as np

SR = 48000


def midi_hz(m):
    return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)


def note(midi, vel=0.8, dur=2.5, metal=0.4, seed=0):
    rng = np.random.default_rng(seed + int(midi * 7))
    f0 = float(midi_hz(midi))
    n_len = int((dur + 0.05) * SR)
    t = np.arange(n_len) / SR
    B = 0.00012 * 2 ** ((midi - 60) / 20)             # inharmonicity rises up the keyboard
    maxp = int(min(40, 16000 / f0))
    out = np.zeros(n_len)
    strings = 1 if midi < 35 else (2 if midi < 50 else 3)
    detune_c = [0.0, 0.9, -0.7][:strings]
    bright = 0.25 + 0.6 * vel ** 1.5 + 0.3 * metal
    t_long = 3.2 * (1.9 ** (-(midi - 48) / 12)) + 0.25  # low notes ring longer
    for n in range(1, maxp + 1):
        fn = n * f0 * np.sqrt(1 + B * n * n)
        if fn > 18000:
            break
        amp = (1 / n ** (1.9 - 0.7 * bright)) * np.exp(-((n - 1) / (2.5 + 9 * bright ** 2))) * np.exp(-fn / (1800 + 5000 * bright ** 2))
        amp *= abs(np.sin(np.pi * n * 0.118)) + 0.08    # hammer strikes 1/8.5 along the string
        tau1 = 0.22 * t_long / (1 + 0.35 * n)
        tau2 = t_long / (1 + 0.12 * n)
        env = 0.65 * np.exp(-t / tau1) + 0.35 * np.exp(-t / tau2)
        for dc in detune_c:
            f = fn * 2 ** (dc / 1200)
            out += amp * env * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) / strings
    # hammer thump: brief low noise burst (felt) plus a click (metal)
    k = int(0.03 * SR)
    thump = rng.standard_normal(k) * np.exp(-np.arange(k) / (0.006 * SR))
    thump = np.convolve(thump, np.ones(12) / 12, mode='same')
    click = rng.standard_normal(k // 6) * np.exp(-np.arange(k // 6) / (0.0008 * SR))
    out[:k] += 0.05 * thump * (0.5 + vel)
    out[:k // 6] += 0.04 * metal * click
    # attack ramp (1 ms) and release damper (80 ms before the end)
    a = int(0.001 * SR)
    out[:a] *= np.linspace(0, 1, a)
    r = int(0.08 * SR)
    out[-r:] *= np.linspace(1, 0, r) ** 2
    return out * vel ** 1.3


def render(events, total, metal=0.4):
    """events: [(time_s, midi, vel, dur_s)] -> stereo float array (pan by pitch, like sitting at the keyboard)."""
    L = np.zeros(int(total * SR) + SR)
    R = np.zeros_like(L)
    cache = {}
    for (t0, m, v, d) in events:
        key = (int(m), round(v, 2), round(min(d, 4.0), 2))
        if key not in cache:
            cache[key] = note(int(m), v, min(d, 4.0), metal)
        x = cache[key]
        i = int(t0 * SR)
        j = min(i + len(x), len(L))
        pan = np.clip((m - 21) / 87, 0, 1)
        L[i:j] += x[:j - i] * np.cos(pan * np.pi / 2) * 1.2
        R[i:j] += x[:j - i] * np.sin(pan * np.pi / 2) * 1.2
    return np.stack([L, R], 1)


def room(x, seconds=1.8, mix=0.18, seed=3):
    """A plain synthetic room: exponentially decaying stereo noise, convolved via FFT."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    env = np.exp(-np.arange(n) / (seconds * SR / 6.9))
    out = np.empty_like(x)
    for c in range(2):
        ir = rng.standard_normal(n) * env
        ir[:int(0.012 * SR)] = 0                      # pre-delay
        ir /= np.sqrt((ir ** 2).sum())
        L = len(x[:, c]) + n
        nfft = 1 << (L - 1).bit_length()
        wet = np.fft.irfft(np.fft.rfft(x[:, c], nfft) * np.fft.rfft(ir, nfft), nfft)[:len(x)]
        out[:, c] = x[:, c] * (1 - mix) + wet * mix * 3
    return out
