import pytest
from httpx import ASGITransport, AsyncClient

from app.db.init_db import reset_database
from app.db.seed import seed_database
from app.main import app
from app.db.session import SessionLocal
from app.db.base import LiveComment, OwncastEvent
from sqlalchemy import select


@pytest.fixture(autouse=True)
async def seeded_database():
    await reset_database()
    await seed_database()


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "meerkat-backend"}


@pytest.mark.asyncio
async def test_coupon_simulation_creates_business_objects_through_agent_tools():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/comments",
            json={
                "session_id": 1,
                "comments": [
                    {"user_name": "u1", "body": "券领不了"},
                    {"user_name": "u2", "body": "为什么没有 50 元券"},
                    {"user_name": "u3", "body": "主播不是说有券吗"},
                    {"user_name": "u4", "body": "点进去没有券啊"},
                ],
            },
        )
        payload = response.json()
        logs = (
            await client.get(
                "/api/v1/agent-action-logs",
                params={"trace_id": payload["trace_id"]},
            )
        ).json()["items"]
        alerts = (
            await client.get(
                "/api/v1/ops-alerts",
                params={"session_id": 1, "status": "OPEN"},
            )
        ).json()["items"]
        notes = (
            await client.get("/api/v1/speaker-notes", params={"session_id": 1})
        ).json()["items"]
        approvals = (
            await client.get("/api/v1/approval-tasks", params={"status": "PENDING"})
        ).json()["items"]
        proposals = (
            await client.get("/api/v1/action-proposals", params={"session_id": 1})
        ).json()["items"]

    assert response.status_code == 200
    assert payload["inserted"] == 4
    assert payload["agent_runs_triggered"] == 1
    assert payload["alerts_created"] == 1

    action_types = {log["action_type"] for log in logs}
    tools = {log["tool_name"] for log in logs if log["action_type"] == "TOOL_CALL"}
    assert {"SUBAGENT_DISPATCH", "TOOL_CALL", "TOOL_RESULT", "RISK_DECISION", "AGENT_RUN_FINISHED"} <= action_types
    assert {
        "search_recent_comments",
        "get_live_products",
        "get_coupon_detail",
        "search_policy_docs",
        "create_action_proposal",
        "create_ops_alert",
        "create_speaker_note",
        "create_approval_task",
    } <= tools
    assert "change_coupon_time" not in tools
    assert alerts[0]["alert_type"] == "COUPON_UNAVAILABLE"
    assert notes[0]["created_by"] == "agent"
    assert proposals[0]["action_type"] == "CHANGE_COUPON_TIME"
    assert proposals[0]["risk_level"] == "DESTRUCTIVE"
    assert approvals[0]["title"].startswith("审批优惠券")
    assert approvals[0]["proposal_id"] == proposals[0]["id"]


@pytest.mark.asyncio
async def test_inventory_simulation_does_not_create_unneeded_approval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/comments",
            json={
                "session_id": 1,
                "comments": [
                    {"user_name": "u1", "body": "2 号链接拍不了"},
                    {"user_name": "u2", "body": "下不了单"},
                    {"user_name": "u3", "body": "是不是没库存了"},
                ],
            },
        )
        payload = response.json()
        logs = (
            await client.get(
                "/api/v1/agent-action-logs",
                params={"trace_id": payload["trace_id"]},
            )
        ).json()["items"]
        approvals = (
            await client.get("/api/v1/approval-tasks", params={"status": "PENDING"})
        ).json()["items"]

    tools = {log["tool_name"] for log in logs if log["action_type"] == "TOOL_CALL"}
    assert response.status_code == 200
    assert "get_live_products" in tools
    assert "get_product_inventory" in tools
    assert "create_action_proposal" in tools
    assert "hide_product_from_live" not in tools
    assert approvals == []


@pytest.mark.asyncio
async def test_price_simulation_blocks_direct_price_change_and_requests_approval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/comments",
            json={
                "session_id": 1,
                "comments": [
                    {"user_name": "u1", "body": "主播说 99 页面怎么是 129"},
                    {"user_name": "u2", "body": "价格不对啊"},
                    {"user_name": "u3", "body": "这不是虚假宣传吗"},
                ],
            },
        )
        payload = response.json()
        logs = (
            await client.get(
                "/api/v1/agent-action-logs",
                params={"trace_id": payload["trace_id"]},
            )
        ).json()["items"]
        approvals = (
            await client.get("/api/v1/approval-tasks", params={"status": "PENDING"})
        ).json()["items"]

    tools = {log["tool_name"] for log in logs if log["action_type"] == "TOOL_CALL"}
    assert response.status_code == 200
    assert "get_live_products" in tools
    assert "get_product_detail" in tools
    assert "create_action_proposal" in tools
    assert "change_product_price" not in tools
    assert len(approvals) == 1
    assert approvals[0]["risk_level"] == "DESTRUCTIVE"


@pytest.mark.asyncio
async def test_owncast_chat_webhook_links_comment_to_raw_event_and_runs_agent():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for idx, body in enumerate(["券领不了", "为什么没有 50 元券", "点进去没有券啊"], start=1):
            response = await client.post(
                "/api/v1/integrations/owncast/webhook",
                json={
                    "type": "CHAT",
                    "eventData": {
                        "id": f"msg-{idx}",
                        "body": body,
                        "user": {"displayName": f"viewer-{idx}", "id": f"user-{idx}"},
                    },
                },
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["agent_runs_triggered"] == 1
    assert payload["trace_id"]

    async with SessionLocal() as session:
        events = list((await session.scalars(select(OwncastEvent).order_by(OwncastEvent.id.asc()))).all())
        comments = list((await session.scalars(select(LiveComment).order_by(LiveComment.id.asc()))).all())

    assert len(events) == 3
    assert len(comments) == 3
    assert all(event.processed for event in events)
    assert [comment.owncast_event_id for comment in comments] == [event.id for event in events]
    assert [comment.external_message_id for comment in comments] == ["msg-1", "msg-2", "msg-3"]
