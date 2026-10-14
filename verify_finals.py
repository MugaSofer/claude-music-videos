"""Check every *_final-1080p.mp4: H.264 profile/pix_fmt/level via ffprobe, plus a full decode test."""
import glob, json, subprocess

for f in sorted(glob.glob("E:/Claude/music-video-2-work/*/*_final-1080p.mp4")):
    p = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=profile,pix_fmt,level,width,height:format=duration", "-of", "json", f],
        capture_output=True, text=True).stdout)
    s, d = p["streams"][0], float(p["format"]["duration"])
    err = subprocess.run(["ffmpeg", "-v", "error", "-threads", "2", "-i", f, "-f", "null", "-"],
                         capture_output=True, text=True).stderr.strip()
    ok = s["profile"] in ("High", "Main") and s["pix_fmt"] == "yuv420p" and s["level"] <= 42 and not err
    print(f"{'OK ' if ok else 'BAD'} {f[-40:]:>40} {s['profile']} {s['pix_fmt']} L{s['level']} "
          f"{s['width']}x{s['height']} {d:.1f}s decode_errors={len(err.splitlines())}", flush=True)
