#!/usr/bin/env bash
set -euo pipefail

STREAM_KEY="${1:-abc123}"
ffmpeg -re \
  -f lavfi -i testsrc=size=1280x720:rate=30 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -c:v libx264 -preset veryfast -b:v 2500k -g 60 \
  -c:a aac -b:a 128k \
  -f flv "rtmp://127.0.0.1/live/${STREAM_KEY}"
