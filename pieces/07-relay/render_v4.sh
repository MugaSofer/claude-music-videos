#!/bin/bash
# Relay v4: Gemini's caption said "let this one pass", an invented quote for what were system errors (Muga asked Gemini,
# 10-19). Now "an error each time; the tune went on unchanged". Only the 60-100 s chunks change: the others are copied
# from chunks_v3 into chunks_v4, so chunk_render rebuilds just the missing two.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/07'
TOTAL=$(python -c "import json;print(json.load(open('score.json'))['total']+3)")
python ../../chunk_render.py --cmd "python film.py video {out} {t0} {t1}" --cwd . --total $TOTAL \
    --work "$W/chunks_v4" --audio "$W/relay_v3.wav" --out "$W/relay_v4.mp4" > "$W/v4.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/relay_v4.mp4" -c:v libx264 -profile:v high -crf 20 -preset slow -threads 2 -pix_fmt yuv420p \
    -c:a copy -movflags +faststart "$W/relay_v4-1080p.mp4" >> "$W/v4.log" 2>&1 || exit 1
echo done >> "$W/v4.log"
