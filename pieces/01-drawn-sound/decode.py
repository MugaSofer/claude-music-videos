"""Decode the soundtrack from a video file's pixels. This is the only source of audio.

usage: python decode.py frames.mkv out.wav [gain]

Post-processing is deliberately minimal and fixed for the whole piece:
DC-block / high-pass at 20 Hz, one constant gain, and a hard safety clip.
"""
import subprocess
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

from optical import W, H, SR, columns_to_samples


def read_frames(path):
    cmd = ['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    p.wait()


def decode(path):
    return np.concatenate([columns_to_samples(f) for f in read_frames(path)])


def finish(raw, gain):
    sos = butter(2, 20, 'highpass', fs=SR, output='sos')
    x = sosfilt(sos, raw - raw[:SR // 10].mean())
    return np.clip(x * gain, -1, 1)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    gain = float(sys.argv[3]) if len(sys.argv) > 3 else None
    raw = decode(src)
    if gain is None:
        sos = butter(2, 20, 'highpass', fs=SR, output='sos')
        peak = np.abs(sosfilt(sos, raw - raw[:SR // 10].mean())).max()
        gain = 0.9 / max(peak, 1e-9)
        print(f'auto gain {gain:.2f} (fix this constant for the final piece)')
    out = finish(raw, gain)
    wavfile.write(dst, SR, (out * 32767).astype(np.int16))
    print(f'{len(out) / SR:.2f}s written to {dst}')
