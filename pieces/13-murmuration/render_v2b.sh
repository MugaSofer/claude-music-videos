#!/bin/bash
# Murmuration v2b (frayed edges, no hard rim): flapping individual birds, faster flight, collective swerves rippling across the flock. Chunked.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/13'
python ../../chunk_render.py --cmd "python film.py video {out} {t0} {t1}" --cwd . --total 181.545     --work "$W/chunks_v2b" --audio "$W/murmuration.wav" --out "$W/murmuration_v2b.mp4" > "$W/v2b.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/murmuration_v2b.mp4" -c:v libx264 -crf 20 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/murmuration_v2b-1080p.mp4" >> "$W/v2b.log" 2>&1
echo done >> "$W/v2b.log"
