#!/bin/bash
# Piece 2 v3: render, mux with the canon audio, phone preview.
cd "$(dirname "$0")"
W='E:\Claude\music-video-2-work\02'
python city.py "$W\\city_v3_video.mp4" > "$W\\v3.log" 2>&1
ffmpeg -v error -y -i "$W\\city_v3_video.mp4" -i "$W\\canon.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W\\city_v3.mp4" >> "$W\\v3.log" 2>&1
ffmpeg -v error -y -i "$W\\city_v3.mp4" -vf scale=1280:720 -c:v libx264 -crf 26 -preset slow -threads 2 -c:a copy -movflags +faststart "$W\\city_v3-phone.mp4" >> "$W\\v3.log" 2>&1
echo done >> "$W\\v3.log"
