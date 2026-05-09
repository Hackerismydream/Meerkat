import pytest
from httpx import ASGITransport, AsyncClient

from app.db.init_db import reset_database
from app.db.seed import seed_database
from app.main import app
from app.db.session import SessionLocal
from app.db.base import (
    ApprovalTask,
    CommentCluster,
    LiveComment,
    LiveRoom,
    LiveScript,
    OwncastEvent,
    PostLiveReport,
    Product,
    ProductAlias,
    StreamHealthSample,
    StreamIncident,
)
from sqlalchemy import select
from meerkat_agent.tools import owncast_tools


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
async def test_coupon_flow_blocks_high_risk_tool_inside_tool_registry_and_dry_runs_owncast_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/comments",
            json={
                "session_id": 1,
                "comments": [
                    {"user_name": "u1", "body": "券领不了"},
                    {"user_name": "u2", "body": "为什么没有 50 元券"},
                    {"user_name": "u3", "body": "点进去没有券啊"},
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

    assert response.status_code == 200
    action_types = [log["action_type"] for log in logs]
    approval_events = [log for log in logs if log["action_type"] == "APPROVAL_REQUIRED"]
    owncast_events = [log for log in logs if log["action_type"] == "OWNCAST_MESSAGE_DRY_RUN"]
    executed_tools = [log["tool_name"] for log in logs if log["action_type"] == "TOOL_RESULT"]

    assert "APPROVAL_REQUIRED" in action_types
    assert approval_events[0]["tool_name"] == "change_coupon_time"
    assert approval_events[0]["output"]["status"] == "APPROVAL_REQUIRED"
    assert "change_coupon_time" not in executed_tools
    assert owncast_events
    assert owncast_events[0]["output"]["dry_run"] is True

    async with SessionLocal() as session:
        approvals = list((await session.scalars(select(ApprovalTask))).all())

    assert approvals[0].status == "PENDING"
    assert approvals[0].risk_level == "DESTRUCTIVE"


@pytest.mark.asyncio
async def test_owncast_system_message_failure_is_not_logged_as_sent(monkeypatch):
    class Response:
        status_code = 401

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(owncast_tools.settings, "owncast_dry_run", False)
    monkeypatch.setattr(owncast_tools.settings, "auto_send_owncast", True)
    monkeypatch.setattr(owncast_tools.settings, "owncast_access_token", "bad-token")
    monkeypatch.setattr(owncast_tools.httpx, "AsyncClient", lambda **_kwargs: Client())

    result = await owncast_tools.send_owncast_system_message("hello", dry_run=False)

    assert result["dry_run"] is True
    assert result["status_code"] == 401
    assert "Owncast returned 401" in result["error"]


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


@pytest.mark.asyncio
async def test_seed_data_matches_final_product_plan_domain_surface():
    async with SessionLocal() as session:
        live_rooms = list((await session.scalars(select(LiveRoom))).all())
        products = list((await session.scalars(select(Product))).all())
        aliases = list((await session.scalars(select(ProductAlias))).all())
        scripts = list((await session.scalars(select(LiveScript))).all())

    assert len(live_rooms) == 1
    assert len(products) >= 8
    assert len(aliases) >= 10
    assert len(scripts) >= 2


@pytest.mark.asyncio
async def test_stream_down_simulation_creates_incident_alert_note_and_trace_replay():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/stream-health",
            json={
                "session_id": 1,
                "scenario": "stream_down",
                "samples": [
                    {"is_live": False, "probe_status": "FAILED", "probe_error": "HLS playlist unavailable"},
                    {"is_live": False, "probe_status": "FAILED", "probe_error": "HLS playlist unavailable"},
                    {"is_live": False, "probe_status": "FAILED", "probe_error": "HLS playlist unavailable"},
                ],
            },
        )
        payload = response.json()
        replay = (await client.get(f"/api/v1/traces/{payload['trace_id']}")).json()

    assert response.status_code == 200
    assert payload["incident_type"] == "STREAM_INTERRUPTED"
    assert payload["created_entities"]["stream_incident_id"]
    assert payload["created_entities"]["ops_alert_id"]
    assert payload["created_entities"]["speaker_note_id"]
    assert payload["trace_id"]
    assert [event["action_type"] for event in replay["timeline"]]
    assert "stream_monitor" in {event["agent_name"] for event in replay["timeline"]}

    async with SessionLocal() as session:
        samples = list((await session.scalars(select(StreamHealthSample))).all())
        incidents = list((await session.scalars(select(StreamIncident))).all())

    assert len(samples) == 3
    assert len(incidents) == 1


@pytest.mark.asyncio
async def test_owncast_stream_stopped_webhook_triggers_stream_monitor_agent():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/integrations/owncast/webhook",
            json={"type": "STREAM_STOPPED", "eventData": {"streamTitle": "618 爆款家电直播"}},
        )
        payload = response.json()
        replay = (await client.get(f"/api/v1/traces/{payload['trace_id']}")).json()

    assert response.status_code == 200
    assert payload["incident_type"] == "STREAM_INTERRUPTED"
    assert payload["created_entities"]["stream_incident_id"]
    assert "stream_monitor" in {event["agent_name"] for event in replay["timeline"]}


@pytest.mark.asyncio
async def test_stream_probe_run_once_uses_real_probe_failure_path_and_triggers_agent():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/stream/probe/run-once",
            json={
                "session_id": 1,
                "owncast_base_url": "http://127.0.0.1:1",
                "hls_playlist_url": "http://127.0.0.1:1/hls/stream.m3u8",
            },
        )
        payload = response.json()
        latest = (await client.get("/api/v1/stream/health/latest", params={"session_id": 1})).json()

    assert response.status_code == 200
    assert payload["incident_type"] == "STREAM_INTERRUPTED"
    assert payload["trace_id"]
    assert latest["item"]["probe_status"] == "FAILED"
    assert "127.0.0.1:1" in latest["item"]["probe_error"]


@pytest.mark.asyncio
async def test_stream_probe_run_once_uses_ffprobe_audio_metadata(monkeypatch):
    async def fake_owncast_status(_base_url: str) -> dict:
        return {"probe_type": "OWNCAST_STATUS", "status": "OK", "duration_ms": 1, "is_live": True, "raw": {}, "error": None}

    async def fake_hls_playlist(_playlist_url: str) -> dict:
        return {"probe_type": "HLS_PLAYLIST", "status": "OK", "duration_ms": 1, "last_segment_age_ms": 0, "error": None}

    async def fake_ffprobe(_media_url: str) -> dict:
        return {"probe_type": "FFPROBE", "status": "OK", "duration_ms": 1, "video_present": True, "audio_present": False, "error": None}

    monkeypatch.setattr("app.services.stream_probe_service.probe_owncast_status", fake_owncast_status)
    monkeypatch.setattr("app.services.stream_probe_service.probe_hls_playlist", fake_hls_playlist)
    monkeypatch.setattr("app.services.stream_probe_service.probe_ffprobe_stream", fake_ffprobe)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/stream/probe/run-once",
            json={"session_id": 1, "owncast_base_url": "http://owncast", "hls_playlist_url": "http://owncast/hls/stream.m3u8"},
        )
        payload = response.json()
        latest = (await client.get("/api/v1/stream/health/latest", params={"session_id": 1})).json()

    assert response.status_code == 200
    assert payload["incident_type"] == "NO_AUDIO"
    assert payload["probe"]["ffprobe"]["audio_present"] is False
    assert latest["item"]["audio_present"] is False


@pytest.mark.asyncio
async def test_single_noise_comment_does_not_create_cluster_or_agent_run():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/comments",
            json={"session_id": 1, "comments": [{"user_name": "u1", "body": "主播今天状态不错"}]},
        )

    assert response.status_code == 200
    assert response.json()["agent_runs_triggered"] == 0

    async with SessionLocal() as session:
        clusters = list((await session.scalars(select(CommentCluster))).all())

    assert clusters == []


@pytest.mark.asyncio
async def test_post_live_report_persists_markdown_and_memory_updates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
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
        response = await client.post("/api/v1/simulations/post-live-report", json={"session_id": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"]
    assert "价格口径" in payload["summary_markdown"]
    assert payload["memory_updates"]
    assert payload["run_id"]

    async with SessionLocal() as session:
        reports = list((await session.scalars(select(PostLiveReport))).all())

    assert len(reports) == 1


@pytest.mark.asyncio
async def test_dashboard_summary_and_trace_timeline_api_show_console_sections():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        simulation = await client.post(
            "/api/v1/simulations/stream-health",
            json={
                "session_id": 1,
                "scenario": "no_audio",
                "samples": [{"is_live": True, "audio_present": False, "probe_status": "OK"}],
            },
        )
        trace_id = simulation.json()["trace_id"]
        summary = (await client.get("/api/v1/dashboard/summary", params={"session_id": 1})).json()
        timeline = (await client.get(f"/api/v1/traces/{trace_id}/timeline")).json()

    assert summary["live_session"]["id"] == 1
    assert summary["stream_health"]["latest_sample"]["audio_present"] is False
    assert summary["stream_incidents"]["items"][0]["incident_type"] == "NO_AUDIO"
    assert summary["agent"]["recent_runs"]
    assert timeline["trace_id"] == trace_id
    assert timeline["events"]


@pytest.mark.asyncio
async def test_dashboard_summary_scopes_agent_runs_to_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/live-sessions", json={"title": "Second room"})
        session_id = created.json()["id"]
        await client.post(
            "/api/v1/simulations/stream-health",
            json={
                "session_id": session_id,
                "scenario": "no_audio",
                "samples": [{"is_live": True, "audio_present": False, "probe_status": "OK"}],
            },
        )
        summary = (await client.get("/api/v1/dashboard/summary", params={"session_id": 1})).json()

    assert summary["agent"]["recent_runs"] == []
