#!/bin/bash
# Signal v2: 120 bpm (2:30), words lift whole then scatter, bigger boat, title card, beams meet at GOODNIGHT, Salamander boat voice, mastered.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/11'
python film.py smoke x > "$W/v2.log" 2>&1 || { echo "SMOKE FAILED" >> "$W/v2.log"; exit 1; }
python film.py video "$W/signal_v2_video.mp4" >> "$W/v2.log" 2>&1
ffmpeg -v error -y -i "$W/signal_v2_video.mp4" -i "$W/signal_v2.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$W/signal_v2.mp4" >> "$W/v2.log" 2>&1
ffmpeg -v error -y -i "$W/signal_v2.mp4" -vf scale=1280:720 -c:v libx264 -crf 29 -maxrate 1000k -bufsize 2000k -preset slow -threads 2 -c:a aac -b:a 160k -movflags +faststart "$W/signal_v2-phone.mp4" >> "$W/v2.log" 2>&1
echo done >> "$W/v2.log"
