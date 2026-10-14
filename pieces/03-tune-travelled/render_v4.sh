#!/bin/bash
# Piece 3 v4: repainted figures (shepherd, kitchen parent, child), same audio as v2/v3.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/03'
python journey.py "$W/journey_v4_video.mp4" > "$W/v4.log" 2>&1
ffmpeg -v error -y -i "$W/journey_v4_video.mp4" -i "$W/tune_v2.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/journey_v4.mp4" >> "$W/v4.log" 2>&1
ffmpeg -v error -y -i "$W/journey_v4.mp4" -vf scale=1280:720 -c:v libx264 -crf 26 -maxrate 1500k -bufsize 3000k -preset slow -threads 2 -c:a copy -movflags +faststart "$W/journey_v4-phone.mp4" >> "$W/v4.log" 2>&1
echo done >> "$W/v4.log"
