# Meerkat Handoff

Last updated: 2026-05-09

## Current State

`18-business-capstone-meerkat/` is now a working Step 18 business capstone for the `build-your-own-openclaw` repo.

The implemented product is:

```text
Meerkat：狐獴哨兵，直播间运营异常处理多智能体系统
```

The core shape is agent-first:

```text
Owncast CHAT / Owncast status + HLS probe / simulated comments
  -> Meerkat Backend saves comments
  -> deterministic classifier marks candidate anomaly
  -> anomaly window creates AgentTask
  -> MeerkatAgentRunner creates AgentRun
  -> commander dispatches live_triage / product / coupon / policy / risk / script
  -> ToolRegistry executes read/low-risk tools
  -> ToolRegistry blocks destructive tools and creates approval tasks
  -> tools create ops_alerts / action_proposals / speaker_notes / approval_tasks
  -> agent_action_logs records trace
```

The detector does not directly create final alerts, speaker notes, or approval tasks. It only produces candidate anomaly events that become `AgentTask`.

## What Was Implemented

### Owncast integration

- Added `docker-compose.yml` with Owncast on ports `8080` and `1935`.
- Added `extra_hosts` for `host.docker.internal` so Owncast-in-Docker can call a host backend.
- Added `POST /api/v1/integrations/owncast/webhook`.
- Configured Owncast Admin API webhook id `1`:

```text
http://host.docker.internal:8018/api/v1/integrations/owncast/webhook
events = CHAT, STREAM_STARTED, STREAM_STOPPED, STREAM_TITLE_UPDATED
```

- Webhook handles:
  - `CHAT`
  - `STREAM_STARTED`
  - `STREAM_STOPPED`
- `CHAT` events are saved to `owncast_events`, normalized into `live_comments`, and linked through `owncast_event_id`.
- Webhook parser is tolerant of common Owncast field variants such as `type`, `eventData.body`, `eventData.user.displayName`, and message ids.
- Real Owncast chat was verified through Owncast's public chat registration API plus `/ws` WebSocket, not only by direct webhook curl.

### Backend business system

Implemented Python/FastAPI + SQLAlchemy async + SQLite backend under `meerkat_backend/`.

Core persisted objects:

- `live_sessions`
- `products`
- `live_session_products`
- `sku_inventory`
- `coupons`
- `owncast_events`
- `live_comments`
- `ops_alerts`
- `speaker_notes`
- `action_proposals`
- `approval_tasks`
- `agent_tasks`
- `agent_runs`
- `agent_action_logs`

Core APIs include:

- health
- Owncast webhook
- simulation comments
- live sessions
- live products
- comment search/recent
- products
- inventory
- coupons
- ops alerts
- speaker notes
- action proposals
- approval tasks
- agent tasks/runs/logs
- minimal `/dashboard`

### Agent runtime path

Implemented `meerkat_agent/runner.py` and runtime helpers:

- `MeerkatAgentRunner`
- `ToolRegistry`
- `RiskGuard`
- runtime schemas
- trace logging through `agent_action_logs`

Current tools:

- `search_recent_comments`
- `get_live_products`
- `get_product_detail`
- `get_product_inventory`
- `get_coupon_detail`
- `search_policy_docs`
- `create_ops_alert`
- `create_action_proposal`
- `create_speaker_note`
- `create_approval_task`
- `send_owncast_system_message`
- `change_coupon_time` approval-only
- `change_product_price` approval-only
- `hide_product_from_live` approval-only
- `stop_stream` approval-only

High-risk or destructive operations such as `change_coupon_time`, `change_product_price`, `hide_product_from_live`, and `stop_stream` are registered in ToolRegistry with schemas, allowed agents, and approval gates. Calling them returns `APPROVAL_REQUIRED`, creates a pending `approval_task`, and does not execute a destructive handler.

`send_owncast_system_message` is registered as a medium-risk write tool. By default it records an Owncast dry-run trace instead of sending, controlled by `OWNCAST_DRY_RUN` and `OWNCAST_AUTO_SEND`.

### Stream probe and Console APIs

Implemented:

- `POST /api/v1/stream/probe/run-once`
- `GET /api/v1/stream/health/latest`
- `GET /api/v1/stream/incidents`
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/traces/{trace_id}/timeline`

`run-once` probes Owncast `/api/status` and the HLS playlist, persists stream health samples, and triggers `stream_monitor_agent` when failures cross the incident threshold.

### Multi-agent roles

Role docs exist under `meerkat_agent/agents/`:

- `commander`
- `live_triage`
- `product`
- `coupon`
- `policy`
- `risk`
- `script`

The MVP runner is deterministic, but the trace records the intended agent structure:

- `AGENT_TASK_CREATED`
- `AGENT_RUN_STARTED`
- `SUBAGENT_DISPATCH`
- `SUBAGENT_RESULT`
- `TOOL_CALL`
- `TOOL_RESULT`
- `POLICY_RETRIEVED`
- `RISK_DECISION`
- `ACTION_PLAN_CREATED`
- `ALERT_CREATED`
- `SPEAKER_NOTE_CREATED`
- `APPROVAL_CREATED`
- `AGENT_RUN_FINISHED`

### Business demos

Implemented three demo scripts:

- `scripts/run_demo_coupon.py`
- `scripts/run_demo_inventory.py`
- `scripts/run_demo_price.py`

Current behavior:

```text
coupon demo:
  tools = search_recent_comments,get_live_products,get_coupon_detail,search_policy_docs,create_ops_alert,create_action_proposal,create_speaker_note,create_approval_task,send_owncast_system_message
  creates COUPON_UNAVAILABLE alert
  creates speaker note
  creates DESTRUCTIVE approval
  records OWNCAST_MESSAGE_DRY_RUN
  does not execute change_coupon_time

inventory demo:
  tools = search_recent_comments,get_live_products,get_product_detail,get_product_inventory,search_policy_docs,create_ops_alert,create_action_proposal,create_speaker_note
  creates INVENTORY_UNAVAILABLE alert
  creates speaker note
  creates no approval
  does not execute hide_product_from_live

price demo:
  tools = search_recent_comments,get_live_products,get_product_detail,search_policy_docs,create_ops_alert,create_speaker_note,create_action_proposal,create_approval_task
  creates PRICE_MISMATCH alert
  creates speaker note
  creates DESTRUCTIVE approval
  does not execute change_product_price
```

### Eval

Implemented under `meerkat_agent/evals/`:

- `cases.jsonl`
- `graders.py`
- `run_eval.py`
- `report_example.md`

Eval checks agent behavior, not just database rows:

- alert type
- subagent dispatch coverage
- tool selection
- tool recall
- tool precision
- tool execution success
- forbidden tool blocking
- risk gate accuracy
- approval trigger
- policy grounding
- speaker note creation
- trace completeness
- latency
- average agent steps per alert

Latest local eval output:

```text
alert_type_accuracy = 0.94
subagent_dispatch_coverage = 0.96
tool_selection_accuracy = 0.96
tool_call_recall = 0.96
tool_call_precision = 0.96
tool_execution_success_rate = 1.00
forbidden_tool_block_rate = 1.00
risk_gate_accuracy = 0.96
approval_trigger_accuracy = 1.00
policy_grounding_accuracy = 0.94
speaker_note_created_rate = 0.96
trace_completeness = 1.00
p95_end_to_end_latency = 88 ms
avg_agent_steps_per_alert = 23.20
```

Known failed cases remain `inventory_003`, `inventory_006`, and `known_gap_mixed_001`.

### Docs and repo integration

Updated:

- root `README.md`
- `web/src/lib/constants.ts`
- `18-business-capstone-meerkat/README.md`
- `18-business-capstone-meerkat/RESUME.md`

Root README now lists Step 18 under Phase 5. The web constants now expose Phase 5 with Step 18.

`RESUME.md` is agent-first and includes the latest eval metrics. It does not frame the project as a plain FastAPI CRUD backend.

## Verification Already Run

From `18-business-capstone-meerkat/meerkat_backend`:

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
16 passed in 1.17s
```

From `18-business-capstone-meerkat/meerkat_agent/evals`:

```bash
../../meerkat_backend/.venv/bin/python run_eval.py
```

Result: metrics listed above, with known gaps still visible in `meerkat_agent/evals/report.md`.

Demo scripts run successfully:

```bash
.venv/bin/python ../scripts/run_demo_coupon.py
.venv/bin/python ../scripts/run_demo_inventory.py
.venv/bin/python ../scripts/run_demo_price.py
../meerkat_backend/.venv/bin/python ../scripts/run_demo_owncast_message.py
```

Web build was verified from `web/`:

```bash
npm run build
```

The first build attempt failed because the sandbox could not fetch Google Fonts. After running with network permission, the build passed:

```text
Compiled successfully
Generated static pages: 194/194
```

Ignored generated/runtime files were checked:

```bash
git check-ignore -v \
  18-business-capstone-meerkat/meerkat.db \
  18-business-capstone-meerkat/meerkat_backend/.venv/pyvenv.cfg \
  18-business-capstone-meerkat/owncast_data/owncast.db \
  18-business-capstone-meerkat/meerkat_agent/evals/report.md
```

All are ignored by `18-business-capstone-meerkat/.gitignore`.

Dry-run add was checked:

```bash
git add -n 18-business-capstone-meerkat README.md web/src/lib/constants.ts
```

It includes source/docs/tests/scripts and excludes db/venv/Owncast runtime data.

Owncast Admin API webhook configuration was verified:

```bash
curl -s -u admin:abc123 http://127.0.0.1:8080/api/admin/webhooks
```

Result:

```json
[{"url":"http://host.docker.internal:8018/api/v1/integrations/owncast/webhook","events":["CHAT","STREAM_STARTED","STREAM_STOPPED","STREAM_TITLE_UPDATED"],"id":1}]
```

Real Owncast chat end-to-end verification was run by registering Owncast chat users and sending spaced `CHAT` WebSocket messages:

```text
券领不了
为什么没有 50 元券
点进去没有券啊
```

Meerkat persisted the real Owncast chat comments with `owncast_event_id` and Owncast message ids:

```text
comment 7: owncast_event_id=7, external_message_id=sZt0qV0vg, matched_type=COUPON_UNAVAILABLE
comment 8: owncast_event_id=8, external_message_id=6UeA3V0vg, matched_type=COUPON_UNAVAILABLE
comment 9: owncast_event_id=9, external_message_id=ksm1340DRz, matched_type=COUPON_UNAVAILABLE
```

The real Owncast chat stream triggered a fresh Agent run:

```text
trace_id = tr_20260509002058_3adf38
root_agent = commander
status = SUCCEEDED
alert_type = COUPON_UNAVAILABLE
tool_calls = search_recent_comments,get_live_products,get_coupon_detail,search_policy_docs,create_ops_alert,create_action_proposal,create_speaker_note,create_approval_task
created_entities = ops_alert_id=2, speaker_note_id=2, approval_task_id=2
```

## Current Running Services

At the time of this handoff:

Owncast is running through Docker Compose:

```text
18-business-capstone-meerkat-owncast-1
image: owncast/owncast:latest
ports: 8080, 1935
status: Up
```

Owncast status endpoint:

```text
http://127.0.0.1:8080/api/status
versionNumber = 0.2.5
online = false
```

Meerkat Backend was started temporarily for HTTP smoke and then stopped:

```text
http://127.0.0.1:8018
command = .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8018
```

Health endpoint returns:

```json
{"ok": true, "service": "meerkat-backend"}
```

One manual webhook curl was sent after the server started:

```text
POST /api/v1/integrations/owncast/webhook
body: "券领不了"
result: inserted=1, agent_runs_triggered=0
```

This is expected because coupon anomaly threshold is three matching comments.

## Files That Matter Most

Backend:

- `meerkat_backend/app/main.py`
- `meerkat_backend/app/api/router.py`
- `meerkat_backend/app/db/base.py`
- `meerkat_backend/app/db/init_db.py`
- `meerkat_backend/app/db/seed.py`
- `meerkat_backend/app/services/comment_classifier.py`
- `meerkat_backend/app/services/anomaly_detector.py`
- `meerkat_backend/app/services/simulation_service.py`
- `meerkat_backend/app/services/owncast_webhook_service.py`
- `meerkat_backend/app/services/agent_task_service.py`
- `meerkat_backend/app/services/trace_service.py`
- `meerkat_backend/tests/test_agent_first_flow.py`

Agent:

- `meerkat_agent/runner.py`
- `meerkat_agent/runtime/tool_registry.py`
- `meerkat_agent/runtime/risk_guard.py`
- `meerkat_agent/tools/meerkat_tools.py`
- `meerkat_agent/tools/owncast_tools.py`
- `meerkat_agent/knowledge/*.md`
- `meerkat_agent/evals/run_eval.py`
- `meerkat_agent/evals/graders.py`
- `meerkat_agent/evals/cases.jsonl`

Docs:

- `README.md`
- `RESUME.md`
- this `HANDOFF.md`

## Git State

Current branch:

```text
main...origin/main
```

Modified tracked files:

```text
README.md
web/src/lib/constants.ts
```

Untracked new capstone:

```text
18-business-capstone-meerkat/
```

No commit has been made.

## What Still Needs Doing

### Required before calling this production-like

1. Verify full compose backend path.

`docker compose up -d owncast` was verified. The local backend path was verified. The `meerkat-backend` compose service has not been fully re-verified after the latest code changes.

2. Decide whether to keep the local backend running.

Current backend process is useful for manual testing. If you need to stop it:

```bash
kill 81387
```

3. Decide whether to keep Owncast running.

To stop it:

```bash
cd 18-business-capstone-meerkat
docker compose down
```

### Good next engineering improvements

1. Add a small Dockerfile for `meerkat-backend` instead of relying on `python:3.11-slim` plus `pip install -e .` at container startup.
2. Add tests for `STREAM_STARTED` and `STREAM_STOPPED`.
3. Add tests for `send_owncast_system_message` dry-run and missing-token behavior.
4. Add action-proposal checks to eval, not only tests.
5. Add a trace replay endpoint that groups logs by `trace_id` into a readable workflow tree.
6. Add stronger dedupe bucket logic. Current dedupe prevents repeated OPEN alerts for the same session/type/target, but the `dedupe_key` created by tools is trace-specific.
7. Add a `LINK_BROKEN` flow if the capstone needs a fourth demo. Classifier enum support exists, but the runner currently handles only coupon, inventory, and price flows.
8. Improve `/dashboard` from raw JSON panes into a minimal operator view. Do not turn it into a full frontend project unless the project direction changes.
9. If this will be submitted as a clean repo change, run `git add -n` again and commit only source/docs/tests/scripts, not generated db/cache/runtime files.

## Quick Commands For The Next Agent

Install and seed:

```bash
cd 18-business-capstone-meerkat/meerkat_backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m app.db.init_db
python -m app.db.seed
```

Run backend:

```bash
cd 18-business-capstone-meerkat/meerkat_backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8018
```

Run Owncast:

```bash
cd 18-business-capstone-meerkat
docker compose up -d owncast
```

Run tests:

```bash
cd 18-business-capstone-meerkat/meerkat_backend
.venv/bin/python -m pytest -q
```

Run eval:

```bash
cd 18-business-capstone-meerkat/meerkat_agent/evals
../../meerkat_backend/.venv/bin/python run_eval.py
```

Run demos:

```bash
cd 18-business-capstone-meerkat/meerkat_backend
.venv/bin/python ../scripts/run_demo_coupon.py
.venv/bin/python ../scripts/run_demo_inventory.py
.venv/bin/python ../scripts/run_demo_price.py
```

Manual webhook smoke:

```bash
curl -s -X POST http://127.0.0.1:8018/api/v1/integrations/owncast/webhook \
  -H 'Content-Type: application/json' \
  -d '{"type":"CHAT","eventData":{"id":"msg-1","body":"券领不了","user":{"displayName":"viewer-1","id":"user-1"}}}'
```

## Completion Boundary

The capstone is implemented and locally verified as an agent-first MVP:

- Owncast service runs.
- Backend service runs.
- Simulated comments trigger AgentTask and AgentRun.
- Owncast Admin API webhook is configured.
- Real Owncast WebSocket chat triggers webhook delivery into Meerkat.
- Real Owncast chat comments persist with `owncast_event_id` and Owncast message ids.
- Three demos create business objects through Agent tools.
- Tests pass.
- Eval passes with agent behavior metrics.
- Web tutorial build passes.

The remaining gap is not core implementation. It is packaging/runtime polish: verify the optional `meerkat-backend` Docker Compose service path if you want one-command full-stack startup instead of the current verified mode of Owncast in Docker plus backend on the host.
