#!/bin/bash
# Piece 2 v4: render, mux with the canon audio, phone preview.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/02'
python render_v4.py "$W/city_v4_video.mp4" > "$W/v4.log" 2>&1
ffmpeg -v error -y -i "$W/city_v4_video.mp4" -i "$W/canon.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/city_v4.mp4" >> "$W/v4.log" 2>&1
ffmpeg -v error -y -i "$W/city_v4.mp4" -vf scale=1280:720 -c:v libx264 -crf 25 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/city_v4-phone.mp4" >> "$W/v4.log" 2>&1
echo done >> "$W/v4.log"
