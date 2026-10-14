#!/bin/bash
# Piece 10 v3: smoke test, full film, mux, phone preview (capped for the upload limit).
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/10'
python film.py smoke x > "$W/v3.log" 2>&1 || { echo "SMOKE FAILED" >> "$W/v3.log"; exit 1; }
python film.py video "$W/clockwork_v3_video.mp4" >> "$W/v3.log" 2>&1
ffmpeg -v error -y -i "$W/clockwork_v3_video.mp4" -i "$W/clockwork.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/clockwork_v3.mp4" >> "$W/v3.log" 2>&1
ffmpeg -v error -y -i "$W/clockwork_v3.mp4" -vf scale=1280:720 -c:v libx264 -crf 28 -maxrate 1000k -bufsize 2000k -preset slow -threads 2 -c:a aac -b:a 128k -movflags +faststart "$W/clockwork_v3-phone.mp4" >> "$W/v3.log" 2>&1
echo done >> "$W/v3.log"
