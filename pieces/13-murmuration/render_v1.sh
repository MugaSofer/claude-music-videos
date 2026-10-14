#!/bin/bash
# Piece 13 v1: smoke test, full film, mux, phone preview (capped for the upload limit).
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/13'
python film.py smoke x > "$W/v1.log" 2>&1 || { echo "SMOKE FAILED" >> "$W/v1.log"; exit 1; }
python film.py video "$W/murmuration_v1_video.mp4" >> "$W/v1.log" 2>&1
ffmpeg -v error -y -i "$W/murmuration_v1_video.mp4" -i "$W/murmuration.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/murmuration_v1.mp4" >> "$W/v1.log" 2>&1
ffmpeg -v error -y -i "$W/murmuration_v1.mp4" -vf scale=1280:720 -c:v libx264 -crf 28 -maxrate 1000k -bufsize 2000k -preset slow -threads 2 -c:a aac -b:a 128k -movflags +faststart "$W/murmuration_v1-phone.mp4" >> "$W/v1.log" 2>&1
echo done >> "$W/v1.log"
