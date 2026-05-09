from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import LiveComment
from app.schemas import SimulationComment
from app.services.agent_task_service import create_agent_task, run_agent_task
from app.services.anomaly_detector import detect_after_comment
from app.services.comment_classifier import CommentClassifier, normalize_text


async def insert_comment(db: AsyncSession, *, session_id: int, comment: SimulationComment, owncast_event_id: int | None = None) -> LiveComment:
    classifier = CommentClassifier()
    matched = classifier.classify(comment.body)
    live_comment = LiveComment(
        session_id=session_id,
        owncast_event_id=owncast_event_id,
        external_message_id=comment.external_message_id,
        user_name=comment.user_name,
        user_external_id=comment.user_external_id,
        body=comment.body,
        normalized_body=normalize_text(comment.body),
        matched_type=matched.value if matched else None,
    )
    db.add(live_comment)
    await db.flush()
    return live_comment


async def insert_comments_and_run_agent(
    db: AsyncSession,
    *,
    session_id: int,
    comments: list[SimulationComment],
    source: str = "simulation",
    owncast_event_ids: list[int | None] | None = None,
) -> dict:
    inserted = 0
    runs: list[dict] = []
    for index, comment in enumerate(comments):
        owncast_event_id = owncast_event_ids[index] if owncast_event_ids and index < len(owncast_event_ids) else None
        live_comment = await insert_comment(db, session_id=session_id, comment=comment, owncast_event_id=owncast_event_id)
        inserted += 1
        anomalies = await detect_after_comment(session_id, live_comment.id, db)
        for anomaly in anomalies:
            task = await create_agent_task(
                db,
                session_id=anomaly.session_id,
                source=source,
                alert_type_hint=anomaly.alert_type,
                comment_ids=anomaly.comment_ids,
                input_payload={
                    "reason": anomaly.reason,
                    "severity": anomaly.severity.value,
                    "product_id": anomaly.product_id,
                    "coupon_id": anomaly.coupon_id,
                },
            )
            runs.append(await run_agent_task(db, task.id))
    return {
        "inserted": inserted,
        "agent_runs_triggered": len(runs),
        "alerts_created": sum(1 for run in runs if run.get("alert_created")),
        "trace_id": runs[-1]["trace_id"] if runs else None,
        "agent_run_id": runs[-1]["run_id"] if runs else None,
    }
