#!/bin/bash
# Transit Canon v2 (10-19): a mensuration canon. Every line sings one hand-written tune at its own speed (2:3:4:6),
# learning it phrase by phrase until all four meet at Central; the map inks itself as they learn. See design_v2.md.
# Chunked/resumable: re-run to resume after a kill.
cd "$(dirname "$0")"
W='E:/Claude/music-video-2-work/06'
python canon.py events > "$W/v2.log" 2>&1 && python film_v2.py pan >> "$W/v2.log" 2>&1 || exit 1
python render_audio.py "$W/transit_v2_raw.wav" events_v2.json >> "$W/v2.log" 2>&1 || exit 1
python ../../master.py "$W/transit_v2_raw.wav" "$W/transit_v2.wav" >> "$W/v2.log" 2>&1 || exit 1
TOTAL=$(python -c "import film_v2;print(film_v2.TOTAL)")
python ../../chunk_render.py --cmd "python film_v2.py video {out} {t0} {t1}" --cwd . --total $TOTAL \
    --work "$W/chunks_v2" --audio "$W/transit_v2.wav" --out "$W/transit_v2.mp4" >> "$W/v2.log" 2>&1 || exit 1
ffmpeg -v error -y -i "$W/transit_v2.mp4" -c:v libx264 -profile:v high -crf 20 -preset slow -threads 2 -pix_fmt yuv420p \
    -c:a copy -movflags +faststart "$W/transit_v2-1080p.mp4" >> "$W/v2.log" 2>&1 || exit 1
echo done >> "$W/v2.log"
