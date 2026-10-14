#!/bin/bash
# Small Hours v2, rendered in resumable 20 s chunks (re-run this script to resume after a kill).
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/05'
python ../../chunk_render.py --cmd "python film.py $W/sectionsB.json {out} {t0} {t1}" --cwd . --total 170 \
    --work "$W/chunks_v2" --audio "$W/takeB.wav" --out "$W/small_hours_v2.mp4" > "$W/v2.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/small_hours_v2.mp4" -c:v libx264 -crf 20 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/small_hours_v2-1080p.mp4" >> "$W/v2.log" 2>&1
echo done >> "$W/v2.log"
