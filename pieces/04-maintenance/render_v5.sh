#!/bin/bash
# Maintenance v5: composed score (music.py), painted gloves (glove_art.py), handle fix. Chunked and resumable.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/04'
python ../../chunk_render.py --cmd "python scene.py {out} {t0} {t1}" --cwd . --total 140.0 \
    --work "$W/chunks_v5" --audio "$W/maintenance_v5.wav" --out "$W/maint_v5.mp4" > "$W/v5.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/maint_v5.mp4" -c:v libx264 -crf 20 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/maint_v5-1080p.mp4" >> "$W/v5.log" 2>&1
echo done >> "$W/v5.log"
