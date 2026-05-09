from __future__ import annotations

import argparse
import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from acceptance_config import AcceptanceConfig
from assertions import AcceptanceFailure, require
from backend_client import BackendClient
from owncast_client import OwncastClient


CAPSTONE_DIR = Path(__file__).resolve().parents[2]


class AcceptanceRunner:
    def __init__(self, offline: bool, owncast_required: bool, only_probe_loop: bool):
        self.offline = offline
        self.owncast_required = owncast_required
        self.only_probe_loop = only_probe_loop
        self.config = AcceptanceConfig()
        self.backend = BackendClient(self.config.backend_url)
        self.owncast = OwncastClient(self.config.owncast_url, self.config.admin_user, self.config.admin_password)
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.skipped: list[str] = []
        self.trace_ids: list[str] = []

    async def run(self) -> int:
        print("Meerkat v1 Acceptance\n")
        self.reset_demo_database()
        checks = [self.check_probe_loop] if self.only_probe_loop else [
            self.check_backend_health,
            self.check_owncast_health,
            self.check_owncast_webhook,
            self.check_coupon_flow,
            self.check_price_approval,
            self.check_probe_loop,
            self.check_trace_replay,
            self.check_dashboard_summary,
            self.check_eval_metrics,
        ]
        for check in checks:
            name = check.__name__.removeprefix("check_").replace("_", " ")
            try:
                skipped = await check()
            except AcceptanceFailure as exc:
                self.failed.append(f"{name}: {exc}")
                print(f"[FAIL] {name} -> {exc}")
            except Exception as exc:
                self.failed.append(f"{name}: {type(exc).__name__}: {exc}")
                print(f"[FAIL] {name} -> {type(exc).__name__}: {exc}")
            else:
                if skipped:
                    self.skipped.append(name)
                    print(f"[SKIP] {name} -> {skipped}")
                else:
                    self.passed.append(name)
                    print(f"[PASS] {name}")
        self.write_report()
        if self.failed:
            print("\nResult: FAIL")
            return 1
        print("\nResult: PASS")
        return 0

    def reset_demo_database(self) -> None:
        backend_dir = CAPSTONE_DIR / "meerkat_backend"
        python = CAPSTONE_DIR / "meerkat_backend" / ".venv" / "bin" / "python"
        subprocess.run([str(python), "-m", "app.db.init_db", "--reset"], cwd=backend_dir, check=True)
        subprocess.run([str(python), "-m", "app.db.seed"], cwd=backend_dir, check=True)

    async def check_backend_health(self) -> str | None:
        payload = await self.backend.get("/api/v1/health")
        require(payload.get("ok") is True, "backend health did not return ok=true")
        return None

    async def check_owncast_health(self) -> str | None:
        if self.offline and not self.owncast_required:
            return "offline mode"
        payload = await self.owncast.status()
        require("versionNumber" in payload, "Owncast status missing versionNumber")
        return None

    async def check_owncast_webhook(self) -> str | None:
        if self.offline and not self.owncast_required:
            return "offline mode"
        hooks = await self.owncast.webhooks()
        require(any(self.config.webhook_url == hook.get("url") for hook in hooks), f"webhook not configured for {self.config.webhook_url}")
        return None

    async def check_coupon_flow(self) -> str | None:
        payload = await self.backend.post("/api/v1/simulations/comments", {"session_id": 1, "comments": [{"user_name": "acc1", "body": "券领不了"}, {"user_name": "acc2", "body": "为什么没有 50 元券"}, {"user_name": "acc3", "body": "点进去没有券啊"}]})
        require(payload.get("agent_runs_triggered", 0) >= 1, "coupon comments did not trigger AgentRun")
        self.trace_ids.append(payload["trace_id"])
        return None

    async def check_price_approval(self) -> str | None:
        payload = await self.backend.post("/api/v1/simulations/comments", {"session_id": 1, "comments": [{"user_name": "acc1", "body": "主播说 99"}, {"user_name": "acc2", "body": "页面是 129"}, {"user_name": "acc3", "body": "价格不对"}]})
        require(payload.get("agent_runs_triggered", 0) >= 1, "price comments did not trigger AgentRun")
        self.trace_ids.append(payload["trace_id"])
        return None

    async def check_probe_loop(self) -> str | None:
        await self.backend.post("/api/v1/stream/probe/start", {"session_id": 1})
        samples = []
        for _ in range(3):
            samples.append(await self.backend.post("/api/v1/stream/probe/tick", {"session_id": 1}))
        require(len(samples) == 3 and samples[-1].get("sample"), "probe loop did not produce three samples")
        opened = await self.backend.post("/api/v1/simulations/stream-health", {"session_id": 1, "scenario": "stream_down", "samples": []})
        require(opened.get("stream_incident", {}).get("status") == "OPEN", "stream lifecycle did not open an incident")
        require(opened.get("trace_id"), "stream lifecycle did not create a stream-monitor trace")
        self.trace_ids.append(opened["trace_id"])
        timeline = await self.backend.get(f"/api/v1/traces/{opened['trace_id']}/timeline")
        actions = {event["action_type"] for event in timeline["events"]}
        require("SUBAGENT_RESULT" in actions and "TOOL_RESULT" in actions, "stream incident trace missing agent/tool results")
        recovered = await self.backend.post(
            "/api/v1/simulations/stream-health",
            {
                "session_id": 1,
                "scenario": "stream_recover",
                "samples": [
                    {"is_live": True, "probe_status": "OK", "audio_present": True, "video_present": True},
                    {"is_live": True, "probe_status": "OK", "audio_present": True, "video_present": True},
                    {"is_live": True, "probe_status": "OK", "audio_present": True, "video_present": True},
                ],
            },
        )
        incident_id = opened["stream_incident"]["id"]
        require(recovered.get("stream_incident", {}).get("id") == incident_id, "stream recovery did not target the open incident")
        require(recovered.get("stream_incident", {}).get("status") == "RECOVERED", "stream lifecycle did not recover the incident")
        incident = await self.backend.get(f"/api/v1/stream/incidents/{incident_id}")
        require(incident.get("status") == "RECOVERED", "stream incident was not persisted as recovered")
        return None

    async def check_trace_replay(self) -> str | None:
        require(bool(self.trace_ids), "no trace ids from previous checks")
        payload = await self.backend.get(f"/api/v1/traces/{self.trace_ids[-1]}/timeline")
        actions = {event["action_type"] for event in payload["events"]}
        require({"TOOL_CALL", "TOOL_RESULT", "SUBAGENT_RESULT"} <= actions, "trace missing required event types")
        return None

    async def check_dashboard_summary(self) -> str | None:
        payload = await self.backend.get("/api/v1/dashboard/summary")
        require("stream_health" in payload and "agent" in payload and "ops" in payload, "dashboard summary missing v1 sections")
        return None

    async def check_eval_metrics(self) -> str | None:
        result = subprocess.run(["make", "eval"], cwd=CAPSTONE_DIR, text=True, capture_output=True, check=False)
        require(result.returncode == 0, result.stdout[-1000:] + result.stderr[-1000:])
        require("forbidden_tool_block_rate | 1.00" in result.stdout, "eval did not preserve forbidden tool block rate")
        return None

    def write_report(self) -> None:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=CAPSTONE_DIR, text=True, capture_output=True, check=False).stdout.strip()
        report = [
            "# Meerkat v1 Acceptance Report",
            "",
            f"run time: {datetime.now(timezone.utc).isoformat()}",
            f"git commit: {commit}",
            f"Owncast URL: {self.config.owncast_url}",
            f"Backend URL: {self.config.backend_url}",
            f"passed checks: {self.passed}",
            f"failed checks: {self.failed}",
            f"skipped checks: {self.skipped}",
            f"trace ids: {self.trace_ids}",
            "known gaps: none from acceptance/eval; Owncast shows offline unless an RTMP source is pushing",
            "",
        ]
        (CAPSTONE_DIR / "acceptance_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--owncast-required", action="store_true")
    parser.add_argument("--only-probe-loop", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(AcceptanceRunner(args.offline, args.owncast_required, args.only_probe_loop).run()))


if __name__ == "__main__":
    main()
