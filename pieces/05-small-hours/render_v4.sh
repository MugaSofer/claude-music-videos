#!/bin/bash
# Small Hours v4: the lorry's headlight beam is clipped at the dad's terrace (its far end used to be painted over
# the neighbour's brick wall as the camera panned on, ~67-70 s; Muga, 10-16). Re-render the lorry segment
# 48.5-74 s and splice it, with v3's 27-38 s segment, into v2's picture by frame, exactly as v3 did.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/05'
python film.py "$W/sectionsB.json" "$W/seg_v4b.mp4" 48.5 74 > "$W/v4.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/chunks_v2/joined.mp4" -i "$W/seg_v3a.mp4" -i "$W/seg_v4b.mp4" -i "$W/takeB.wav" -filter_complex \
  "[0:v]trim=start_frame=0:end_frame=648,setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[0:v]trim=start_frame=912:end_frame=1164,setpts=PTS-STARTPTS[c];[2:v]setpts=PTS-STARTPTS[d];[0:v]trim=start_frame=1776,setpts=PTS-STARTPTS[e];[a][b][c][d][e]concat=n=5:v=1:a=0[v]" \
  -map "[v]" -map 3:a -c:v libx264 -profile:v high -crf 20 -preset slow -threads 2 -pix_fmt yuv420p -c:a aac -b:a 256k -shortest -movflags +faststart \
  "$W/small_hours_v4-1080p.mp4" >> "$W/v4.log" 2>&1 || exit 1
echo done >> "$W/v4.log"
