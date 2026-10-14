#!/bin/bash
# Small Hours v3: the lorry is parked on the flyover from the start and pulls away on its verse (no pop-in),
# and its beam stops at the end of the flyover (it used to shine across the dad's house). Only the frames where
# the lorry can be seen changed, so re-render 27-38 s and 48.5-74 s and splice them into v2's picture by frame.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/05'
python film.py "$W/sectionsB.json" "$W/seg_v3a.mp4" 27 38 > "$W/v3.log" 2>&1 || exit 1
python film.py "$W/sectionsB.json" "$W/seg_v3b.mp4" 48.5 74 >> "$W/v3.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/chunks_v2/joined.mp4" -i "$W/seg_v3a.mp4" -i "$W/seg_v3b.mp4" -i "$W/takeB.wav" -filter_complex \
  "[0:v]trim=start_frame=0:end_frame=648,setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[0:v]trim=start_frame=912:end_frame=1164,setpts=PTS-STARTPTS[c];[2:v]setpts=PTS-STARTPTS[d];[0:v]trim=start_frame=1776,setpts=PTS-STARTPTS[e];[a][b][c][d][e]concat=n=5:v=1:a=0[v]" \
  -map "[v]" -map 3:a -c:v libx264 -crf 20 -preset slow -threads 2 -pix_fmt yuv420p -c:a aac -b:a 256k -shortest -movflags +faststart \
  "$W/small_hours_v3-1080p.mp4" >> "$W/v3.log" 2>&1
echo done >> "$W/v3.log"
