#!/bin/bash
# Signal v3: re-composed music (chord per bar, letters as chord tones in arches, the sea answers, a build, a hush, GOODNIGHT in A major). Chunked.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/11'
python film.py smoke x > "$W/v3.log" 2>&1 || { echo "SMOKE FAILED" >> "$W/v3.log"; exit 1; }
python ../../chunk_render.py --cmd "python film.py video {out} {t0} {t1}" --cwd . --total 167.0 \
    --work "$W/chunks_v3" --audio "$W/signal_v3.wav" --out "$W/signal_v3.mp4" >> "$W/v3.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/signal_v3.mp4" -c:v libx264 -crf 20 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/signal_v3-1080p.mp4" >> "$W/v3.log" 2>&1
echo done >> "$W/v3.log"
