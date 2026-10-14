#!/bin/bash
# Piece 3 v2: re-arrange audio (kitchen trimmed), re-render the journey, mux, phone preview.
cd "$(dirname "$0")"
W='E:\Claude\music-video-2-work\03'
python arrange.py > "$W\\v2.log" 2>&1
cp /e/Claude/music-video-2-work/03/tune.wav /e/Claude/music-video-2-work/03/tune_v2.wav
python journey.py "$W\\journey_v2_video.mp4" >> "$W\\v2.log" 2>&1
ffmpeg -v error -y -i "$W\\journey_v2_video.mp4" -i "$W\\tune_v2.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W\\journey_v2.mp4" >> "$W\\v2.log" 2>&1
ffmpeg -v error -y -i "$W\\journey_v2.mp4" -vf scale=1280:720 -c:v libx264 -crf 26 -preset slow -threads 2 -c:a copy -movflags +faststart "$W\\journey_v2-phone.mp4" >> "$W\\v2.log" 2>&1
echo done >> "$W\\v2.log"
