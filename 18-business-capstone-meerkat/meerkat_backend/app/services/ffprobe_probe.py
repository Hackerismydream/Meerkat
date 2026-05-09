from __future__ import annotations

import asyncio
import json
from time import perf_counter
from typing import Any


async def probe_ffprobe_stream(media_url: str) -> dict[str, Any]:
    started = perf_counter()
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            media_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
    except FileNotFoundError:
        return {"probe_type": "FFPROBE", "status": "SKIPPED", "duration_ms": 0, "video_present": None, "audio_present": None, "error": "ffprobe not installed"}
    except Exception as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        return {"probe_type": "FFPROBE", "status": "FAILED", "duration_ms": duration_ms, "video_present": None, "audio_present": None, "error": f"{media_url}: {exc}"}

    duration_ms = int((perf_counter() - started) * 1000)
    if process.returncode != 0:
        return {
            "probe_type": "FFPROBE",
            "status": "FAILED",
            "duration_ms": duration_ms,
            "video_present": None,
            "audio_present": None,
            "error": f"{media_url}: {stderr.decode(errors='replace').strip()}",
        }
    payload = json.loads(stdout.decode() or "{}")
    streams = payload.get("streams", [])
    return {
        "probe_type": "FFPROBE",
        "status": "OK",
        "duration_ms": duration_ms,
        "video_present": any(stream.get("codec_type") == "video" for stream in streams),
        "audio_present": any(stream.get("codec_type") == "audio" for stream in streams),
        "error": None,
    }
