#!/bin/bash
# Murmuration v4b: boids (boids.py) steered by the music (film4.py): piano A/B roosts part and meet with the phasing,
# chord changes startle the flock's edge, a stream arrives in the gather, they pour into the reeds at dusk. Chunked.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/13'
python ../../chunk_render.py --cmd "python film4.py video {out} {t0} {t1}" --cwd . --total 181.545 \
    --work "$W/chunks_v4c" --audio "$W/murmuration.wav" --out "$W/murmuration_v4c.mp4" > "$W/v4c.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/murmuration_v4c.mp4" -c:v libx264 -crf 20 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/murmuration_v4c-1080p.mp4" >> "$W/v4c.log" 2>&1
echo done >> "$W/v4c.log"
