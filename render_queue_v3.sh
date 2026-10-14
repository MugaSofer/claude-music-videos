#!/bin/bash
# Queue after Small Hours v2: Relay v3, then Maintenance v4. Each is chunked and resumable.
cd "$(dirname "$0")"
bash pieces/07-relay/render_v3.sh
bash pieces/04-maintenance/render_v4.sh
echo queue v3 done > E:/Claude/music-video-2-work/queue_v3.log
