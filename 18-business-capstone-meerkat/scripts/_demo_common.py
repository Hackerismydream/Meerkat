import asyncio
import os
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

CAPSTONE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = CAPSTONE_DIR / "meerkat_backend"
demo_db = BACKEND_DIR / f"{Path(sys.argv[0]).stem}.db"
os.environ.setdefault("MEERKAT_DATABASE_URL", f"sqlite+aiosqlite:///{demo_db}")
for path in (CAPSTONE_DIR, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.db.init_db import reset_database
from app.db.seed import seed_database
from app.main import app


async def run_demo(name: str, comments: list[str]) -> None:
    await reset_database()
    await seed_database()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/comments",
            json={"session_id": 1, "comments": [{"user_name": f"{name}-{idx}", "body": body} for idx, body in enumerate(comments, start=1)]},
        )
        payload = response.json()
        logs = (await client.get("/api/v1/agent-action-logs", params={"trace_id": payload["trace_id"]})).json()["items"]
        alerts = (await client.get("/api/v1/ops-alerts", params={"session_id": 1, "status": "OPEN"})).json()["items"]
        notes = (await client.get("/api/v1/speaker-notes", params={"session_id": 1})).json()["items"]
        approvals = (await client.get("/api/v1/approval-tasks", params={"status": "PENDING"})).json()["items"]

    print(f"demo={name}")
    print(f"trace_id={payload['trace_id']}")
    print(f"agent_runs_triggered={payload['agent_runs_triggered']}")
    print(f"alerts={[(item['id'], item['alert_type']) for item in alerts]}")
    print(f"speaker_notes={[(item['id'], item['body']) for item in notes]}")
    print(f"approvals={[(item['id'], item['risk_level'], item['title']) for item in approvals]}")
    print("tool_calls=" + ",".join(log["tool_name"] for log in logs if log["action_type"] == "TOOL_CALL"))
    print("eval_hint=run `make eval` and inspect matching case ids in meerkat_agent/evals/report.md")


async def run_stream_demo(name: str, scenario: str, samples: list[dict] | None = None) -> None:
    await reset_database()
    await seed_database()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulations/stream-health",
            json={"session_id": 1, "scenario": scenario, "samples": samples or []},
        )
        payload = response.json()
        logs = (await client.get("/api/v1/agent-action-logs", params={"trace_id": payload["trace_id"]})).json()["items"]
        alerts = (await client.get("/api/v1/ops-alerts", params={"session_id": 1, "status": "OPEN"})).json()["items"]
        notes = (await client.get("/api/v1/speaker-notes", params={"session_id": 1})).json()["items"]
        approvals = (await client.get("/api/v1/approval-tasks", params={"status": "PENDING"})).json()["items"]

    print(f"demo={name}")
    print(f"trace_id={payload['trace_id']}")
    print(f"incident_type={payload['incident_type']}")
    print(f"created_alerts={[(item['id'], item['alert_type']) for item in alerts]}")
    print(f"speaker_notes={[(item['id'], item['body']) for item in notes]}")
    print(f"approval_tasks={[(item['id'], item['risk_level'], item['title']) for item in approvals]}")
    print("agent_run_summary=" + str(payload.get("created_entities")))
    print("tool_calls=" + ",".join(log["tool_name"] for log in logs if log["action_type"] == "TOOL_CALL"))
    print("eval_hint=stream_health cases in meerkat_agent/evals/report.md")


async def run_post_live_report_demo() -> None:
    await reset_database()
    await seed_database()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/simulations/comments",
            json={"session_id": 1, "comments": [{"user_name": "price-demo", "body": body} for body in ["主播说 99 页面怎么是 129", "价格不对", "虚假宣传"]]},
        )
        response = await client.post("/api/v1/simulations/post-live-report", json={"session_id": 1})
        payload = response.json()

    print("demo=post-live-report")
    print(f"trace_id={payload['trace_id']}")
    print(f"report_id={payload['report_id']}")
    print("created_alerts=see summary_markdown")
    print("speaker_notes=see summary_markdown")
    print("approval_tasks=see metrics")
    print("agent_run_summary=" + str(payload["metrics"]))
    print("memory_updates=" + str(payload["memory_updates"]))
    print("eval_hint=report is generated from persisted alerts/incidents/approvals")


async def run_pre_live_check_demo() -> None:
    await reset_database()
    await seed_database()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/simulations/pre-live-check", json={"session_id": 1})
        payload = response.json()
        alerts = (await client.get("/api/v1/ops-alerts", params={"session_id": 1, "status": "OPEN"})).json()["items"]
        notes = (await client.get("/api/v1/speaker-notes", params={"session_id": 1})).json()["items"]
        approvals = (await client.get("/api/v1/approval-tasks", params={"status": "PENDING"})).json()["items"]
        logs = (await client.get("/api/v1/agent-action-logs", params={"trace_id": payload["trace_id"]})).json()["items"]

    print("demo=pre-live-check")
    print(f"trace_id={payload['trace_id']}")
    print(f"created_alerts={[(item['id'], item['alert_type']) for item in alerts]}")
    print(f"speaker_notes={[(item['id'], item['body']) for item in notes]}")
    print(f"approval_tasks={[(item['id'], item['risk_level'], item['title']) for item in approvals]}")
    print("agent_run_summary=" + str(payload.get("created_entities")))
    print("tool_calls=" + ",".join(log["tool_name"] for log in logs if log["action_type"] == "TOOL_CALL"))
    print("eval_hint=pre-live check verifies inventory, coupon, and price risk before live operations")


def main(name: str, comments: list[str]) -> None:
    asyncio.run(run_demo(name, comments))


def stream_main(name: str, scenario: str, samples: list[dict] | None = None) -> None:
    asyncio.run(run_stream_demo(name, scenario, samples))


def report_main() -> None:
    asyncio.run(run_post_live_report_demo())


def pre_live_main() -> None:
    asyncio.run(run_pre_live_check_demo())
