from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas import StreamHealthSampleInput
from app.services.ffprobe_probe import probe_ffprobe_stream
from app.services.hls_probe import probe_hls_playlist
from app.services.owncast_status_probe import probe_owncast_status
from app.services.stream_health_service import simulate_stream_health


async def run_stream_probe_once(
    db: AsyncSession,
    *,
    session_id: int,
    owncast_base_url: str | None = None,
    hls_playlist_url: str | None = None,
) -> dict[str, Any]:
    base_url = owncast_base_url or settings.owncast_base_url
    playlist_url = hls_playlist_url or settings.hls_playlist_url
    owncast = await probe_owncast_status(base_url)
    hls = await probe_hls_playlist(playlist_url)
    ffprobe = await probe_ffprobe_stream(playlist_url) if hls["status"] == "OK" else {"status": "SKIPPED", "video_present": None, "audio_present": None, "error": "HLS probe failed"}
    failed = owncast["status"] == "FAILED" or hls["status"] == "FAILED"
    error = "; ".join(str(item["error"]) for item in [owncast, hls] if item.get("error")) or None
    video_present = True if failed or ffprobe.get("video_present") is None else bool(ffprobe.get("video_present"))
    audio_present = True if failed or ffprobe.get("audio_present") is None else bool(ffprobe.get("audio_present"))
    sample = StreamHealthSampleInput(
        is_live=bool(owncast.get("is_live")) and not failed,
        video_present=video_present,
        audio_present=audio_present,
        last_segment_age_ms=hls.get("last_segment_age_ms"),
        last_segment_uri=hls.get("last_segment_uri"),
        playlist_hash=hls.get("playlist_hash"),
        probe_status="FAILED" if failed else "OK",
        probe_error=error,
    )
    samples = [sample, sample, sample] if failed else [sample]
    result = await simulate_stream_health(db, session_id=session_id, scenario="stream_probe_run_once", samples=samples)
    return {"probe": {"owncast": owncast, "hls": hls, "ffprobe": ffprobe}, **result}
