#!/bin/bash
# Piece 3 v3: same audio as v2 (tune_v2.wav), visuals with the clef moved before the pickup note.
cd "$(dirname "$0")"
W='E:\Claude\music-video-2-work\03'
python journey.py "$W\\journey_v3_video.mp4" > "$W\\v3.log" 2>&1
ffmpeg -v error -y -i "$W\\journey_v3_video.mp4" -i "$W\\tune_v2.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W\\journey_v3.mp4" >> "$W\\v3.log" 2>&1
ffmpeg -v error -y -i "$W\\journey_v3.mp4" -vf scale=1280:720 -c:v libx264 -crf 26 -preset slow -threads 2 -c:a copy -movflags +faststart "$W\\journey_v3-phone.mp4" >> "$W\\v3.log" 2>&1
echo done >> "$W\\v3.log"
