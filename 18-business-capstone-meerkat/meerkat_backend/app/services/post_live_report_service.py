from __future__ import annotations

import secrets
from typing import Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import ApprovalTask, OpsAlert, PostLiveReport, SpeakerNote, StreamIncident
from app.services.serialization import dumps, model_to_dict
from app.services.trace_service import write_log


def new_report_trace_id() -> str:
    return f"tr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"


async def create_post_live_report(
    db: AsyncSession,
    session_id: int,
    *,
    trace_id: str | None = None,
    created_by_agent_run_id: int | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    trace_id = trace_id or new_report_trace_id()
    alerts = list((await db.scalars(select(OpsAlert).where(OpsAlert.session_id == session_id))).all())
    incidents = list((await db.scalars(select(StreamIncident).where(StreamIncident.session_id == session_id))).all())
    notes = list((await db.scalars(select(SpeakerNote).where(SpeakerNote.session_id == session_id))).all())
    approvals = list((await db.scalars(select(ApprovalTask).where(ApprovalTask.session_id == session_id))).all())

    price_alerts = [alert for alert in alerts if alert.alert_type == "PRICE_MISMATCH"]
    coupon_alerts = [alert for alert in alerts if alert.alert_type == "COUPON_UNAVAILABLE"]
    memory_updates = []
    if price_alerts:
        memory_updates.append({"scope": "by_product", "summary": "该商品上次直播出现过价格口径问题，开播前必须复核页面价、口播价和券后价。"})
    if coupon_alerts:
        memory_updates.append({"scope": "by_coupon", "summary": "直播间出现过优惠券未生效投诉，开播前必须检查优惠券生效时间。"})
    if incidents:
        memory_updates.append({"scope": "by_live_room", "summary": "直播间出现过推流健康异常，开播前必须执行 HLS/ffprobe 巡检。"})

    metrics = {
        "ops_alerts": len(alerts),
        "stream_incidents": len(incidents),
        "speaker_notes": len(notes),
        "approval_tasks": len(approvals),
        "pending_approvals": sum(1 for task in approvals if task.status == "PENDING"),
    }
    recommendations = [
        "开播前检查优惠券生效时间和适用商品。",
        "开播前比对主播口播价、页面价和券后价。",
        "直播中持续记录推流健康样本，连续异常后升级为运营告警。",
    ]
    summary_markdown = "\n".join(
        [
            f"# 直播复盘 Session {session_id}",
            "",
            f"- 推流异常：{len(incidents)} 次",
            f"- 评论运营异常：{len(alerts)} 次",
            f"- 主播话术：{len(notes)} 条",
            f"- 待审批任务：{metrics['pending_approvals']} 个",
            "",
            "## 最高风险问题",
            "价格口径风险" if price_alerts else "暂无价格口径风险",
            "",
            "## 改进建议",
            *[f"- {item}" for item in recommendations],
        ]
    )
    report = PostLiveReport(
        session_id=session_id,
        title=f"Session {session_id} 直播复盘",
        summary_markdown=summary_markdown,
        metrics_json=dumps(metrics),
        recommendations_json=dumps(recommendations),
        memory_updates_json=dumps(memory_updates),
        created_by_agent_run_id=created_by_agent_run_id,
        trace_id=trace_id,
    )
    db.add(report)
    await db.flush()
    await write_log(
        db,
        trace_id=trace_id,
        session_id=session_id,
        agent_name="report",
        action_type="MEMORY_UPDATED",
        output_data={"report_id": report.id, "memory_updates": memory_updates},
    )
    if commit:
        await db.commit()
    return {
        **model_to_dict(report),
        "report_id": report.id,
        "metrics": metrics,
        "recommendations": recommendations,
        "memory_updates": memory_updates,
    }
