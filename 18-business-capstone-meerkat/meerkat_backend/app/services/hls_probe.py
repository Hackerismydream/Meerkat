from __future__ import annotations

from time import perf_counter
from typing import Any
import hashlib

import httpx


async def probe_hls_playlist(playlist_url: str) -> dict[str, Any]:
    started = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(playlist_url)
        duration_ms = int((perf_counter() - started) * 1000)
        body = response.text
        if response.status_code != 200 or "#EXTM3U" not in body:
            return {
                "probe_type": "HLS_PLAYLIST",
                "status": "FAILED",
                "duration_ms": duration_ms,
                "last_segment_age_ms": None,
                "error": f"{playlist_url}: unexpected playlist response {response.status_code}",
            }
        parsed = parse_hls_playlist(body)
        return {
            "probe_type": "HLS_PLAYLIST",
            "status": "OK",
            "duration_ms": duration_ms,
            **parsed,
            "error": None,
        }
    except Exception as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        return {
            "probe_type": "HLS_PLAYLIST",
            "status": "FAILED",
            "duration_ms": duration_ms,
            "last_segment_age_ms": None,
            "error": f"{playlist_url}: {exc}",
        }


def parse_hls_playlist(body: str) -> dict[str, Any]:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    target_duration_ms: int | None = None
    media_sequence: int | None = None
    segments: list[str] = []
    for line in lines:
        if line.startswith("#EXT-X-TARGETDURATION:"):
            target_duration_ms = int(float(line.split(":", 1)[1]) * 1000)
        elif line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            media_sequence = int(line.split(":", 1)[1])
        elif not line.startswith("#"):
            segments.append(line)
    playlist_hash = "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()
    return {
        "playlist_hash": playlist_hash,
        "last_segment_uri": segments[-1] if segments else None,
        "last_segment_age_ms": 0,
        "target_duration_ms": target_duration_ms,
        "media_sequence": media_sequence,
    }
