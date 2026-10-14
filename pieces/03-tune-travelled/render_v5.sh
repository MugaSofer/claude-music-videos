#!/bin/bash
# Piece 3 v5: the real hum (realhum.py, tune_v5.wav) and the redrawn parlour (piano_art.py).
# Only the parlour changed visually, so re-render 76-116 s and splice it into v4's picture by frame number.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/03'
python journey.py "$W/parlour_v5.mp4" 76 116 > "$W/v5.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/journey_v4_video.mp4" -i "$W/parlour_v5.mp4" -i "$W/tune_v5.wav" -filter_complex \
  "[0:v]trim=start_frame=0:end_frame=2280,setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[0:v]trim=start_frame=3480,setpts=PTS-STARTPTS[c];[a][b][c]concat=n=3:v=1:a=0[v]" \
  -map "[v]" -map 2:a -c:v libx264 -crf 20 -preset slow -threads 2 -pix_fmt yuv420p -c:a aac -b:a 256k -shortest -movflags +faststart \
  "$W/journey_v5-1080p.mp4" >> "$W/v5.log" 2>&1
echo done >> "$W/v5.log"
