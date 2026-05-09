from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.base import AgentActionLog, CommentCluster, OpsAlert, SpeakerNote, StreamIncident, StreamProbeJob
from app.db.init_db import reset_database
from app.db.seed import seed_database
from app.db.session import SessionLocal
from app.main import app
from meerkat_agent.runtime.schemas import AgentTool
from meerkat_agent.runtime.tool_registry import ToolRegistry


CAPSTONE_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
async def seeded_database():
    await reset_database()
    await seed_database()


def test_acceptance_v1_files_and_make_targets_exist():
    makefile = (CAPSTONE_DIR / "Makefile").read_text(encoding="utf-8")
    assert "acceptance-v1:" in makefile
    assert "acceptance-offline:" in makefile
    assert "acceptance-owncast:" in makefile
    assert "check-owncast-webhook:" in makefile
    assert "configure-owncast-webhook:" in makefile
    assert (CAPSTONE_DIR / "meerkat_backend" / "Dockerfile").exists()
    assert (CAPSTONE_DIR / "scripts" / "acceptance" / "run_acceptance_v1.py").exists()
    assert (CAPSTONE_DIR / "ACCEPTANCE.md").exists()
    assert (CAPSTONE_DIR / "V1_STATUS.md").exists()


@pytest.mark.asyncio
async def test_probe_job_tick_opens_and_recovers_stream_incident(monkeypatch):
    async def failed_owncast(_base_url: str) -> dict:
        return {"probe_type": "OWNCAST_STATUS", "status": "FAILED", "duration_ms": 1, "is_live": False, "raw": {}, "error": "offline"}

    async def ok_owncast(_base_url: str) -> dict:
        return {"probe_type": "OWNCAST_STATUS", "status": "OK", "duration_ms": 1, "is_live": True, "raw": {}, "error": None}

    async def ok_hls(_playlist_url: str) -> dict:
        return {"probe_type": "HLS_PLAYLIST", "status": "OK", "duration_ms": 1, "last_segment_age_ms": 0, "last_segment_uri": "seg.ts", "playlist_hash": "sha256:1", "target_duration_ms": 2000, "error": None}

    async def ok_ffprobe(_media_url: str) -> dict:
        return {"probe_type": "FFPROBE", "status": "OK", "duration_ms": 1, "video_present": True, "audio_present": True, "error": None}

    monkeypatch.setattr("app.services.stream_probe_scheduler.probe_owncast_status", failed_owncast)
    monkeypatch.setattr("app.services.stream_probe_scheduler.probe_hls_playlist", ok_hls)
    monkeypatch.setattr("app.services.stream_probe_scheduler.probe_ffprobe_stream", ok_ffprobe)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/api/v1/stream/probe/start", json={"session_id": 1, "probe_interval_seconds": 1})
        for _ in range(3):
            opened = await client.post("/api/v1/stream/probe/tick", json={"session_id": 1})
        monkeypatch.setattr("app.services.stream_probe_scheduler.probe_owncast_status", ok_owncast)
        for _ in range(3):
            recovered = await client.post("/api/v1/stream/probe/tick", json={"session_id": 1})

    assert start.status_code == 200
    assert opened.json()["incident"]["status"] == "OPEN"
    assert recovered.json()["incident"]["status"] == "RECOVERED"
    async with SessionLocal() as session:
        job = await session.scalar(select(StreamProbeJob))
        incident = await session.scalar(select(StreamIncident))
    assert job.status == "RUNNING"
    assert incident.status == "RECOVERED"


@pytest.mark.asyncio
async def test_mixed_anomaly_split_resolves_product_alias_and_creates_two_alerts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/comments",
            json={
                "session_id": 1,
                "comments": [
                    {"user_name": "u1", "body": "3 号链接券领不了"},
                    {"user_name": "u2", "body": "主播说 99 页面是 129"},
                    {"user_name": "u3", "body": "点进去没有 50 元券"},
                    {"user_name": "u4", "body": "价格不对啊"},
                ],
            },
        )
        alerts = (await client.get("/api/v1/ops-alerts", params={"session_id": 1, "status": "OPEN"})).json()["items"]

    assert response.status_code == 200
    assert response.json()["agent_runs_triggered"] == 2
    assert {alert["alert_type"] for alert in alerts} == {"COUPON_UNAVAILABLE", "PRICE_MISMATCH"}
    assert all(alert["product_id"] == 3 for alert in alerts if alert["alert_type"] == "PRICE_MISMATCH")
    async with SessionLocal() as session:
        clusters = list((await session.scalars(select(CommentCluster).order_by(CommentCluster.id))).all())
    assert {cluster.alert_type for cluster in clusters} == {"COUPON_UNAVAILABLE", "PRICE_MISMATCH"}


@pytest.mark.asyncio
async def test_structured_subagent_files_exist_and_stream_trace_contains_diagnosis():
    for agent_name in ["stream_monitor", "comment_triage", "product", "coupon", "policy", "risk", "script", "report"]:
        assert (CAPSTONE_DIR / "meerkat_agent" / "agents" / agent_name / "schema.py").exists()
        assert (CAPSTONE_DIR / "meerkat_agent" / "agents" / agent_name / "runner.py").exists()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/simulations/stream-health", json={"session_id": 1, "scenario": "stream_down", "samples": []})
        logs = (await client.get("/api/v1/agent-action-logs", params={"trace_id": response.json()["trace_id"]})).json()["items"]

    stream_results = [log for log in logs if log["action_type"] == "SUBAGENT_RESULT" and log["agent_name"] == "stream_monitor"]
    assert stream_results
    assert stream_results[0]["output"]["diagnosis"]
    assert stream_results[0]["output"]["recommended_actions"]


@pytest.mark.asyncio
async def test_stream_health_simulation_recovers_existing_incident():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        opened = await client.post("/api/v1/simulations/stream-health", json={"session_id": 1, "scenario": "stream_down", "samples": []})
        recovered = await client.post(
            "/api/v1/simulations/stream-health",
            json={
                "session_id": 1,
                "scenario": "stream_recover",
                "samples": [
                    {"is_live": True, "probe_status": "OK", "audio_present": True, "video_present": True},
                    {"is_live": True, "probe_status": "OK", "audio_present": True, "video_present": True},
                    {"is_live": True, "probe_status": "OK", "audio_present": True, "video_present": True},
                ],
            },
        )
        incident = await client.get(f"/api/v1/stream/incidents/{opened.json()['stream_incident']['id']}")

    assert opened.status_code == 200
    assert opened.json()["stream_incident"]["status"] == "OPEN"
    assert recovered.status_code == 200
    assert recovered.json()["stream_incident"]["status"] == "RECOVERED"
    assert recovered.json()["trace_id"] == opened.json()["trace_id"]
    assert incident.json()["status"] == "RECOVERED"


@pytest.mark.asyncio
async def test_tool_registry_v3_schema_timeout_output_validation_and_idempotency():
    async with SessionLocal() as session:
        registry = ToolRegistry(session, "tr_tool_v3", 1)

        async def slow_tool() -> dict:
            import asyncio

            await asyncio.sleep(0.05)
            return {"ok": True}

        async def missing_output() -> dict:
            return {"status": "OK"}

        async def create_entity(name: str) -> dict:
            return {"id": 1, "status": "OK", "name": name}

        registry.register(AgentTool("slow", "READ_ONLY", "slow", slow_tool, timeout_ms=1))
        registry.register(AgentTool("bad_output", "READ_ONLY", "bad", missing_output, output_schema={"required": ["id"]}))
        registry.register(AgentTool("create_once", "LOW_RISK_WRITE", "create", create_entity, input_schema={"required": ["name"]}, output_schema={"required": ["id", "status"]}, idempotency_key_strategy="arguments_hash"))

        timeout = await registry.call("slow", {}, agent_name="commander")
        bad = await registry.call("bad_output", {}, agent_name="commander")
        first = await registry.call("create_once", {"name": "same"}, agent_name="commander")
        second = await registry.call("create_once", {"name": "same"}, agent_name="commander")
        logs = list((await session.scalars(select(AgentActionLog).where(AgentActionLog.trace_id == "tr_tool_v3"))).all())

    assert timeout["status"] == "TOOL_TIMEOUT"
    assert bad["status"] == "TOOL_RESULT_SCHEMA_ERROR"
    assert first == second
    assert "IDEMPOTENCY_HIT" in {log.action_type for log in logs}


@pytest.mark.asyncio
async def test_speaker_note_send_owncast_updates_send_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/simulations/comments",
            json={"session_id": 1, "comments": [{"user_name": "u1", "body": "券领不了"}, {"user_name": "u2", "body": "为什么没有 50 元券"}, {"user_name": "u3", "body": "点进去没有券啊"}]},
        )
        notes = (await client.get("/api/v1/speaker-notes", params={"session_id": 1})).json()["items"]
        response = await client.post(f"/api/v1/speaker-notes/{notes[0]['id']}/send-owncast")

    assert response.status_code == 200
    assert response.json()["send_status"] == "DRY_RUN"
    async with SessionLocal() as session:
        note = await session.get(SpeakerNote, notes[0]["id"])
    assert note.send_status == "DRY_RUN"
