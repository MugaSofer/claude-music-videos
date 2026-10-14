#!/bin/bash
# Piece 6 sync test: 108-128 s (the approach and the meeting), muxed with the matching audio.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/06'
python film.py video "$W/test_video.mp4" 108 128 > "$W/test.log" 2>&1
ffmpeg -v error -y -i "$W/test_video.mp4" -ss 108 -t 20 -i "$W/transit.wav" -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart "$W/test_clip.mp4" >> "$W/test.log" 2>&1
echo done >> "$W/test.log"
