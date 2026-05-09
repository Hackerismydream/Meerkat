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


def main(name: str, comments: list[str]) -> None:
    asyncio.run(run_demo(name, comments))
