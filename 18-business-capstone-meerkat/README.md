# Step 18: Meerkat

> Meerkat：狐獴哨兵，直播间运营异常处理多智能体系统。

Meerkat 不是从零实现直播系统，而是接入开源直播服务 Owncast，把直播评论流转成 Agent 可处理的业务事件；随后使用 Python/FastAPI 实现 Meerkat Backend，并基于 OpenClaw Runtime 的事件驱动、工具调用、多智能体 dispatch、风险控制和 trace 思路构建 Meerkat Agent。

学习者最终得到的不是一个聊天机器人，而是一个能写进简历的 Agent 工程项目：Agent 监听实时评论、查询商品/库存/优惠券、检索运营 SOP、生成主播话术、创建运营告警、发起人工审批，并记录 trace 和 eval 指标。

## Architecture

```text
Owncast CHAT / simulated comments
  -> Meerkat Backend saves comments
  -> deterministic classifier creates candidate anomaly
  -> AgentTask
  -> commander agent
  -> live_triage / product / coupon / policy / risk / script agents
  -> ToolRegistry
  -> ops_alerts / speaker_notes / approval_tasks / agent_action_logs
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
python -m app.db.init_db
python -m app.db.seed
uvicorn app.main:app --host 0.0.0.0 --port 8018 --reload
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

## Demos Without Owncast

```bash
python scripts/run_demo_coupon.py
python scripts/run_demo_inventory.py
python scripts/run_demo_price.py
```

Each demo resets and seeds the local SQLite database, injects comments through `/api/v1/simulations/comments`, runs the Agent workflow, then prints the trace id, created entities, and tool calls.

## Business Flows

Coupon unavailable:

```text
comments -> COUPON_UNAVAILABLE -> get_live_products -> get_coupon_detail
-> search_policy_docs -> create_ops_alert -> create_action_proposal
-> create_speaker_note -> create_approval_task
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

## OpenClaw Agent Capability Mapping

| OpenClaw capability | Meerkat implementation |
|---|---|
| Event-driven Agent Workflow | Owncast CHAT webhook and simulated comments trigger AgentTask |
| Tool Calling | comments, products, inventory, coupons, alerts, speaker notes, approvals are Agent tools |
| Multi-Agent Dispatch | commander dispatches live_triage / product / coupon / policy / risk / script |
| RAG / SOP Grounding | policy_agent searches `meerkat_agent/knowledge/*.md` |
| Human-in-the-loop | price changes, coupon time changes, product hiding, and system messages are blocked or moved to approval |
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
8. risk -> create_approval_task
```

Query trace logs:

```bash
curl "http://localhost:8018/api/v1/agent-action-logs?trace_id=tr_xxx"
```

## Eval

```bash
cd meerkat_agent/evals
python run_eval.py
```

The eval checks Agent behavior quality: alert type, subagent dispatch, expected tools, tool execution, forbidden tool block, risk gate, approval trigger, SOP grounding, speaker note creation, and trace completeness. It writes `report.md`.

Latest local eval reports 1.00 for alert type, subagent dispatch, tool recall, tool precision, tool execution, forbidden-tool blocking, risk gate, approval trigger, SOP grounding, and trace completeness on the three MVP cases.

## Risk Levels

| Tool type | Handling |
|---|---|
| READ_ONLY | execute directly |
| LOW_RISK_WRITE | execute and audit |
| HIGH_RISK_WRITE | dry-run or approval |
| DESTRUCTIVE | blocked; create approval instead |

## Resume

Use [RESUME.md](./RESUME.md) as the Agent-first resume template. Do not fill metric placeholders until local eval has been run.
