#!/bin/bash
# Waits for piece 2 v2 to finish (CPU), then renders Maintenance v1 with sound and a phone preview.
cd "$(dirname "$0")"
W='E:\Claude\music-video-2-work\04'
while ! grep -q done /e/Claude/music-video-2-work/02/v2.log 2>/dev/null; do sleep 60; done
python scene.py "$W\\maint_v1_video.mp4" > "$W\\v1.log" 2>&1
ffmpeg -v error -y -i "$W\\maint_v1_video.mp4" -i "$W\\maintenance.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W\\maint_v1.mp4" >> "$W\\v1.log" 2>&1
ffmpeg -v error -y -i "$W\\maint_v1.mp4" -vf scale=1280:720 -c:v libx264 -crf 26 -preset slow -threads 2 -c:a copy -movflags +faststart "$W\\maint_v1-phone.mp4" >> "$W\\v1.log" 2>&1
echo done >> "$W\\v1.log"
