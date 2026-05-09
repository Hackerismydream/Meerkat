from __future__ import annotations

from time import perf_counter
from typing import Any

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
        return {
            "probe_type": "HLS_PLAYLIST",
            "status": "OK",
            "duration_ms": duration_ms,
            "last_segment_age_ms": 0,
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
