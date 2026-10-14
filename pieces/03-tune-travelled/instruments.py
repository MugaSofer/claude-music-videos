"""Synthesised instruments for The Tune That Travelled (no samples).

Each instrument renders a monophonic line from [(t0, freq, dur, vel)] with its own
idiom (slides, breath, vibrato, mechanics), so the same notes sound like different
people in different centuries.
"""
import numpy as np
from scipy.signal import butter, sosfilt, lfilter

SR = 48000


def _t(n):
    return np.arange(n) / SR


def _env_adsr(n, a, d, s, r):
    e = np.ones(n) * s
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    A = min(A, n); e[:A] = np.linspace(0, 1, A) if A else e[:A]
    D = min(D, n - A); e[A:A + D] = np.linspace(1, s, D) if D else e[A:A + D]
    if R and R < n:
        e[-R:] *= np.linspace(1, 0, R)
    return e


def _bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def _glide_freq(notes, total, glide=0.06, lead=0.0):
    """A continuous pitch track through the notes (for monophonic, legato instruments)."""
    f = np.zeros(int(total * SR))
    gate = np.zeros_like(f)
    prev = None
    for (t0, fr, du, v) in notes:
        i0, i1 = int(t0 * SR), min(int((t0 + du) * SR), len(f))
        if i1 <= i0:
            continue
        seg = np.full(i1 - i0, fr)
        if prev is not None:
            g = min(int(glide * SR), i1 - i0)
            seg[:g] = prev + (fr - prev) * (1 - np.cos(np.linspace(0, np.pi, g))) / 2
        f[i0:i1] = seg
        gate[i0:i1] = v
        prev = fr
    # hold pitch through rests so glides start from the last note
    if notes and f[0] == 0:
        f[0] = notes[0][1]
    idx = np.where(f > 0, np.arange(len(f)), 0)
    np.maximum.accumulate(idx, out=idx)
    return f[idx], gate


def whistle(notes, total, rng=None):
    """Shepherd's whistle: near-sine, breathy, scooping slides, slow vibrato that grows on held notes."""
    rng = rng or np.random.default_rng(1)
    f, gate = _glide_freq(notes, total, glide=0.09)
    t = _t(len(f))
    vib = 1 + 0.012 * np.sin(2 * np.pi * 5.2 * t) * np.clip(gate, 0, 1)
    ph = 2 * np.cumsum(np.pi * f * vib / SR)
    tone = np.sin(ph) + 0.06 * np.sin(2 * ph)
    breath = _bandpass(rng.standard_normal(len(f)), 1500, 6000) * 0.05
    g = sosfilt(butter(1, 18, 'low', fs=SR, output='sos'), gate)        # soft articulation
    return (tone * 0.8 + breath) * g


def hum(notes, total, rng=None, nasal=1.0):
    """Closed-mouth hum: glottal pulse train through a nasal filter (low formant ~250 Hz, antiformant ~1 kHz)."""
    rng = rng or np.random.default_rng(2)
    f, gate = _glide_freq(notes, total, glide=0.12)
    t = _t(len(f))
    jitter = 1 + 0.004 * _bandpass(rng.standard_normal(len(f)), 2, 8, 1) * 30
    vib = 1 + 0.008 * np.sin(2 * np.pi * 4.6 * t)
    ph = np.cumsum(f * vib * jitter / SR) % 1.0
    # Rosenberg-ish glottal pulse
    op = 0.6
    pulse = np.where(ph < op * 0.6, 0.5 * (1 - np.cos(np.pi * ph / (op * 0.6))),
                     np.where(ph < op, np.cos(np.pi * (ph - op * 0.6) / (op * 0.8)), 0.0))
    src = np.diff(pulse, prepend=0) * 20
    x = _bandpass(src, 180, 380, 2) * 1.0 + _bandpass(src, 2000, 2800, 1) * 0.08 * nasal
    x += sosfilt(butter(2, 900, 'low', fs=SR, output='sos'), src) * 0.35
    breath = _bandpass(rng.standard_normal(len(f)), 200, 900) * 0.01
    g = sosfilt(butter(1, 9, 'low', fs=SR, output='sos'), gate)
    return (x + breath) * g


def organ(notes, total, drone_hz=None, fifth_below=True):
    """Portative organ: flue pipes (few harmonics, chiff on attack), parallel fifth below (organum), optional drone."""
    n = int(total * SR)
    out = np.zeros(n)
    rng = np.random.default_rng(3)
    voices = [(1.0, 1.0)] + ([(2 / 3, 0.55)] if fifth_below else [])
    for (t0, fr, du, v) in notes:
        i0 = int(t0 * SR); m = min(int(du * SR), n - i0)
        if m <= 0:
            continue
        t = _t(m)
        e = _env_adsr(m, 0.04, 0.05, 0.9, 0.06)
        for ratio, amp in voices:
            f = fr * ratio
            x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
            out[i0:i0 + m] += amp * x * e * v
        chiff = _bandpass(rng.standard_normal(min(m, int(0.05 * SR))), fr * 2, min(fr * 6, 20000)) * 0.15
        out[i0:i0 + len(chiff)] += chiff * np.linspace(1, 0, len(chiff))
    if drone_hz:
        t = _t(n)
        out += 0.35 * (np.sin(2 * np.pi * drone_hz * t) + 0.3 * np.sin(4 * np.pi * drone_hz * t)) * np.clip(t / 2, 0, 1)
    return out * 0.5


def concertina(notes, total):
    """Free-reed squeezebox: bright pulse-ish tone, two reeds slightly detuned (wet tuning), bellows swell."""
    n = int(total * SR)
    out = np.zeros(n)
    for (t0, fr, du, v) in notes:
        i0 = int(t0 * SR); m = min(int(du * SR), n - i0)
        if m <= 0:
            continue
        t = _t(m)
        x = np.zeros(m)
        for det in (1.0, 1.004):
            ph = (fr * det * t) % 1.0
            x += np.where(ph < 0.32, 1.0, -0.47)
        x = sosfilt(butter(2, min(fr * 7, 9000), 'low', fs=SR, output='sos'), x)
        e = _env_adsr(m, 0.03, 0.08, 0.8, 0.05) * (1 + 0.15 * np.sin(np.pi * t / max(du, 0.1)))
        out[i0:i0 + m] += x * e * v * 0.4
    return out


def stomp(times, total):
    """Boot on a wooden deck: thud plus knock."""
    n = int(total * SR)
    out = np.zeros(n)
    rng = np.random.default_rng(5)
    k = int(0.25 * SR)
    tt = _t(k)
    thud = np.sin(2 * np.pi * 70 * tt * (1 - 0.3 * tt)) * np.exp(-tt / 0.06)
    knock = _bandpass(rng.standard_normal(k), 300, 1200) * np.exp(-tt / 0.015)
    hit = thud + 0.5 * knock
    for t0 in times:
        i0 = int(t0 * SR)
        m = min(k, n - i0)
        if m > 0:
            out[i0:i0 + m] += hit[:m]
    return out * 0.6


def music_box(notes, total, wind_down=None):
    """Steel comb tines: inharmonic partials (1, 5.4, 11.9) with a bright ping and long ring.
    wind_down: (t_start, t_end) over which the spring slows: timing stretches and pitch sags slightly."""
    n = int(total * SR)
    out = np.zeros(n)
    for (t0, fr, du, v) in notes:
        sag = 1.0
        if wind_down and t0 > wind_down[0]:
            k = min((t0 - wind_down[0]) / (wind_down[1] - wind_down[0]), 1.0)
            sag = 1 - 0.015 * k
        i0 = int(t0 * SR); m = min(int(2.5 * SR), n - i0)
        if m <= 0:
            continue
        t = _t(m)
        f = fr * sag
        x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.1) + 0.45 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.18)
             + 0.2 * np.sin(2 * np.pi * f * 11.9 * t) * np.exp(-t / 0.05))
        out[i0:i0 + m] += x * v * 0.5
    return out


def square(notes, total, duty=0.5):
    """Phone ringtone: a naive (aliasy on purpose) square wave with hard gating."""
    n = int(total * SR)
    out = np.zeros(n)
    for (t0, fr, du, v) in notes:
        i0 = int(t0 * SR); m = min(int(du * SR * 0.9), n - i0)
        if m <= 0:
            continue
        ph = (fr * _t(m)) % 1.0
        out[i0:i0 + m] += np.where(ph < duty, 1.0, -1.0) * v * 0.25
    return out


def brass(notes, total):
    """A band's cornet line: sawtooth-ish with a brightness that opens with loudness, plus vibrato."""
    n = int(total * SR)
    out = np.zeros(n)
    for (t0, fr, du, v) in notes:
        i0 = int(t0 * SR); m = min(int(du * SR), n - i0)
        if m <= 0:
            continue
        t = _t(m)
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.3, 0, 1)
        ph = np.cumsum(fr * vib / SR)
        x = sum(np.sin(2 * np.pi * k * ph) / k ** 1.1 for k in range(1, 14))
        e = _env_adsr(m, 0.035, 0.1, 0.75, 0.06)
        cut = 900 + 3500 * v
        x = sosfilt(butter(2, cut, 'low', fs=SR, output='sos'), x)
        out[i0:i0 + m] += x * e * v * 0.4
    return out


def radio(x, rng=None):
    """Through an old wireless: 300-3400 Hz band, soft saturation, crackle and hiss, a little fade wobble."""
    rng = rng or np.random.default_rng(9)
    y = _bandpass(x, 300, 3400, 2)
    y = np.tanh(y * 2.5) / 2.5
    n = len(y)
    t = _t(n)
    y *= 1 + 0.12 * np.sin(2 * np.pi * 0.3 * t)
    hiss = _bandpass(rng.standard_normal(n), 2000, 6000) * 0.012
    crack = np.zeros(n)
    idx = rng.integers(0, n, int(n / SR * 9))
    crack[idx] = rng.uniform(-0.5, 0.5, len(idx))
    crack = _bandpass(crack, 1000, 7000)
    return y + hiss + crack * 0.6
