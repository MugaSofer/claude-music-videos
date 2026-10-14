#!/bin/bash
# Piece 6 v1: full film, mux, phone preview.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/06'
python film.py video "$W/transit_v1_video.mp4" > "$W/v1.log" 2>&1
ffmpeg -v error -y -i "$W/transit_v1_video.mp4" -i "$W/transit.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/transit_v1.mp4" >> "$W/v1.log" 2>&1
ffmpeg -v error -y -i "$W/transit_v1.mp4" -vf scale=1280:720 -c:v libx264 -crf 28 -maxrate 1500k -bufsize 3000k -preset slow -threads 2 -c:a copy -movflags +faststart "$W/transit_v1-phone.mp4" >> "$W/v1.log" 2>&1
echo done >> "$W/v1.log"
