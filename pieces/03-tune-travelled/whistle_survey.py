"""Survey candidate whistle recordings: pitch range, how much is voiced, held notes, noise floor."""
import glob, subprocess, sys
import numpy as np

SR = 44100


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def track(x, hop=441, n=4096):
    """Whistles are near-sinusoids: the spectral peak (parabolic-interpolated) is the pitch."""
    win = np.hanning(n)
    f, a, tonal = [], [], []
    for i in range(0, len(x) - n, hop):
        s = np.abs(np.fft.rfft(x[i:i + n] * win))
        lo, hi = int(400 * n / SR), int(4000 * n / SR)
        k = lo + int(np.argmax(s[lo:hi]))
        y0, y1, y2 = np.log(s[k - 1:k + 2] + 1e-12)
        d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
        f.append((k + d) * SR / n)
        a.append(s[k])
        tonal.append(s[k - 2:k + 3].sum() ** 2 / ((s ** 2).sum() + 1e-12))   # energy share of the peak
    return np.array(f), np.array(a), np.array(tonal)


for p in sorted(glob.glob(sys.argv[1] + '/*.mp3')):
    x = load(p)
    f, a, ton = track(x)
    v = (ton > 0.6) & (a > a.max() * 0.05)
    fv = f[v]
    held = 0
    run = 0
    for i in range(1, len(f)):                     # held notes: >=0.25 s within 40 cents
        if v[i] and v[i - 1] and abs(1200 * np.log2(f[i] / f[i - 1])) < 40:
            run += 1
        else:
            held += run >= 25
            run = 0
    print(f"{p.split(chr(92))[-1].split('/')[-1]:28} {len(x)/SR:5.1f}s voiced {v.mean():.0%} "
          f"range {np.percentile(fv,3):.0f}-{np.percentile(fv,97):.0f} Hz held notes {held} "
          f"tonality {np.median(ton[v]):.2f} floor {20*np.log10(np.percentile(np.abs(x),10)+1e-9):.0f} dB")
