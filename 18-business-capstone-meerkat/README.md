# Step 18: Meerkat

> Meerkat：狐獴哨兵，直播运营现场指挥多智能体系统。

Meerkat 不是从零实现直播系统，而是接入开源直播服务 Owncast，把直播评论流和推流健康样本转成 Agent 可处理的业务事件；随后使用 Python/FastAPI 实现 Meerkat Backend，并基于 OpenClaw Runtime 的事件驱动、工具调用、多智能体 dispatch、风险控制和 trace 思路构建 Meerkat Agent。

学习者最终得到的不是一个聊天机器人，而是一个能写进简历的 Agent 工程项目：Agent 监听实时评论、主动识别推流异常、查询商品/库存/优惠券、检索运营 SOP、生成主播/场控话术、创建运营告警、发起人工审批、生成下播复盘，并记录 trace 和 eval 指标。

## Architecture

```text
Owncast CHAT / Owncast status + HLS probe / simulated comments
  -> Meerkat Backend saves comments
  -> deterministic classifier / stream detector creates candidate anomaly
  -> AgentTask
  -> commander agent
  -> stream_monitor / live_triage / product / coupon / policy / risk / script / report agents
  -> ToolRegistry schema / allowed-agent / approval guard
  -> stream_incidents / ops_alerts / speaker_notes / approval_tasks / post_live_reports / agent_action_logs
```

Backend 只负责业务数据、事件接入、工具 API 和状态持久化。告警、话术、审批必须由 Meerkat Agent 通过 tools 创建，`anomaly_detector` 只创建候选异常和 AgentTask。

## Why Owncast

Owncast 提供自托管直播、聊天、Webhook 和 Integration API。它承担直播基础设施，Meerkat 聚焦直播运营异常处理和 Agent 工具链，避免把 capstone 扩成完整直播平台或电商平台。

## Quick Start

```bash
cd 18-business-capstone-meerkat
cp .env.example .env
docker compose up -d owncast

cd meerkat_backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m app.db.init_db --reset
python -m app.db.seed
uvicorn app.main:app --host 0.0.0.0 --port 8018 --reload
```

Equivalent Make targets:

```bash
make owncast-up
make backend-setup
make backend
make check-owncast
make check-backend
```

Open:

```text
FastAPI docs: http://localhost:8018/docs
Meerkat Console: http://localhost:8018/dashboard
Owncast: http://localhost:8080
```

## Owncast Webhook

1. Open Owncast admin.
2. Create a webhook.
3. If backend runs inside compose, use `http://meerkat-backend:8018/api/v1/integrations/owncast/webhook`.
4. If backend runs on the host, use `http://host.docker.internal:8018/api/v1/integrations/owncast/webhook`.
5. Enable `CHAT`, `STREAM_STARTED`, `STREAM_STOPPED`, and `STREAM_TITLE_UPDATED`.

The webhook parser tolerates missing fields and accepts the common Owncast shape:

```json
{"type":"CHAT","eventData":{"body":"券领不了","user":{"displayName":"viewer001"}}}
```

Local smoke test:

```bash
make smoke-webhook
python scripts/setup_owncast_webhook.py
```

`setup_owncast_webhook.py --configure` first tries the Owncast Admin API. For
the local Owncast version used here, if that write endpoint is unavailable it
falls back to updating `owncast_data/owncast.db`, then Owncast should be
restarted before `make check-owncast-webhook`.

## Stream Probe

Real probe path:

```text
POST /api/v1/stream/probe/run-once
  -> GET Owncast /api/status
  -> GET HLS playlist
  -> persist stream_probe_runs / stream_health_samples
  -> create StreamIncident when failed samples cross threshold
  -> trigger stream_monitor_agent
```

Useful commands:

```bash
make ffmpeg-stream
make ffmpeg-stream-docker
make ffmpeg-stream-stop
make ffmpeg-no-audio
make probe-hls
make probe-ffprobe
```

`make ffmpeg-stream` uses local `ffmpeg` when available and falls back to a
Docker ffmpeg container. If Owncast opens but says the stream is offline, the
Owncast service is up but no RTMP source is currently pushing.

`/api/v1/stream/health/latest`, `/api/v1/stream/incidents`, `/api/v1/dashboard/summary`, and `/api/v1/traces/{trace_id}/timeline` provide the Console-facing state.

## Demos Without Owncast

```bash
python scripts/run_demo_coupon.py
python scripts/run_demo_inventory.py
python scripts/run_demo_price.py
python scripts/run_demo_stream_down.py
python scripts/run_demo_no_audio.py
python scripts/run_demo_post_live_report.py
```

Each demo resets and seeds the local SQLite database, injects comments or stream samples through simulation APIs, runs the Agent workflow, then prints the trace id, created entities, tool calls, and eval hint.

## Business Flows

Coupon unavailable:

```text
comments -> COUPON_UNAVAILABLE -> get_live_products -> get_coupon_detail
-> search_policy_docs -> create_ops_alert -> create_action_proposal
-> create_speaker_note -> ToolRegistry blocks change_coupon_time
-> create_approval_task -> send_owncast_system_message dry-run
```

Inventory unavailable:

```text
comments -> INVENTORY_UNAVAILABLE -> get_live_products -> get_product_detail
-> get_product_inventory -> search_policy_docs -> create_ops_alert
-> create_action_proposal -> create_speaker_note
```

Price mismatch:

```text
comments -> PRICE_MISMATCH -> get_live_products -> get_product_detail
-> search_policy_docs -> create_ops_alert -> create_speaker_note
-> create_action_proposal -> create_approval_task
```

Stream interrupted:

```text
stream_health_samples -> STREAM_INTERRUPTED -> stream_monitor_agent
-> get_stream_incident_context -> search_policy_docs -> create_ops_alert
-> create_speaker_note
```

Post-live report:

```text
ops_alerts / stream_incidents / speaker_notes / approvals
-> report_agent -> post_live_report -> memory_updates
```

## OpenClaw Agent Capability Mapping

| OpenClaw capability | Meerkat implementation |
|---|---|
| Event-driven Agent Workflow | Owncast CHAT webhook, simulated comments, and stream health probes trigger AgentTask |
| Tool Calling | comments, products, inventory, coupons, alerts, speaker notes, approvals are Agent tools |
| Multi-Agent Dispatch | commander dispatches stream_monitor / live_triage / product / coupon / policy / risk / script / report |
| Stream Health | Owncast status and HLS probes create stream incidents and stream_monitor_agent tasks |
| RAG / SOP Grounding | policy_agent searches `meerkat_agent/knowledge/*.md` |
| Human-in-the-loop | ToolRegistry blocks destructive tools and creates approval tasks instead of executing them |
| Trace / Observability | `agent_action_logs` records subagent dispatch, tool calls, policy retrieval, risk decisions, and final actions |
| Eval | `cases.jsonl` and graders verify subagent dispatch, tool choice, tool execution, forbidden tools, risk gate, approval trigger, policy grounding, and trace completeness |
| Concurrency / Dedupe | anomaly windows and open-alert checks prevent repeated alerts for the same active issue |

## Trace Example

```text
Trace tr_...
1. commander -> live_triage: COUPON_UNAVAILABLE
2. coupon -> get_coupon_detail(coupon_id=1)
3. policy -> search_policy_docs("优惠券 未生效")
4. risk -> DESTRUCTIVE, requires approval
5. commander -> create_ops_alert
6. risk -> create_action_proposal
7. script -> create_speaker_note
8. risk -> APPROVAL_REQUIRED(change_coupon_time)
9. risk -> create_approval_task
10. script -> send_owncast_system_message(dry_run)
```

Query trace logs:

```bash
curl "http://localhost:8018/api/v1/traces/tr_xxx"
```

## Eval

```bash
cd meerkat_agent/evals
python run_eval.py
```

The eval checks Agent behavior quality across 50 cases: alert type, stream health, false positives, subagent dispatch, expected tools, tool execution, forbidden tool block, risk gate, approval trigger, SOP grounding, speaker note creation, and trace completeness. It writes `report.md` and keeps failed cases visible.

Latest local eval:

```text
alert_type_accuracy = 1.00
subagent_dispatch_coverage = 1.00
tool_selection_accuracy = 1.00
tool_call_recall = 1.00
tool_call_precision = 1.00
tool_execution_success_rate = 1.00
forbidden_tool_block_rate = 1.00
risk_gate_accuracy = 1.00
approval_trigger_accuracy = 1.00
policy_grounding_accuracy = 1.00
speaker_note_created_rate = 1.00
trace_completeness = 1.00
p95_end_to_end_latency = 35 ms
```

Known failed cases are documented in `meerkat_agent/evals/report.md`; current local eval has no failed cases.

## Risk Levels

| Tool type | Handling |
|---|---|
| READ_ONLY | execute directly |
| LOW_RISK_WRITE | execute and audit |
| HIGH_RISK_WRITE | dry-run or approval |
| DESTRUCTIVE | ToolRegistry returns `APPROVAL_REQUIRED`; no destructive handler runs |

## Resume

Use [RESUME.md](./RESUME.md) as the Agent-first resume template. Do not fill metric placeholders until local eval has been run.

## Roadmap

The full product plan has been moved into [ROADMAP.md](./ROADMAP.md). It is the source of truth for v0.2-v1.0 scope and the final acceptance checklist.
