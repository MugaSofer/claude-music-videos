#!/bin/bash
# Waits for Murmuration v2b to finish, then renders Signal v3.
until grep -q '^done' E:/Claude/music-video-2-work/13/v2b.log 2>/dev/null; do sleep 60; done
bash "$(dirname "$0")/pieces/11-signal/render_v3.sh"
