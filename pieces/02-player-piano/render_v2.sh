#!/bin/bash
# Waits for piece 3's render to finish (CPU), then renders piece 2 v2 with audio and a phone preview.
cd "$(dirname "$0")"
W='E:\Claude\music-video-2-work\02'
while ! grep -q done /e/Claude/music-video-2-work/03/v1.log 2>/dev/null; do sleep 60; done
python city.py "$W\\city_v2_video.mp4" > "$W\\v2.log" 2>&1
ffmpeg -v error -y -i "$W\\city_v2_video.mp4" -i "$W\\canon.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W\\city_v2.mp4" >> "$W\\v2.log" 2>&1
ffmpeg -v error -y -i "$W\\city_v2.mp4" -vf scale=1280:720 -c:v libx264 -crf 26 -preset slow -threads 2 -c:a copy -movflags +faststart "$W\\city_v2-phone.mp4" >> "$W\\v2.log" 2>&1
echo done >> "$W\\v2.log"
