from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AlertSeverity, AlertType, LiveSessionStatus
from app.db.base import LiveSession, StreamHealthSample, StreamIncident, StreamProbeRun, utcnow
from app.schemas import StreamHealthSampleInput
from app.services.agent_task_service import create_agent_task, run_agent_task
from app.services.serialization import dumps, model_to_dict


def classify_stream_incident(samples: list[StreamHealthSample], session_status: str) -> str | None:
    if not samples:
        return None
    if any(sample.probe_status == "RECOVERED" for sample in samples):
        return AlertType.STREAM_RECOVERED.value
    if any(sample.audio_present is False for sample in samples):
        return AlertType.NO_AUDIO.value
    if any(sample.video_present is False for sample in samples):
        return AlertType.NO_VIDEO.value
    if any((sample.last_segment_age_ms or 0) >= 10000 for sample in samples):
        return AlertType.SEGMENT_STALLED.value
    if sum(1 for sample in samples if sample.probe_status == "FAILED") >= 3 and session_status == LiveSessionStatus.LIVE.value:
        return AlertType.STREAM_INTERRUPTED.value
    if sum(1 for sample in samples if sample.probe_status == "FAILED") >= 3:
        return AlertType.STREAM_UNAVAILABLE.value
    if any((sample.bitrate_kbps or 999999) < 500 for sample in samples):
        return AlertType.BITRATE_DROP.value
    return None


async def simulate_stream_health(
    db: AsyncSession,
    *,
    session_id: int,
    scenario: str,
    samples: list[StreamHealthSampleInput],
) -> dict[str, Any]:
    live_session = await db.get(LiveSession, session_id)
    if live_session is None:
        raise ValueError(f"live session {session_id} not found")

    persisted: list[StreamHealthSample] = []
    for index, sample in enumerate(samples or _default_samples_for(scenario), start=1):
        run = StreamProbeRun(
            session_id=session_id,
            probe_type="MOCK_FFPROBE" if scenario in {"no_audio", "no_video"} else "HLS",
            status=sample.probe_status,
            error_message=sample.probe_error,
            duration_ms=20 + index,
        )
        db.add(run)
        await db.flush()
        health = StreamHealthSample(
            session_id=session_id,
            probe_run_id=run.id,
            is_live=sample.is_live,
            video_present=sample.video_present,
            audio_present=sample.audio_present,
            bitrate_kbps=sample.bitrate_kbps,
            fps=sample.fps,
            width=sample.width,
            height=sample.height,
            last_segment_age_ms=sample.last_segment_age_ms,
            last_segment_uri=getattr(sample, "last_segment_uri", None),
            playlist_hash=getattr(sample, "playlist_hash", None),
            probe_status=sample.probe_status,
            probe_error=sample.probe_error,
        )
        db.add(health)
        persisted.append(health)
    await db.flush()

    if scenario == "stream_recover":
        incident = await db.scalar(
            select(StreamIncident)
            .where(
                StreamIncident.session_id == session_id,
                StreamIncident.status.in_(["OPEN", "RECOVERING"]),
            )
            .order_by(StreamIncident.id.desc())
            .limit(1)
        )
        if incident is not None:
            incident.status = "RECOVERED"
            incident.recovered_at = utcnow()
            incident.resolved_at = utcnow()
            incident.last_seen_at = utcnow()
            incident.recovery_count = sum(1 for sample in persisted if sample.probe_status in {"OK", "RECOVERED"} and sample.audio_present and sample.video_present)
            await db.commit()
            return {
                "incident_created": False,
                "incident_recovered": True,
                "samples_created": len(persisted),
                "stream_incident": model_to_dict(incident),
                "trace_id": incident.trace_id,
            }

    incident_type = classify_stream_incident(persisted, live_session.status)
    if incident_type is None:
        await db.commit()
        return {"incident_created": False, "samples_created": len(persisted), "trace_id": None}

    incident = StreamIncident(
        session_id=session_id,
        incident_type=incident_type,
        severity=AlertSeverity.P1.value,
        status="OPEN",
        opened_at=utcnow(),
        last_seen_at=utcnow(),
        dedupe_key=f"stream:{session_id}:{incident_type}",
        failure_count=sum(1 for sample in persisted if sample.probe_status == "FAILED"),
        recovery_count=sum(1 for sample in persisted if sample.probe_status in {"OK", "RECOVERED"}),
        evidence_json=dumps({"scenario": scenario, "sample_ids": [sample.id for sample in persisted]}),
        created_by="SYSTEM",
    )
    db.add(incident)
    await db.flush()

    task = await create_agent_task(
        db,
        session_id=session_id,
        source="STREAM_PROBE",
        task_type="STREAM_HEALTH_ANALYSIS",
        alert_type_hint=incident_type,
        input_payload={"stream_incident_id": incident.id, "scenario": scenario},
    )
    incident.trace_id = task.trace_id
    run_result = await run_agent_task(db, task.id)
    await db.commit()

    return {
        "incident_created": True,
        "incident_type": incident_type,
        "samples_created": len(persisted),
        "stream_incident": model_to_dict(incident),
        "trace_id": task.trace_id,
        **run_result,
    }


async def get_stream_incident_context(db: AsyncSession, incident_id: int) -> dict[str, Any]:
    incident = await db.get(StreamIncident, incident_id)
    if incident is None:
        return {"error": "stream_incident_not_found", "stream_incident_id": incident_id}
    samples = list(
        (
            await db.scalars(
                select(StreamHealthSample)
                .where(StreamHealthSample.session_id == incident.session_id)
                .order_by(StreamHealthSample.id.desc())
                .limit(5)
            )
        ).all()
    )
    return {"incident": model_to_dict(incident), "recent_samples": [model_to_dict(sample) for sample in samples]}


def _default_samples_for(scenario: str) -> list[StreamHealthSampleInput]:
    if scenario == "no_audio":
        return [StreamHealthSampleInput(is_live=True, audio_present=False, probe_status="OK")]
    if scenario == "segment_stalled":
        return [StreamHealthSampleInput(is_live=True, last_segment_age_ms=15000, probe_status="OK")]
    if scenario == "stream_recover":
        return [StreamHealthSampleInput(is_live=True, probe_status="RECOVERED")]
    return [
        StreamHealthSampleInput(is_live=False, probe_status="FAILED", probe_error="HLS playlist unavailable"),
        StreamHealthSampleInput(is_live=False, probe_status="FAILED", probe_error="HLS playlist unavailable"),
        StreamHealthSampleInput(is_live=False, probe_status="FAILED", probe_error="HLS playlist unavailable"),
    ]
