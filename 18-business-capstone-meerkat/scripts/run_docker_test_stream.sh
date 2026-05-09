#!/usr/bin/env bash
set -euo pipefail

STREAM_KEY="${1:-abc123}"
STREAM_NAME="${MEERKAT_STREAM_CONTAINER:-meerkat-test-stream}"
NETWORK="${MEERKAT_DOCKER_NETWORK:-18-business-capstone-meerkat_default}"
RTMP_URL="${MEERKAT_RTMP_URL:-rtmp://owncast/live/${STREAM_KEY}}"
IMAGE="${MEERKAT_FFMPEG_IMAGE:-linuxserver/ffmpeg:latest}"

docker rm -f "${STREAM_NAME}" >/dev/null 2>&1 || true
docker run -d \
  --name "${STREAM_NAME}" \
  --rm \
  --network "${NETWORK}" \
  "${IMAGE}" \
  -re \
  -f lavfi -i testsrc=size=1280x720:rate=30 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -c:v libx264 -preset veryfast -b:v 2500k -g 60 \
  -c:a aac -b:a 128k \
  -f flv "${RTMP_URL}"

echo "started ${STREAM_NAME} -> ${RTMP_URL}"
