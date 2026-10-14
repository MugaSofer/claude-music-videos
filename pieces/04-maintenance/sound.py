"""Maintenance: the soundtrack. Near-silent, all synthesised.

usage: python sound.py   (writes E:/Claude/music-video-2-work/04/maintenance.wav)
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

import cues as C

sys.path.insert(0, '../03-tune-travelled')
import instruments as I  # noqa: E402
from tune import PARLOUR, semis  # noqa: E402

SR = 48000
N = int(C.TOTAL * SR)
rng = np.random.default_rng(40)
T = np.arange(N) / SR


def bp(x, lo, hi, o=2):
    return sosfilt(butter(o, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def place(buf, x, t0, gain=1.0):
    i = int(t0 * SR)
    j = min(i + len(x), len(buf))
    if j > i:
        buf[i:j] += x[:j - i] * gain


def drip(pitch=1400, decay=0.05):
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    f = pitch * (1 + 0.6 * np.exp(-t / 0.01))          # the bubble's upward chirp
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / decay)
    x[:int(0.002 * SR)] += rng.standard_normal(int(0.002 * SR)) * 0.3
    return x


def metallophone(midi, dur=6.0, beat_hz=4.5):
    f = 440 * 2 ** ((midi - 69) / 12)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for ratio, amp, tau in ((1, 1, 2.8), (2.76, 0.35, 0.9), (5.4, 0.15, 0.3), (8.93, 0.06, 0.12)):
        for det in (0, beat_hz):                        # the pair, tuned apart: ombak
            x += amp * np.sin(2 * np.pi * (f + det) * ratio * t) * np.exp(-t / tau)
    x[:int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    return x * 0.2


def creak(dur=1.2, f0=600):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + 0.25 * np.sin(2 * np.pi * t / dur))
    x = rng.standard_normal(n)
    y = np.zeros(n)
    for k in range(0, n, 2400):                          # a narrow band that glides
        seg = x[k:k + 2400]
        y[k:k + 2400] = bp(seg, f[k] * 0.97, f[k] * 1.03, 1)[:len(seg)]
    return y * np.sin(np.pi * t / dur) * 0.6


def ticks(t0, t1, rate):
    """Growth: tiny dry clicks, rate per second."""
    x = np.zeros(N)
    n = int((t1 - t0) * rate)
    for tt in rng.uniform(t0, t1, n):
        i = int(tt * SR)
        k = int(0.004 * SR)
        if i + k < N:
            x[i:i + k] += rng.standard_normal(k) * np.exp(-np.arange(k) / 40) * rng.uniform(0.05, 0.2)
    return bp(x, 2000, 9000)


def main():
    out = np.zeros(N)
    # wind through a crack: always there, gusting
    wind = bp(rng.standard_normal(N), 180, 1400)
    gust = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * T / 11) * np.sin(2 * np.pi * T / 4.3)) ** 2
    out += wind * gust * 0.02 * np.clip(1.2 - T / C.TOTAL, 0.4, 1)
    # drips: irregular, from the start
    t = 2.0
    while t < C.TOTAL - 4:
        place(out, drip(rng.uniform(1100, 1900)), t, rng.uniform(0.05, 0.12))
        t += rng.uniform(3.5, 9)
    # glass creaks
    for tc in (6, 33, 47, 71, 118):
        place(out, creak(rng.uniform(0.8, 1.6), rng.uniform(450, 800)), tc, 0.05)
    # the rituals
    place(out, creak(0.6, 1500), C.TAP_TURN[0] + 0.3, 0.06)                   # the tap squeak
    s0, s1 = C.STREAM
    stream = bp(rng.standard_normal(int((s1 - s0) * SR)), 700, 3500) * 0.05
    env = np.minimum(1, np.minimum(np.arange(len(stream)) / (0.4 * SR), (len(stream) - np.arange(len(stream))) / (0.8 * SR)))
    place(out, stream * env, s0)
    p0, p1 = C.POT_NUDGE
    scrape = bp(rng.standard_normal(int((p1 - p0) * SR)), 250, 1200) * 0.03
    scrape *= np.sin(np.pi * np.arange(len(scrape)) / len(scrape))
    place(out, scrape, p0)
    out += ticks(15, 35, 6) + ticks(35, 55, 10) + ticks(*C.REPLICA, 24) + ticks(C.REPLICA[1], 110, 5)
    # the metallophone
    AMBIENT_ONLY = '--ambient' in sys.argv          # v5: the composed score (music.py) replaces the metallophone
    for tm, m in ([] if AMBIENT_ONLY else C.METAL):
        place(out, metallophone(m), tm, 0.9 if tm < 85 else 0.6)
    # the hum: the gardener's tune (the first phrase of piece 3's), remembered by the building
    h0, h1 = C.HUM
    notes, t = [], h0
    for dg, du in PARLOUR[:11]:
        sec = du * 60 / 60
        notes.append((t - h0, 293.7 * 2 ** (semis(dg) / 12), sec * 0.95, 0.8))
        t += sec
    hum = I.hum(notes, h1 - h0 + 2)
    hum = bp(hum, 150, 2500) / (np.abs(hum).max() + 1e-9) * 0.16
    fade = np.minimum(1, np.minimum(np.arange(len(hum)) / (1.5 * SR), (len(hum) - np.arange(len(hum))) / (2.5 * SR)))
    # v4: cut. The quote of piece 3's tune read as a bug to Muga without setup, and the hum is synthetic.
    # place(out, hum * fade, h0)
    # the pour, and the last drop
    q0, q1 = C.POUR
    pour = bp(rng.standard_normal(int((q1 - q0) * SR)), 500, 4000) * 0.06
    pour *= np.sin(np.pi * np.arange(len(pour)) / len(pour)) ** 0.5
    place(out, pour, q0)
    place(out, drip(1250, 0.09), C.LAST_DROP, 0.2)
    # a small room: short reverb from filtered noise
    n = int(1.6 * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.35 * SR))
    ir[:int(0.01 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    L = N + n
    nfft = 1 << (L - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(out, nfft) * np.fft.rfft(ir, nfft), nfft)[:N]
    out = out * 0.8 + wet * 0.5
    out = out / np.abs(out).max() * 0.85
    name = 'maintenance_ambient.wav' if AMBIENT_ONLY else 'maintenance.wav'
    wavfile.write('E:/Claude/music-video-2-work/04/' + name, SR, (out * 32767).astype(np.int16))
    for a in range(0, int(C.TOTAL), 10):
        s = out[a * SR:(a + 10) * SR]
        print(f'{a:3d}s {20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9):6.1f} dB')


if __name__ == '__main__':
    main()
