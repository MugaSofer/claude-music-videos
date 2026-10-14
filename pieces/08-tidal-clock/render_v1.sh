#!/bin/bash
# Piece 8 v1: full film, mux, phone preview (capped for the upload limit).
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/08'
python film.py video "$W/tidal_v1_video.mp4" > "$W/v1.log" 2>&1
ffmpeg -v error -y -i "$W/tidal_v1_video.mp4" -i "$W/tidal.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/tidal_v1.mp4" >> "$W/v1.log" 2>&1
ffmpeg -v error -y -i "$W/tidal_v1.mp4" -vf scale=1280:720 -c:v libx264 -crf 30 -maxrate 900k -bufsize 1800k -preset slow -threads 2 -c:a aac -b:a 128k -movflags +faststart "$W/tidal_v1-phone.mp4" >> "$W/v1.log" 2>&1
echo done >> "$W/v1.log"
