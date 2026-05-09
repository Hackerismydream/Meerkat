from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AlertStatus, ApprovalStatus, LiveSessionStatus
from app.db.base import (
    ActionProposal,
    AgentActionLog,
    AgentRun,
    AgentTask,
    ApprovalTask,
    Coupon,
    LiveComment,
    LiveSession,
    LiveSessionProduct,
    OpsAlert,
    Product,
    SpeakerNote,
    StreamHealthSample,
    StreamIncident,
    SkuInventory,
)
from app.db.session import get_session
from app.schemas import (
    CreateAgentTaskRequest,
    CreateActionProposalRequest,
    CreateApprovalTaskRequest,
    CreateLiveSessionRequest,
    CreateOpsAlertRequest,
    CreateSpeakerNoteRequest,
    PostLiveReportRequest,
    SimulationRequest,
    SimulationResponse,
    StreamHealthSimulationRequest,
)
from app.services.agent_task_service import create_agent_task, run_agent_task
from app.services.owncast_webhook_service import handle as handle_owncast_webhook
from app.services.serialization import dumps, model_to_dict
from app.services.simulation_service import insert_comments_and_run_agent
from app.services.stream_health_service import simulate_stream_health

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "meerkat-backend"}


@router.post("/integrations/owncast/webhook")
async def owncast_webhook(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    payload = await request.json()
    result = await handle_owncast_webhook(payload, session=session)
    return {"ok": True, **result}


@router.post("/simulations/comments", response_model=SimulationResponse)
async def simulate_comments(payload: SimulationRequest, session: AsyncSession = Depends(get_session)) -> dict:
    result = await insert_comments_and_run_agent(session, session_id=payload.session_id, comments=payload.comments)
    await session.commit()
    return result


@router.post("/simulations/stream-health")
async def simulate_stream_health_endpoint(payload: StreamHealthSimulationRequest, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        return await simulate_stream_health(session, session_id=payload.session_id, scenario=payload.scenario, samples=payload.samples)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/simulations/post-live-report")
async def simulate_post_live_report(payload: PostLiveReportRequest, session: AsyncSession = Depends(get_session)) -> dict:
    task = await create_agent_task(
        session,
        session_id=payload.session_id,
        source="SIMULATION",
        task_type="POST_LIVE_REPORT",
        input_payload={"report_scope": "post_live"},
    )
    return await run_agent_task(session, task.id)


@router.post("/simulations/pre-live-check")
async def simulate_pre_live_check(payload: PostLiveReportRequest, session: AsyncSession = Depends(get_session)) -> dict:
    task = await create_agent_task(
        session,
        session_id=payload.session_id,
        source="SIMULATION",
        task_type="PRE_LIVE_CHECK",
        input_payload={"check_scope": "pre_live"},
    )
    return await run_agent_task(session, task.id)


@router.get("/live-sessions/{session_id}")
async def get_live_session(session_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    live_session = await session.get(LiveSession, session_id)
    if not live_session:
        raise HTTPException(404, "live session not found")
    return model_to_dict(live_session)


@router.post("/live-sessions")
async def create_live_session(payload: CreateLiveSessionRequest, session: AsyncSession = Depends(get_session)) -> dict:
    live_session = LiveSession(title=payload.title, status=LiveSessionStatus.SCHEDULED.value)
    session.add(live_session)
    await session.commit()
    return model_to_dict(live_session)


@router.get("/live-sessions/{session_id}/products")
async def get_live_products(session_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    rows = (
        await session.execute(
            select(LiveSessionProduct, Product)
            .join(Product, Product.id == LiveSessionProduct.product_id)
            .where(LiveSessionProduct.session_id == session_id)
            .order_by(LiveSessionProduct.display_order)
        )
    ).all()
    return {"items": [{**model_to_dict(product), "anchor_alias": live_product.anchor_alias, "display_order": live_product.display_order} for live_product, product in rows]}


@router.get("/comments/recent")
async def recent_comments(session_id: int, limit: int = 50, session: AsyncSession = Depends(get_session)) -> dict:
    comments = list((await session.scalars(select(LiveComment).where(LiveComment.session_id == session_id).order_by(LiveComment.created_at.desc()).limit(limit))).all())
    return {"items": [model_to_dict(comment) for comment in comments]}


@router.get("/comments/search")
async def search_comments(session_id: int, q: str = "", since_minutes: int = 3, session: AsyncSession = Depends(get_session)) -> dict:
    comments = list((await session.scalars(select(LiveComment).where(LiveComment.session_id == session_id).order_by(LiveComment.created_at.desc()).limit(200))).all())
    if q:
        comments = [comment for comment in comments if q in comment.body or q in (comment.matched_type or "")]
    return {"items": [model_to_dict(comment) for comment in comments], "since_minutes": since_minutes}


@router.get("/products/{product_id}")
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "product not found")
    return model_to_dict(product)


@router.get("/products/by-external-id/{external_product_id}")
async def get_product_by_external_id(external_product_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    product = await session.scalar(select(Product).where(Product.external_product_id == external_product_id))
    if not product:
        raise HTTPException(404, "product not found")
    return model_to_dict(product)


@router.get(
    "/products/{product_id}/inventory",
    openapi_extra={"x-agent-tool": {"enabled": True, "name": "get_product_inventory", "risk_level": "READ_ONLY", "description": "Get SKU inventory for a product."}},
)
async def get_product_inventory(product_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    inventory = list((await session.scalars(select(SkuInventory).where(SkuInventory.product_id == product_id))).all())
    return {"items": [model_to_dict(item) for item in inventory], "total_available": sum(item.available_stock for item in inventory)}


@router.get("/coupons/{coupon_id}")
async def get_coupon(coupon_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    coupon = await session.get(Coupon, coupon_id)
    if not coupon:
        raise HTTPException(404, "coupon not found")
    return model_to_dict(coupon)


@router.get("/coupons/by-external-id/{external_coupon_id}")
async def get_coupon_by_external_id(external_coupon_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    coupon = await session.scalar(select(Coupon).where(Coupon.external_coupon_id == external_coupon_id))
    if not coupon:
        raise HTTPException(404, "coupon not found")
    return model_to_dict(coupon)


@router.get("/live-sessions/{session_id}/coupons")
async def get_session_coupons(session_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    coupons = list((await session.scalars(select(Coupon))).all())
    return {"items": [model_to_dict(coupon) for coupon in coupons]}


@router.post(
    "/ops-alerts",
    openapi_extra={"x-agent-tool": {"enabled": True, "name": "create_ops_alert", "risk_level": "LOW_RISK_WRITE", "description": "Create an operation alert for a detected livestream issue."}},
)
async def create_ops_alert(payload: CreateOpsAlertRequest, session: AsyncSession = Depends(get_session)) -> dict:
    alert = OpsAlert(
        session_id=payload.session_id,
        alert_type=payload.alert_type,
        severity=payload.severity,
        status=AlertStatus.OPEN.value,
        title=payload.title,
        summary=payload.summary,
        evidence_json=dumps(payload.evidence),
        product_id=payload.product_id,
        coupon_id=payload.coupon_id,
        dedupe_key=f"api:{payload.session_id}:{payload.alert_type}:{datetime.now(timezone.utc).timestamp()}",
        created_by="agent",
        trace_id=payload.trace_id,
    )
    session.add(alert)
    await session.commit()
    return model_to_dict(alert)


@router.get("/ops-alerts")
async def list_ops_alerts(session_id: int | None = None, status: str | None = None, session: AsyncSession = Depends(get_session)) -> dict:
    query = select(OpsAlert).order_by(OpsAlert.created_at.desc())
    if session_id is not None:
        query = query.where(OpsAlert.session_id == session_id)
    if status is not None:
        query = query.where(OpsAlert.status == status)
    alerts = list((await session.scalars(query)).all())
    return {"items": [model_to_dict(alert) for alert in alerts]}


@router.get("/ops-alerts/{alert_id}")
async def get_ops_alert(alert_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    alert = await session.get(OpsAlert, alert_id)
    if not alert:
        raise HTTPException(404, "alert not found")
    return model_to_dict(alert)


@router.patch("/ops-alerts/{alert_id}/status")
async def update_ops_alert_status(alert_id: int, status: str, session: AsyncSession = Depends(get_session)) -> dict:
    alert = await session.get(OpsAlert, alert_id)
    if not alert:
        raise HTTPException(404, "alert not found")
    alert.status = status
    await session.commit()
    return model_to_dict(alert)


@router.post("/speaker-notes")
async def create_speaker_note(payload: CreateSpeakerNoteRequest, session: AsyncSession = Depends(get_session)) -> dict:
    note = SpeakerNote(session_id=payload.session_id, alert_id=payload.alert_id, body=payload.body, target=payload.target, status="DRAFT", created_by="agent", trace_id=payload.trace_id)
    session.add(note)
    await session.commit()
    return model_to_dict(note)


@router.get("/speaker-notes")
async def list_speaker_notes(session_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    notes = list((await session.scalars(select(SpeakerNote).where(SpeakerNote.session_id == session_id).order_by(SpeakerNote.created_at.desc()))).all())
    return {"items": [model_to_dict(note) for note in notes]}


@router.post("/speaker-notes/{note_id}/send-owncast")
async def send_note_owncast(note_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    note = await session.get(SpeakerNote, note_id)
    if not note:
        raise HTTPException(404, "speaker note not found")
    return {"dry_run": True, "note_id": note.id, "body": note.body}


@router.post("/action-proposals")
async def create_action_proposal(payload: CreateActionProposalRequest, session: AsyncSession = Depends(get_session)) -> dict:
    proposal = ActionProposal(
        session_id=payload.session_id,
        alert_id=payload.alert_id,
        action_type=payload.action_type,
        risk_level=payload.risk_level,
        arguments_json=dumps(payload.arguments),
        reason=payload.reason,
        status=payload.status,
        created_by_agent=payload.created_by_agent,
        trace_id=payload.trace_id,
    )
    session.add(proposal)
    await session.commit()
    return model_to_dict(proposal)


@router.get("/action-proposals")
async def list_action_proposals(session_id: int | None = None, trace_id: str | None = None, session: AsyncSession = Depends(get_session)) -> dict:
    query = select(ActionProposal).order_by(ActionProposal.created_at.desc())
    if session_id is not None:
        query = query.where(ActionProposal.session_id == session_id)
    if trace_id is not None:
        query = query.where(ActionProposal.trace_id == trace_id)
    proposals = list((await session.scalars(query)).all())
    return {"items": [model_to_dict(proposal) for proposal in proposals]}


@router.post("/approval-tasks")
async def create_approval_task(payload: CreateApprovalTaskRequest, session: AsyncSession = Depends(get_session)) -> dict:
    task = ApprovalTask(proposal_id=payload.proposal_id, session_id=payload.session_id, risk_level=payload.risk_level, title=payload.title, reason=payload.reason, payload_json=dumps(payload.payload), status=ApprovalStatus.PENDING.value, trace_id=payload.trace_id)
    session.add(task)
    await session.commit()
    return model_to_dict(task)


@router.get("/approval-tasks")
async def list_approval_tasks(status: str | None = None, session: AsyncSession = Depends(get_session)) -> dict:
    query = select(ApprovalTask).order_by(ApprovalTask.created_at.desc())
    if status:
        query = query.where(ApprovalTask.status == status)
    tasks = list((await session.scalars(query)).all())
    return {"items": [model_to_dict(task) for task in tasks]}


@router.post("/approval-tasks/{task_id}/approve")
async def approve_task(task_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    task = await session.get(ApprovalTask, task_id)
    if not task:
        raise HTTPException(404, "approval task not found")
    task.status = ApprovalStatus.APPROVED.value
    task.reviewed_at = datetime.now(timezone.utc)
    await session.commit()
    return model_to_dict(task)


@router.post("/approval-tasks/{task_id}/reject")
async def reject_task(task_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    task = await session.get(ApprovalTask, task_id)
    if not task:
        raise HTTPException(404, "approval task not found")
    task.status = ApprovalStatus.REJECTED.value
    task.reviewed_at = datetime.now(timezone.utc)
    await session.commit()
    return model_to_dict(task)


@router.post("/agent-tasks")
async def api_create_agent_task(payload: CreateAgentTaskRequest, session: AsyncSession = Depends(get_session)) -> dict:
    task = await create_agent_task(session, session_id=payload.session_id, source=payload.source, alert_type_hint=payload.alert_type_hint, comment_ids=payload.comment_ids, input_payload=payload.input_payload)
    await session.commit()
    return model_to_dict(task)


@router.get("/agent-tasks/{task_id}")
async def get_agent_task(task_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    task = await session.get(AgentTask, task_id)
    if not task:
        raise HTTPException(404, "agent task not found")
    return model_to_dict(task)


@router.post("/agent-tasks/{task_id}/run")
async def api_run_agent_task(task_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    return await run_agent_task(session, task_id)


@router.get("/agent-runs/{run_id}")
async def get_agent_run(run_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    run = await session.get(AgentRun, run_id)
    if not run:
        raise HTTPException(404, "agent run not found")
    return model_to_dict(run)


@router.get("/agent-runs")
async def list_agent_runs(trace_id: str | None = None, session: AsyncSession = Depends(get_session)) -> dict:
    query = select(AgentRun).order_by(AgentRun.created_at.desc())
    if trace_id:
        query = query.where(AgentRun.trace_id == trace_id)
    runs = list((await session.scalars(query)).all())
    return {"items": [model_to_dict(run) for run in runs]}


@router.get("/agent-action-logs")
async def list_agent_logs(trace_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    logs = list((await session.scalars(select(AgentActionLog).where(AgentActionLog.trace_id == trace_id).order_by(AgentActionLog.id.asc()))).all())
    return {"items": [model_to_dict(log) for log in logs]}


@router.get("/agent-action-logs/recent")
async def recent_agent_logs(limit: int = Query(default=100, le=500), session: AsyncSession = Depends(get_session)) -> dict:
    logs = list((await session.scalars(select(AgentActionLog).order_by(AgentActionLog.id.desc()).limit(limit))).all())
    return {"items": [model_to_dict(log) for log in logs]}


@router.get("/traces/{trace_id}")
async def replay_trace(trace_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    logs = list((await session.scalars(select(AgentActionLog).where(AgentActionLog.trace_id == trace_id).order_by(AgentActionLog.id.asc()))).all())
    if not logs:
        raise HTTPException(404, "trace not found")
    runs = list((await session.scalars(select(AgentRun).where(AgentRun.trace_id == trace_id).order_by(AgentRun.id.asc()))).all())
    timeline = [model_to_dict(log) for log in logs]
    agents: dict[str, dict] = {}
    for event in timeline:
        agent_name = event["agent_name"]
        agents.setdefault(agent_name, {"agent_name": agent_name, "events": [], "tool_calls": []})
        agents[agent_name]["events"].append(event)
        if event["action_type"] == "TOOL_CALL":
            agents[agent_name]["tool_calls"].append(event["tool_name"])
    return {
        "trace_id": trace_id,
        "runs": [model_to_dict(run) for run in runs],
        "timeline": timeline,
        "agents": list(agents.values()),
        "workflow_tree": {
            "root": runs[0].root_agent if runs else timeline[0]["agent_name"],
            "children": sorted({(event.get("output") or {}).get("to") for event in timeline if event["action_type"] == "SUBAGENT_DISPATCH" and (event.get("output") or {}).get("to")}),
        },
    }


@router.get("/stream-health/samples")
async def list_stream_health_samples(session_id: int = 1, session: AsyncSession = Depends(get_session)) -> dict:
    samples = list((await session.scalars(select(StreamHealthSample).where(StreamHealthSample.session_id == session_id).order_by(StreamHealthSample.id.desc()).limit(50))).all())
    return {"items": [model_to_dict(sample) for sample in samples]}


@router.get("/stream-incidents")
async def list_stream_incidents(session_id: int = 1, status: str | None = None, session: AsyncSession = Depends(get_session)) -> dict:
    query = select(StreamIncident).where(StreamIncident.session_id == session_id).order_by(StreamIncident.id.desc())
    if status:
        query = query.where(StreamIncident.status == status)
    incidents = list((await session.scalars(query)).all())
    return {"items": [model_to_dict(incident) for incident in incidents]}


dashboard_router = APIRouter()


@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Meerkat Console</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f7f7f4; color: #1d1d1b; }
    h1 { font-size: 28px; margin-bottom: 4px; }
    main { display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap: 16px; }
    section { background: white; border: 1px solid #ddd8cc; border-radius: 8px; padding: 16px; min-height: 180px; }
    pre { white-space: pre-wrap; font-size: 12px; }
  </style>
</head>
<body>
  <h1>Meerkat Console</h1>
  <p>直播状态、推流健康、评论异常、Agent trace、话术和审批任务。</p>
  <main>
    <section><h2>Recent Comments</h2><pre id="comments"></pre></section>
    <section><h2>Stream Incidents</h2><pre id="incidents"></pre></section>
    <section><h2>Open Alerts</h2><pre id="alerts"></pre></section>
    <section><h2>Speaker Notes</h2><pre id="notes"></pre></section>
    <section><h2>Pending Approvals</h2><pre id="approvals"></pre></section>
    <section><h2>Agent Timeline</h2><pre id="trace"></pre></section>
  </main>
  <script>
    async function load() {
      const [comments, incidents, alerts, notes, approvals, trace] = await Promise.all([
        fetch('/api/v1/comments/recent?session_id=1&limit=50').then(r => r.json()),
        fetch('/api/v1/stream-incidents?session_id=1').then(r => r.json()),
        fetch('/api/v1/ops-alerts?session_id=1&status=OPEN').then(r => r.json()),
        fetch('/api/v1/speaker-notes?session_id=1').then(r => r.json()),
        fetch('/api/v1/approval-tasks?status=PENDING').then(r => r.json()),
        fetch('/api/v1/agent-action-logs/recent?limit=80').then(r => r.json())
      ]);
      document.getElementById('comments').textContent = JSON.stringify(comments.items, null, 2);
      document.getElementById('incidents').textContent = JSON.stringify(incidents.items, null, 2);
      document.getElementById('alerts').textContent = JSON.stringify(alerts.items, null, 2);
      document.getElementById('notes').textContent = JSON.stringify(notes.items, null, 2);
      document.getElementById('approvals').textContent = JSON.stringify(approvals.items, null, 2);
      document.getElementById('trace').textContent = JSON.stringify(trace.items, null, 2);
    }
    load(); setInterval(load, 3000);
  </script>
</body>
</html>"""
