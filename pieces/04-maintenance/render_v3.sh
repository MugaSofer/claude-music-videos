#!/bin/bash
# Maintenance v3: detailed gloves, pots, can, bench. Render, mux, phone preview.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/04'
python scene.py "$W/maint_v3_video.mp4" > "$W/v3.log" 2>&1
ffmpeg -v error -y -i "$W/maint_v3_video.mp4" -i "$W/maintenance.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/maint_v3.mp4" >> "$W/v3.log" 2>&1
ffmpeg -v error -y -i "$W/maint_v3.mp4" -vf scale=1280:720 -c:v libx264 -crf 26 -maxrate 1500k -bufsize 3000k -preset slow -threads 2 -c:a copy -movflags +faststart "$W/maint_v3-phone.mp4" >> "$W/v3.log" 2>&1
echo done >> "$W/v3.log"
