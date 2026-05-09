from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AlertSeverity, AlertType
from app.db.base import CommentCluster, LiveComment
from app.schemas import SimulationComment
from app.services.agent_task_service import create_agent_task, run_agent_task
from app.services.anomaly_detector import detect_after_comment, has_open_alert, resolve_product_id
from app.services.comment_classifier import CommentClassifier, normalize_text
from app.services.serialization import dumps


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
    inserted_comments: list[LiveComment] = []
    for index, comment in enumerate(comments):
        owncast_event_id = owncast_event_ids[index] if owncast_event_ids and index < len(owncast_event_ids) else None
        live_comment = await insert_comment(db, session_id=session_id, comment=comment, owncast_event_id=owncast_event_id)
        inserted_comments.append(live_comment)
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
    runs.extend(await _run_mixed_anomaly_backfill(db, session_id=session_id, comments=inserted_comments, source=source))
    return {
        "inserted": inserted,
        "agent_runs_triggered": len(runs),
        "alerts_created": sum(1 for run in runs if run.get("alert_created")),
        "trace_id": runs[-1]["trace_id"] if runs else None,
        "agent_run_id": runs[-1]["run_id"] if runs else None,
    }


async def _run_mixed_anomaly_backfill(db: AsyncSession, *, session_id: int, comments: list[LiveComment], source: str) -> list[dict]:
    by_type: dict[str, list[LiveComment]] = {}
    for comment in comments:
        if comment.matched_type:
            by_type.setdefault(comment.matched_type, []).append(comment)
    if not (len(by_type.get(AlertType.COUPON_UNAVAILABLE.value, [])) >= 2 and len(by_type.get(AlertType.PRICE_MISMATCH.value, [])) >= 2):
        return []
    runs: list[dict] = []
    for alert_type in [AlertType.COUPON_UNAVAILABLE, AlertType.PRICE_MISMATCH]:
        typed_comments = by_type[alert_type.value]
        product_id = await resolve_product_id(db, session_id, typed_comments, alert_type)
        coupon_id = 1 if alert_type == AlertType.COUPON_UNAVAILABLE else None
        if await has_open_alert(db, session_id, alert_type, product_id, coupon_id):
            continue
        comment_ids = [comment.id for comment in typed_comments]
        db.add(
            CommentCluster(
                session_id=session_id,
                alert_type=alert_type.value,
                status="CONFIRMED",
                confidence=0.88,
                evidence_comment_ids_json=dumps(comment_ids),
                target_product_id=product_id,
                target_coupon_id=coupon_id,
                target_json=dumps({"product_id": product_id, "coupon_id": coupon_id}),
                summary=f"mixed anomaly split produced {alert_type.value}",
                created_by_agent="comment_triage",
            )
        )
        await db.flush()
        task = await create_agent_task(
            db,
            session_id=session_id,
            source=source,
            alert_type_hint=alert_type,
            comment_ids=comment_ids,
            input_payload={
                "reason": f"mixed anomaly split produced {alert_type.value}",
                "severity": AlertSeverity.P0.value if alert_type == AlertType.PRICE_MISMATCH else AlertSeverity.P1.value,
                "product_id": product_id,
                "coupon_id": coupon_id,
            },
        )
        runs.append(await run_agent_task(db, task.id))
    return runs
