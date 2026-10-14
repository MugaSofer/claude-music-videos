"""Resumable chunked rendering: a kill costs one chunk, not the whole render.

    python chunk_render.py --cmd "python film.py {out} {t0} {t1}" --cwd PIECE_DIR --total 170 \
        --work E:/.../05/chunks_v2 --audio E:/.../05/takeB.wav --out E:/.../05/small_hours_v2.mp4

{out}, {t0} and {t1} in --cmd are filled in per chunk. Chunks whose file exists with the right duration are
skipped, so re-running the same command resumes. Chunks are joined losslessly (concat demuxer, -c copy),
then the audio is muxed in.
"""
import argparse
import os
import shlex
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--cmd", required=True)
ap.add_argument("--cwd", required=True)
ap.add_argument("--total", type=float, required=True)
ap.add_argument("--chunk", type=float, default=20.0)
ap.add_argument("--work", required=True)
ap.add_argument("--audio", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
os.makedirs(a.work, exist_ok=True)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


parts = []
t0 = 0.0
k = 0
while t0 < a.total - 1e-6:
    t1 = min(a.total, t0 + a.chunk)
    path = os.path.join(a.work, f"chunk_{k:03d}.mp4").replace("\\", "/")
    if os.path.exists(path) and abs(duration(path) - (t1 - t0)) < 0.2:
        print(f"chunk {k} ({t0:.0f}-{t1:.0f}s) already done", flush=True)
    else:
        cmd = a.cmd.format(out=path, t0=t0, t1=t1)
        print(f"chunk {k} ({t0:.0f}-{t1:.0f}s) rendering", flush=True)
        subprocess.run(shlex.split(cmd), cwd=a.cwd, check=True)
    parts.append(path)
    t0 = t1
    k += 1

lst = os.path.join(a.work, "list.txt")
with open(lst, "w") as f:
    f.writelines(f"file '{p}'\n" for p in parts)
video = os.path.join(a.work, "joined.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", a.audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                "-shortest", "-movflags", "+faststart", a.out], check=True)
print("done", a.out, flush=True)
