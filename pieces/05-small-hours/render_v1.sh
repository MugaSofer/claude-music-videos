#!/bin/bash
# Small Hours v1: render the film on take B, mux the song, phone preview.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/05'
python film.py "$W/sectionsB.json" "$W/small_hours_v1_video.mp4" > "$W/v1.log" 2>&1
ffmpeg -v error -y -i "$W/small_hours_v1_video.mp4" -i "$W/takeB.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/small_hours_v1.mp4" >> "$W/v1.log" 2>&1
ffmpeg -v error -y -i "$W/small_hours_v1.mp4" -vf scale=1280:720 -c:v libx264 -crf 25 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/small_hours_v1-phone.mp4" >> "$W/v1.log" 2>&1
echo done >> "$W/v1.log"
