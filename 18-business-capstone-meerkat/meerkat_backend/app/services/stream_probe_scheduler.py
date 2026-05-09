from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AlertSeverity, AlertType, LiveSessionStatus
from app.db.base import LiveSession, StreamHealthSample, StreamIncident, StreamProbeJob, StreamProbeRun, utcnow
from app.services.agent_task_service import create_agent_task, run_agent_task
from app.services.ffprobe_probe import probe_ffprobe_stream
from app.services.hls_probe import probe_hls_playlist
from app.services.owncast_status_probe import probe_owncast_status
from app.services.serialization import dumps, model_to_dict


async def start_probe_job(
    db: AsyncSession,
    *,
    session_id: int,
    probe_interval_seconds: int = 10,
    failure_threshold: int = 3,
    recovery_threshold: int = 3,
) -> dict[str, Any]:
    job = await _get_job(db, session_id)
    if job is None:
        job = StreamProbeJob(
            session_id=session_id,
            status="RUNNING",
            probe_interval_seconds=probe_interval_seconds,
            failure_threshold=failure_threshold,
            recovery_threshold=recovery_threshold,
            created_by="api",
        )
        db.add(job)
    else:
        job.status = "RUNNING"
        job.stopped_at = None
        job.probe_interval_seconds = probe_interval_seconds
        job.failure_threshold = failure_threshold
        job.recovery_threshold = recovery_threshold
    await db.commit()
    return model_to_dict(job)


async def stop_probe_job(db: AsyncSession, *, session_id: int) -> dict[str, Any]:
    job = await _get_job(db, session_id)
    if job is None:
        job = StreamProbeJob(session_id=session_id, status="STOPPED", stopped_at=utcnow(), created_by="api")
        db.add(job)
    job.status = "STOPPED"
    job.stopped_at = utcnow()
    await db.commit()
    return model_to_dict(job)


async def list_probe_jobs(db: AsyncSession) -> dict[str, Any]:
    jobs = list((await db.scalars(select(StreamProbeJob).order_by(StreamProbeJob.id.desc()))).all())
    return {"items": [model_to_dict(job) for job in jobs]}


async def tick_probe_job(db: AsyncSession, *, session_id: int) -> dict[str, Any]:
    job = await _get_job(db, session_id)
    if job is None or job.status != "RUNNING":
        await start_probe_job(db, session_id=session_id)
        job = await _get_job(db, session_id)
    assert job is not None
    owncast = await probe_owncast_status(settings.owncast_base_url)
    hls = await probe_hls_playlist(settings.hls_playlist_url)
    ffprobe = await probe_ffprobe_stream(settings.hls_playlist_url) if hls["status"] == "OK" else {"status": "SKIPPED", "video_present": None, "audio_present": None, "error": "HLS probe failed"}
    now = utcnow()
    previous = await db.scalar(select(StreamHealthSample).where(StreamHealthSample.session_id == session_id).order_by(StreamHealthSample.id.desc()).limit(1))
    failed = owncast["status"] == "FAILED" or hls["status"] == "FAILED"
    probe_error = "; ".join(str(item["error"]) for item in [owncast, hls, ffprobe] if item.get("error") and item.get("status") == "FAILED") or None
    last_segment_age_ms = hls.get("last_segment_age_ms")
    if previous and previous.playlist_hash == hls.get("playlist_hash") and previous.last_segment_uri == hls.get("last_segment_uri") and hls.get("target_duration_ms"):
        previous_sampled_at = previous.sampled_at if previous.sampled_at.tzinfo else previous.sampled_at.replace(tzinfo=timezone.utc)
        last_segment_age_ms = int((now - previous_sampled_at).total_seconds() * 1000)
        if last_segment_age_ms > int(hls["target_duration_ms"]) * 3:
            failed = True
            probe_error = probe_error or "HLS playlist segment stalled"
    run = StreamProbeRun(
        session_id=session_id,
        probe_type="OWNCAST_HLS_FFPROBE",
        status="FAILED" if failed else "OK",
        error_message=probe_error,
        started_at=now,
        finished_at=now,
        duration_ms=int(owncast.get("duration_ms", 0)) + int(hls.get("duration_ms", 0)) + int(ffprobe.get("duration_ms", 0) or 0),
    )
    db.add(run)
    await db.flush()
    sample = StreamHealthSample(
        session_id=session_id,
        probe_run_id=run.id,
        is_live=bool(owncast.get("is_live")) and not failed,
        video_present=True if failed or ffprobe.get("video_present") is None else bool(ffprobe.get("video_present")),
        audio_present=True if failed or ffprobe.get("audio_present") is None else bool(ffprobe.get("audio_present")),
        last_segment_age_ms=last_segment_age_ms,
        last_segment_uri=hls.get("last_segment_uri"),
        playlist_hash=hls.get("playlist_hash"),
        probe_status="FAILED" if failed else "OK",
        probe_error=probe_error,
        sampled_at=now,
    )
    db.add(sample)
    job.last_tick_at = now
    await db.flush()
    incident = await update_stream_incident_lifecycle(db, session_id=session_id, job=job, sample=sample)
    await db.commit()
    return {
        "job": model_to_dict(job),
        "sample": model_to_dict(sample),
        "incident": model_to_dict(incident) if incident else None,
        "probe": {"owncast": owncast, "hls": hls, "ffprobe": ffprobe},
    }


async def update_stream_incident_lifecycle(db: AsyncSession, *, session_id: int, job: StreamProbeJob, sample: StreamHealthSample) -> StreamIncident | None:
    incident = await db.scalar(
        select(StreamIncident)
        .where(StreamIncident.session_id == session_id, StreamIncident.incident_type.in_([AlertType.STREAM_INTERRUPTED.value, AlertType.STREAM_UNAVAILABLE.value, AlertType.SEGMENT_STALLED.value]), StreamIncident.status.in_(["OPEN", "RECOVERING"]))
        .order_by(StreamIncident.id.desc())
        .limit(1)
    )
    recent = list((await db.scalars(select(StreamHealthSample).where(StreamHealthSample.session_id == session_id).order_by(StreamHealthSample.id.desc()).limit(max(job.failure_threshold, job.recovery_threshold)))).all())
    failure_count = sum(1 for item in recent[: job.failure_threshold] if item.probe_status == "FAILED")
    recovery_count = sum(1 for item in recent[: job.recovery_threshold] if item.probe_status == "OK" and item.audio_present and item.video_present)
    if incident is None and failure_count >= job.failure_threshold:
        live_session = await db.get(LiveSession, session_id)
        incident_type = AlertType.STREAM_INTERRUPTED.value if live_session and live_session.status == LiveSessionStatus.LIVE.value else AlertType.STREAM_UNAVAILABLE.value
        if sample.probe_error and "stalled" in sample.probe_error:
            incident_type = AlertType.SEGMENT_STALLED.value
        incident = StreamIncident(
            session_id=session_id,
            incident_type=incident_type,
            severity=AlertSeverity.P1.value,
            status="OPEN",
            opened_at=utcnow(),
            last_seen_at=utcnow(),
            dedupe_key=f"stream:{session_id}:{incident_type}",
            failure_count=failure_count,
            recovery_count=0,
            evidence_json=dumps({"sample_ids": [item.id for item in recent]}),
            created_by="STREAM_PROBE",
        )
        db.add(incident)
        await db.flush()
        task = await create_agent_task(
            db,
            session_id=session_id,
            source="STREAM_PROBE",
            task_type="STREAM_HEALTH_ANALYSIS",
            alert_type_hint=incident_type,
            input_payload={"stream_incident_id": incident.id, "scenario": "probe_loop"},
        )
        incident.trace_id = task.trace_id
        await run_agent_task(db, task.id)
        return incident
    if incident is not None:
        incident.last_seen_at = utcnow()
        incident.failure_count = failure_count
        incident.recovery_count = recovery_count
        if recovery_count >= job.recovery_threshold:
            incident.status = "RECOVERED"
            incident.recovered_at = utcnow()
            incident.resolved_at = utcnow()
    return incident


async def resolve_stream_incident(db: AsyncSession, incident_id: int) -> dict[str, Any] | None:
    incident = await db.get(StreamIncident, incident_id)
    if incident is None:
        return None
    incident.status = "RESOLVED"
    incident.resolved_at = utcnow()
    await db.commit()
    return model_to_dict(incident)


async def _get_job(db: AsyncSession, session_id: int) -> StreamProbeJob | None:
    return await db.scalar(select(StreamProbeJob).where(StreamProbeJob.session_id == session_id).order_by(StreamProbeJob.id.desc()).limit(1))
