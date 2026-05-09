from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

from httpx import ASGITransport, AsyncClient

EVAL_DIR = Path(__file__).resolve().parent
CAPSTONE_DIR = EVAL_DIR.parents[1]
BACKEND_DIR = CAPSTONE_DIR / "meerkat_backend"
for path in (CAPSTONE_DIR, BACKEND_DIR, EVAL_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.db.init_db import reset_database
from app.db.seed import seed_database
from app.main import app
from graders import (
    grade_alert_type,
    grade_approval_trigger,
    grade_forbidden_tool_block,
    grade_policy_grounding,
    grade_risk_gate_accuracy,
    grade_subagent_dispatch_coverage,
    grade_tool_call_recall,
    grade_tool_call_precision,
    grade_tool_execution_success_rate,
    grade_tool_selection,
    grade_trace_completeness,
)


def read_cases() -> list[dict]:
    return [json.loads(line) for line in (EVAL_DIR / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


async def run_case(client: AsyncClient, case: dict) -> dict:
    await reset_database()
    await seed_database()
    started = time.perf_counter()
    if case.get("kind") == "stream_health":
        response = await client.post(
            "/api/v1/simulations/stream-health",
            json={
                "session_id": case["session_id"],
                "scenario": case["scenario"],
                "samples": case.get("samples", []),
            },
        )
    else:
        response = await client.post(
            "/api/v1/simulations/comments",
            json={"session_id": case["session_id"], "comments": [{"user_name": case["id"], "body": body} for body in case["comments"]]},
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    payload = response.json()
    trace_id = payload["trace_id"]
    logs = (await client.get("/api/v1/agent-action-logs", params={"trace_id": trace_id})).json()["items"] if trace_id else []
    if case.get("expected_alert_type", "").startswith("MIXED_"):
        runs = (await client.get("/api/v1/agent-runs")).json()["items"]
        logs = []
        for run in runs:
            logs.extend((await client.get("/api/v1/agent-action-logs", params={"trace_id": run["trace_id"]})).json()["items"])
    alerts = (await client.get("/api/v1/ops-alerts", params={"session_id": case["session_id"], "status": "OPEN"})).json()["items"]
    approvals = (await client.get("/api/v1/approval-tasks", params={"status": "PENDING"})).json()["items"]
    notes = (await client.get("/api/v1/speaker-notes", params={"session_id": case["session_id"]})).json()["items"]
    tools = [log["tool_name"] for log in logs if log["action_type"] == "TOOL_CALL"]
    return {
        "case": case,
        "trace_id": trace_id,
        "logs": logs,
        "alerts": alerts,
        "approvals": approvals,
        "notes": notes,
        "tools": tools,
        "latency_ms": latency_ms,
        "scores": {
            "alert_type_accuracy": grade_alert_type(case, alerts),
            "subagent_dispatch_coverage": grade_subagent_dispatch_coverage(case, logs),
            "tool_selection_accuracy": grade_tool_selection(case, tools),
            "tool_call_recall": grade_tool_call_recall(case, tools),
            "tool_call_precision": grade_tool_call_precision(case, tools),
            "tool_execution_success_rate": grade_tool_execution_success_rate(logs),
            "forbidden_tool_block_rate": grade_forbidden_tool_block(case, tools),
            "risk_gate_accuracy": grade_risk_gate_accuracy(case, logs),
            "approval_trigger_accuracy": grade_approval_trigger(case, approvals),
            "policy_grounding_accuracy": grade_policy_grounding(case, logs),
            "speaker_note_created_rate": 1.0 if (not notes if case.get("expected_no_alert") else notes) else 0.0,
            "trace_completeness": grade_trace_completeness(logs),
        },
    }


async def main() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        results = [await run_case(client, case) for case in read_cases()]

    metrics = {}
    for key in results[0]["scores"]:
        metrics[key] = statistics.mean(result["scores"][key] for result in results)
    metrics["p95_end_to_end_latency"] = max(result["latency_ms"] for result in results)
    metrics["avg_agent_steps_per_alert"] = statistics.mean(len(result["logs"]) for result in results)

    lines = ["# Meerkat Eval Report", "", "| metric | value |", "|---|---:|"]
    for key, value in metrics.items():
        lines.append(f"| {key} | {value:.2f} |")
    failed = [
        result
        for result in results
        if any(score < 1.0 for score in result["scores"].values())
    ]
    lines.extend(["", "## Failed Cases", ""])
    if failed:
        for result in failed:
            bad_scores = {key: value for key, value in result["scores"].items() if value < 1.0}
            lines.append(f"- {result['case']['id']}: scores={bad_scores}, trace={result['trace_id']}")
    else:
        lines.append("- None")
    lines.extend(["", "## Cases", ""])
    for result in results:
        lines.append(f"- {result['case']['id']}: trace={result['trace_id']}, tools={','.join(result['tools'])}")
    report = "\n".join(lines) + "\n"
    (EVAL_DIR / "report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
