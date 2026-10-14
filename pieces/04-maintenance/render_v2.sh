#!/bin/bash
# Maintenance v2: render, mux, phone preview.
cd "$(dirname "$0")"
W='E:\Claude\music-video-2-work\04'
python scene.py "$W\\maint_v2_video.mp4" > "$W\\v2.log" 2>&1
ffmpeg -v error -y -i "$W\\maint_v2_video.mp4" -i "$W\\maintenance.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W\\maint_v2.mp4" >> "$W\\v2.log" 2>&1
ffmpeg -v error -y -i "$W\\maint_v2.mp4" -vf scale=1280:720 -c:v libx264 -crf 26 -preset slow -threads 2 -c:a copy -movflags +faststart "$W\\maint_v2-phone.mp4" >> "$W\\v2.log" 2>&1
echo done >> "$W\\v2.log"
