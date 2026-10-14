"""A highlights reel: ~12 s of each piece's best moment, with a small title, for reviewing on a phone.

python reel.py  ->  E:\\Claude\\music-video-2-work\\reel-phone.mp4
"""
import os
import subprocess

W = r"E:/Claude/music-video-2-work"
# (folder/file, start s, title)
CLIPS = [
    ("01/v4-phone.mp4", 60, "01  Drawn Sound"),
    ("02/city_v4-phone.mp4", 95, "02  Player Piano City"),
    ("03/journey_v4-phone.mp4", 150, "03  The Tune That Travelled"),
    ("04/maint_v3-phone.mp4", 120, "04  Maintenance"),
    ("06/transit_v1-phone.mp4", 112, "06  Transit Canon"),
    ("07/relay_v1-phone-small.mp4", 160, "07  Relay"),
    ("08/tidal_v1-phone.mp4", 95, "08  Tidal Clock"),
    ("09/typewriter_v1-phone.mp4", 140, "09  Typewriter Weather"),
    ("10/clockwork_v3-phone.mp4", 70, "10  Clockwork"),
    ("11/signal_v1-phone.mp4", 150, "11  Signal"),
    ("12/passacaglia_v1-phone.mp4", 152, "12  Passacaglia"),
    ("13/murmuration_v1-phone.mp4", 85, "13  Murmuration"),
]
DUR = 12.0
FONT = "C\\:/Windows/Fonts/georgia.ttf"
parts = []
for k, (f, s, title) in enumerate(CLIPS):
    out = f"{W}/_reel_{k:02d}.mp4"
    vf = (f"scale=1280:720,fade=t=in:st=0:d=0.5,fade=t=out:st={DUR - 0.5}:d=0.5,"
          f"drawtext=fontfile='{FONT}':text='{title}':x=40:y=h-70:fontsize=34:fontcolor=white@0.9:"
          f"shadowcolor=black@0.6:shadowx=2:shadowy=2:enable='lt(t,4)'")
    af = f"afade=t=in:st=0:d=0.5,afade=t=out:st={DUR - 0.5}:d=0.5"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", str(DUR), "-i", f"{W}/{f}", "-vf", vf, "-af", af,
                    "-r", "24", "-c:v", "libx264", "-crf", "27", "-preset", "medium", "-threads", "2",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", out], check=True)
    parts.append(out)
lst = f"{W}/_reel_list.txt"
with open(lst, "w") as fh:
    fh.writelines(f"file '{p}'\n" for p in parts)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart",
                f"{W}/reel-phone.mp4"], check=True)
for p in parts + [lst]:
    os.remove(p)
print("ok")
