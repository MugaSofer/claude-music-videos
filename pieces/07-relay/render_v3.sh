#!/bin/bash
# Relay v3: synth piano back (Muga's preference), bulrush heads on their stems, caption bands. Chunked/resumable.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/07'
TOTAL=$(python -c "import json;print(json.load(open('score.json'))['total']+3)")
python ../../chunk_render.py --cmd "python film.py video {out} {t0} {t1}" --cwd . --total $TOTAL \
    --work "$W/chunks_v3" --audio "$W/relay_v3.wav" --out "$W/relay_v3.mp4" > "$W/v3.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/relay_v3.mp4" -c:v libx264 -crf 20 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/relay_v3-1080p.mp4" >> "$W/v3.log" 2>&1
echo done >> "$W/v3.log"
