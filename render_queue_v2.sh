#!/bin/bash
# After Small Hours: render Relay v2, then Signal v2 (one at a time).
cd "$(dirname "$0")"
bash pieces/07-relay/render_v2.sh
bash pieces/11-signal/render_v2.sh
echo queue done > E:/Claude/music-video-2-work/queue_v2.log
