#!/bin/bash
# Relay v2: Salamander piano, mastered audio, seed played once, title card, larger captions, softer Gemini line.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/07'
python film.py smoke x > "$W/v2.log" 2>&1 || { echo "SMOKE FAILED" >> "$W/v2.log"; exit 1; }
python film.py video "$W/relay_v2_video.mp4" >> "$W/v2.log" 2>&1
ffmpeg -v error -y -i "$W/relay_v2_video.mp4" -i "$W/relay_v2.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/relay_v2.mp4" >> "$W/v2.log" 2>&1
ffmpeg -v error -y -i "$W/relay_v2.mp4" -vf scale=1280:720 -c:v libx264 -crf 29 -maxrate 1000k -bufsize 2000k -preset slow -threads 2 -c:a aac -b:a 160k -movflags +faststart "$W/relay_v2-phone.mp4" >> "$W/v2.log" 2>&1
echo done >> "$W/v2.log"
