from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LiveSessionStatus
from app.db.base import LiveSession, OwncastEvent
from app.schemas import SimulationComment, StreamHealthSampleInput
from app.services.serialization import dumps
from app.services.simulation_service import insert_comments_and_run_agent
from app.services.stream_health_service import simulate_stream_health


def get_payload_type(payload: dict) -> str:
    return str(payload.get("type") or payload.get("eventType") or payload.get("event") or "UNKNOWN").upper()


def get_event_data(payload: dict) -> dict:
    data = payload.get("eventData") or payload.get("data") or payload
    return data if isinstance(data, dict) else {}


async def ensure_live_session(db: AsyncSession) -> LiveSession:
    live_session = await db.scalar(select(LiveSession).where(LiveSession.id == 1))
    if live_session:
        return live_session
    live_session = LiveSession(id=1, title="Owncast Live", status=LiveSessionStatus.LIVE.value, started_at=datetime.now(timezone.utc))
    db.add(live_session)
    await db.flush()
    return live_session


async def handle(payload: dict, *, session: AsyncSession) -> dict:
    event_type = get_payload_type(payload)
    event = OwncastEvent(event_type=event_type, raw_payload_json=dumps(payload), processed=False)
    session.add(event)
    await session.flush()
    live_session = await ensure_live_session(session)

    if event_type == "CHAT":
        data = get_event_data(payload)
        user = data.get("user") if isinstance(data.get("user"), dict) else {}
        body = str(data.get("body") or data.get("message") or "")
        user_name = str(user.get("displayName") or user.get("name") or data.get("userName") or "owncast-viewer")
        external_message_id = str(data.get("id") or data.get("messageId") or data.get("eventId") or event.id)
        user_external_id = str(user.get("id") or user.get("userId") or data.get("userId") or "") or None
        result = await insert_comments_and_run_agent(
            session,
            session_id=live_session.id,
            comments=[
                SimulationComment(
                    user_name=user_name,
                    user_external_id=user_external_id,
                    external_message_id=external_message_id,
                    body=body,
                )
            ],
            source="owncast",
            owncast_event_ids=[event.id],
        )
    elif event_type == "STREAM_STARTED":
        live_session.status = LiveSessionStatus.LIVE.value
        live_session.started_at = datetime.now(timezone.utc)
        result = await simulate_stream_health(
            session,
            session_id=live_session.id,
            scenario="stream_started",
            samples=[StreamHealthSampleInput(is_live=True, probe_status="OK")],
        )
    elif event_type == "STREAM_STOPPED":
        result = await simulate_stream_health(
            session,
            session_id=live_session.id,
            scenario="stream_down",
            samples=[
                StreamHealthSampleInput(is_live=False, probe_status="FAILED", probe_error="Owncast STREAM_STOPPED"),
                StreamHealthSampleInput(is_live=False, probe_status="FAILED", probe_error="Owncast STREAM_STOPPED"),
                StreamHealthSampleInput(is_live=False, probe_status="FAILED", probe_error="Owncast STREAM_STOPPED"),
            ],
        )
    else:
        result = {"agent_runs_triggered": 0}

    event.processed = True
    await session.commit()
    return {"event_id": event.id, **result}
