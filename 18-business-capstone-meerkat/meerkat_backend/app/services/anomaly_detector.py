from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AlertSeverity, AlertStatus, AlertType
from app.db.base import LiveComment, LiveSessionProduct, OpsAlert, utcnow


@dataclass(frozen=True)
class DetectedAnomaly:
    session_id: int
    alert_type: AlertType
    severity: AlertSeverity
    comment_ids: list[int]
    product_id: int | None
    coupon_id: int | None
    reason: str


THRESHOLDS = {
    AlertType.COUPON_UNAVAILABLE: 3,
    AlertType.INVENTORY_UNAVAILABLE: 3,
    AlertType.PRICE_MISMATCH: 2,
    AlertType.LINK_BROKEN: 3,
}


def infer_product_alias(text: str) -> int | None:
    normalized = text.replace(" ", "")
    if "1号" in normalized or "一号" in normalized:
        return 1
    if "2号" in normalized or "二号" in normalized:
        return 2
    if "3号" in normalized or "三号" in normalized:
        return 3
    return None


async def resolve_product_id(db: AsyncSession, session_id: int, comments: list[LiveComment], alert_type: AlertType) -> int | None:
    for comment in comments:
        order = infer_product_alias(comment.body)
        if order:
            product_id = await db.scalar(
                select(LiveSessionProduct.product_id).where(
                    LiveSessionProduct.session_id == session_id,
                    LiveSessionProduct.display_order == order,
                )
            )
            if product_id:
                return product_id
    if alert_type == AlertType.INVENTORY_UNAVAILABLE:
        return 2
    if alert_type == AlertType.PRICE_MISMATCH:
        return 3
    return None


async def has_open_alert(db: AsyncSession, session_id: int, alert_type: AlertType, product_id: int | None, coupon_id: int | None) -> bool:
    query = select(OpsAlert).where(
        OpsAlert.session_id == session_id,
        OpsAlert.alert_type == alert_type.value,
        OpsAlert.status == AlertStatus.OPEN.value,
    )
    if product_id is not None:
        query = query.where(OpsAlert.product_id == product_id)
    if coupon_id is not None:
        query = query.where(OpsAlert.coupon_id == coupon_id)
    return (await db.scalar(query)) is not None


async def detect_after_comment(session_id: int, comment_id: int, db: AsyncSession) -> list[DetectedAnomaly]:
    comment = await db.get(LiveComment, comment_id)
    if not comment or not comment.matched_type:
        return []

    alert_type = AlertType(comment.matched_type)
    since = comment.created_at - timedelta(seconds=180)
    comments = list(
        (
            await db.scalars(
                select(LiveComment)
                .where(
                    LiveComment.session_id == session_id,
                    LiveComment.matched_type == alert_type.value,
                    LiveComment.created_at >= since,
                )
                .order_by(LiveComment.created_at.asc())
            )
        ).all()
    )
    threshold = THRESHOLDS.get(alert_type, 3)
    strong_price_signal = alert_type == AlertType.PRICE_MISMATCH and "虚假宣传" in comment.body
    if len(comments) < threshold and not strong_price_signal:
        return []

    product_id = await resolve_product_id(db, session_id, comments, alert_type)
    coupon_id = 1 if alert_type == AlertType.COUPON_UNAVAILABLE else None
    if await has_open_alert(db, session_id, alert_type, product_id, coupon_id):
        return []

    severity = AlertSeverity.P0 if alert_type == AlertType.PRICE_MISMATCH else AlertSeverity.P1
    return [
        DetectedAnomaly(
            session_id=session_id,
            alert_type=alert_type,
            severity=severity,
            comment_ids=[item.id for item in comments],
            product_id=product_id,
            coupon_id=coupon_id,
            reason=f"{len(comments)} comments matched {alert_type.value} within 180s at {utcnow().isoformat()}",
        )
    ]
