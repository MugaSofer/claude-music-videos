#!/bin/bash
# Small Hours v5 (Muga's close-watch notes, 10-16): the baker has a seat behind the counter and his cap no longer
# gaps from its band; the indoor keepers run on one clock all film (no 8 s loop jump); the nurse shot sits a
# little higher so the fox isn't seen appearing; the lorry's road-edge light pool stops at the terrace wall too;
# the moon fades by blending instead of cutting a hole in the dawn sky. These touch the whole film, so it is
# rendered whole, in resumable 20 s chunks (re-run this script to resume after a kill).
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/05'
python ../../chunk_render.py --cmd "python film.py $W/sectionsB.json {out} {t0} {t1}" --cwd . --total 170 \
    --work "$W/chunks_v5" --audio "$W/takeB.wav" --out "$W/small_hours_v5.mp4" > "$W/v5.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/small_hours_v5.mp4" -c:v libx264 -profile:v high -crf 20 -preset slow -threads 2 -pix_fmt yuv420p \
    -c:a copy -movflags +faststart "$W/small_hours_v5-1080p.mp4" >> "$W/v5.log" 2>&1 || exit 1
echo done >> "$W/v5.log"
