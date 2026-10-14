#!/bin/bash
# Small Hours v2: vignettes cued to the sung lines (vocal-stem onsets), bridge opens on the sleeping city,
# a real sunrise by "And now the morning comes", the lamp comes down on "Keep the lamp low". 1080p delivery.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/05'
python film.py "$W/sectionsB.json" "$W/small_hours_v2_video.mp4" > "$W/v2.log" 2>&1
ffmpeg -v error -y -i "$W/small_hours_v2_video.mp4" -i "$W/takeB.wav" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$W/small_hours_v2.mp4" >> "$W/v2.log" 2>&1
ffmpeg -v error -y -i "$W/small_hours_v2.mp4" -c:v libx264 -crf 20 -preset slow -threads 2 -c:a copy -movflags +faststart "$W/small_hours_v2-1080p.mp4" >> "$W/v2.log" 2>&1
echo done >> "$W/v2.log"
