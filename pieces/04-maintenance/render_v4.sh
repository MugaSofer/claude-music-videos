#!/bin/bash
# Maintenance v4: can handle fixed (rotates with the can, feet on the rim), piece-3 hum cut, mastered to -16 LUFS. Chunked.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/04'
python ../../chunk_render.py --cmd "python scene.py {out} {t0} {t1}" --cwd . --total 140.0     --work "$W/chunks_v4" --audio "$W/maintenance_v4.wav" --out "$W/maint_v4.mp4" > "$W/v4.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/maint_v4.mp4" -c:v libx264 -crf 20 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/maint_v4-1080p.mp4" >> "$W/v4.log" 2>&1
echo done >> "$W/v4.log"
