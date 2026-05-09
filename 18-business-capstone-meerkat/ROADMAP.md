# OpenClaw Meerkat 最终形态与完整建设计划

> 产品名：**Meerkat**  
> 中文名：**狐獴哨兵**  
> 完整项目名：**OpenClaw Meerkat**  
> 副标题：**直播运营现场指挥多智能体系统**  
> 英文副标题：**Multi-Agent System for Livestream Operations Command**

---

## 0. 文档目的

这份文档用于指导后续施工 Agent / Codex 将当前 Meerkat 项目从“评论异常 demo”升级为一个完整、可展示、可写进简历、适合投递国内互联网大厂 Agent 开发岗的业务型 Agent 项目。

Meerkat 的目标不是做一个简单 MVP，也不是只做一个“能跑通的 demo”。最终它应该成为一个完整的 Agent 工程项目，体现以下能力：

- Python 后端工程能力；
- 真实业务事件流接入；
- 直播运营业务建模；
- 多智能体任务编排；
- Agent 工具调用治理；
- SOP / 知识库 grounding；
- human-in-the-loop 风险审批；
- trace / replay / observability；
- eval / dataset / grader；
- 最小可展示的运营工作台；
- 可直接转换为简历项目的完整闭环。

---

## 1. 最终产品定位

### 1.1 一句话定位

**Meerkat 是一个接入 Owncast 的直播运营现场指挥 Agent。它不是只检测评论，也不是只监控推流，而是把推流健康、评论异常、商品、库存、优惠券、价格口径和运营 SOP 串成一个可诊断、可处置、可审批、可追踪、可评测的多智能体业务系统。**

### 1.2 更工程化的定位

Meerkat 基于 Owncast 接入直播与评论流，基于 Python/FastAPI 实现直播运营后端，基于 OpenClaw Runtime 构建多智能体系统。它将 Owncast 事件、推流健康探测结果、实时评论、商品配置、库存、优惠券和直播 SOP 转化为 `AgentTask`，由 `commander_agent` 编排多个子 Agent，完成直播现场异常感知、诊断、建议、处置、审批和复盘。

### 1.3 Meerkat 不是什么

Meerkat 不是：

- 完整直播系统；
- 完整电商交易系统；
- 普通客服机器人；
- 关键词评论分类器；
- 单纯的 Owncast 插件；
- 单纯的监控告警系统；
- 只展示 LLM 对话能力的 demo。

Meerkat 是：

- 直播运营业务系统；
- Agent-first 的业务 capstone；
- OpenClaw Runtime 的业务落地项目；
- 直播现场异常处理和运营协同系统；
- Agent 工具治理、审批、trace、eval 的综合展示项目。

---

## 2. 系统边界

### 2.1 Owncast 的职责

Owncast 负责直播和聊天基础设施：

- RTMP 推流；
- Web 播放；
- 聊天区；
- Webhook 事件；
- Integration API；
- 直播开始/停止事件；
- 聊天消息输入；
- 通过 API 发送系统消息或集成消息。

Owncast 不负责商品、优惠券、库存、直播脚本、运营告警、审批、Agent 决策。

### 2.2 Meerkat Backend 的职责

Meerkat Backend 是直播运营业务系统，负责：

- 直播间和直播场次；
- 商品和 SKU 库存；
- 优惠券；
- 商品别名；
- 主播口播脚本；
- Owncast Webhook 接收；
- 实时评论存储；
- 评论异常候选；
- 推流健康样本；
- 推流异常事件；
- 运营告警；
- 主播/场控话术；
- 动作建议；
- 审批任务；
- Agent task；
- Agent run；
- Agent trace；
- 下播复盘报告。

Backend 不应该直接完成智能决策。Backend 提供状态和工具，Agent 负责诊断和决策。

### 2.3 Meerkat Agent 的职责

Meerkat Agent 基于 OpenClaw Runtime，负责：

- 将事件转为 AgentTask；
- commander agent 编排；
- 子 Agent 派发；
- 推流异常诊断；
- 评论异常聚类；
- 商品/库存/优惠券查询；
- SOP 检索；
- 风险判断；
- 主播话术生成；
- 工具调用；
- 审批创建；
- trace 写入；
- eval 数据生成；
- 下播复盘生成。

### 2.4 Meerkat Console 的职责

Meerkat Console 是最小运营工作台，负责展示：

- 当前直播状态；
- Owncast 连接状态；
- 推流健康状态；
- 实时评论流；
- 评论异常聚类；
- 当前讲解商品；
- 当前优惠券；
- Agent 执行链路；
- 工具调用；
- SOP 命中；
- 风险判断；
- 运营告警；
- 主播话术；
- 审批任务；
- 下播复盘。

---

## 3. 最终业务画面

### 3.1 场景一：开播前巡检

运营输入：

```text
帮我检查今晚 8 点直播间有没有问题。
```

Meerkat 应执行：

1. 查询今晚的 `live_session`；
2. 查询直播间挂载商品；
3. 检查商品是否上架；
4. 检查库存是否满足预计直播销量；
5. 检查优惠券是否生效；
6. 检查优惠券是否覆盖直播商品；
7. 检查直播脚本口播价是否和商品页面价一致；
8. 检查 Owncast 是否可访问；
9. 生成开播前巡检报告；
10. 创建库存、优惠券、价格口径相关告警；
11. 对高风险修正动作创建审批任务。

期望输出示例：

```text
今晚直播间共 12 个商品、4 张优惠券。

发现 3 个问题：
1. 商品 A 库存仅 5 件，但直播脚本预计售卖 200 件。
2. 优惠券 coupon_1023 生效时间为 21:00，晚于直播开始时间 20:00。
3. 商品 B 页面价 129 元，脚本口播价 99 元，存在价格口径风险。

我已创建 3 个运营告警，并为优惠券提前生效和价格口径调整创建了审批任务。
```

### 3.2 场景二：推流健康检测

直播中，OBS 断开、黑屏、无声、分片停更、码率暴跌，Meerkat 应该主动发现，而不是等待评论区反馈。

Meerkat 应执行：

1. Owncast `STREAM_STARTED` 触发 stream monitor；
2. `stream_probe_service` 定时探测 HLS / 播放地址；
3. 记录 `stream_health_samples`；
4. 异常持续 N 次后创建 `stream_incident`；
5. `stream_monitor_agent` 诊断异常类型；
6. `policy_agent` 检索推流异常 SOP；
7. `risk_agent` 判断动作风险；
8. `script_agent` 生成场控/主播话术；
9. `commander_agent` 创建运营告警；
10. 必要时通过 Meerkat Console 或 Owncast system message 提醒。

至少支持的异常类型：

```text
STREAM_UNAVAILABLE       直播不可访问
STREAM_INTERRUPTED       非预期断流
SEGMENT_STALLED          HLS 分片停更
NO_VIDEO                 无视频轨 / 黑屏
NO_AUDIO                 无音频轨
BITRATE_DROP             码率异常下降
HIGH_LATENCY             延迟过高
STREAM_RECOVERED         已恢复
```

期望输出示例：

```text
检测到当前直播发生推流异常：STREAM_INTERRUPTED。

证据：
- live_session 仍处于 LIVE 状态；
- 最近 3 次 HLS probe 均失败；
- Owncast 收到 STREAM_STOPPED 事件；
- 异常开始时间：20:37:12。

建议：
1. 场控确认 OBS 是否断开；
2. 主播暂停商品讲解；
3. 使用备用话术安抚观众；
4. 如果 60 秒内未恢复，升级为 P1 运营告警。

我已创建推流异常告警，并生成场控话术。
```

### 3.3 场景三：评论运营异常

评论区出现：

```text
券领不了
为什么没有 50 元券
主播不是说有券吗
点进去没有啊
```

Meerkat 应执行：

1. `comment_window_service` 聚合 3-5 分钟评论窗口；
2. `anomaly_candidate_service` 召回候选异常；
3. `comment_triage_agent` 判断是否是同一类异常；
4. 识别异常类型 `COUPON_UNAVAILABLE`；
5. `product_agent` 查询当前讲解商品；
6. `coupon_agent` 查询直播间绑定优惠券；
7. `policy_agent` 检索优惠券 SOP；
8. `risk_agent` 判断是否允许自动处理；
9. `script_agent` 生成主播/场控话术；
10. `commander_agent` 创建 ops_alert、speaker_note、approval_task。

期望输出示例：

```text
3 分钟内检测到 27 条“优惠券不可领取”相关评论。

诊断结果：
- 异常类型：COUPON_UNAVAILABLE
- 涉及优惠券：coupon_1023
- 当前状态：未生效
- 生效时间：21:00
- 直播开始时间：20:00

建议：
1. 场控提示主播改口径：“优惠券将在 21:00 生效”；
2. 如果需要提前生效，发起优惠券配置变更审批；
3. 暂时不要承诺用户当前即可领取。

我已创建 P1 运营告警、主播话术和优惠券变更审批任务。
```

### 3.4 场景四：价格口径风险

评论区出现：

```text
主播说 99，页面怎么是 129？
这不是虚假宣传吗？
```

Meerkat 应执行：

1. 识别异常类型 `PRICE_MISMATCH`；
2. 查询当前讲解商品；
3. 查询商品页面价；
4. 查询直播脚本口播价；
5. 查询优惠券后价格；
6. 检索 `price_policy.md`；
7. 判断为高风险；
8. 不直接改价；
9. 创建 ops_alert；
10. 创建 approval_task；
11. 生成主播补救话术。

关键原则：

```text
Agent 可以建议、创建审批、生成话术。
Agent 不能直接改价、改券、下架商品。
```

期望输出示例：

```text
检测到价格口径风险。

证据：
- 当前讲解商品：商品 B
- 页面价：129 元
- 直播脚本口播价：99 元
- 当前没有可用优惠券能将价格降至 99 元
- 5 分钟内有 18 条评论反馈价格不一致

该问题涉及价格承诺风险，我已创建高风险运营告警和人工审批任务。
建议主播使用补救话术：“刚才价格口径需要核实，请大家以商品详情页为准，我们马上确认。”
```

### 3.5 场景五：下播复盘

下播后运营输入：

```text
帮我生成今晚直播复盘，重点看异常、处理耗时和后续改进。
```

Meerkat 应执行：

1. 汇总直播场次；
2. 汇总推流健康样本；
3. 汇总 stream incidents；
4. 汇总评论异常 cluster；
5. 汇总 ops alerts；
6. 汇总 approval tasks；
7. 汇总 speaker notes；
8. 汇总 Agent traces；
9. 计算 time_to_alert 和 time_to_recommendation；
10. 生成 post_live_report；
11. 将高频异常写入 memory，供下次直播使用。

期望输出示例：

```text
本场直播共 2 小时 12 分钟。

检测结果：
- 推流异常：1 次
- 评论运营异常：3 次
- 价格/优惠券配置风险：2 次
- 高风险审批任务：2 个
- 平均异常发现耗时：42 秒
- 平均建议生成耗时：9 秒

最高风险问题：
商品 B 价格口径不一致，已进入人工审批。

改进建议：
1. 开播前增加优惠券生效时间校验；
2. 开播前自动比对口播价和页面价；
3. 对商品 B 建立历史风险提醒；
4. 对当前主播增加价格口径确认流程。
```

---

## 4. 最终系统架构

```text
                  ┌───────────────────────┐
                  │        Owncast         │
                  │  RTMP / Web / Chat     │
                  └───────────┬───────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
 Owncast Webhook       Stream Probe          Owncast API
 CHAT/START/STOP       HLS/ffprobe/status    send message/history
        │                     │                     ▲
        ▼                     ▼                     │
┌─────────────────────────────────────────────────────────┐
│                  Meerkat Backend                        │
│ live_sessions / products / coupons / inventory           │
│ comments / stream_health_samples / incidents             │
│ ops_alerts / speaker_notes / approval_tasks              │
│ agent_tasks / agent_runs / agent_action_logs             │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Meerkat Agent                         │
│ commander_agent                                          │
│ ├─ stream_monitor_agent                                  │
│ ├─ comment_triage_agent                                  │
│ ├─ product_agent                                         │
│ ├─ coupon_agent                                          │
│ ├─ policy_agent                                          │
│ ├─ risk_agent                                            │
│ ├─ script_agent                                          │
│ └─ report_agent                                          │
│                                                         │
│ ToolRegistry + RiskGuard + ApprovalGuard + Trace         │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Meerkat Console                        │
│ live health / comments / anomalies / alerts / trace      │
│ speaker notes / approvals / post-live report             │
└─────────────────────────────────────────────────────────┘
```

核心原则：

```text
Backend 不直接智能决策。
Backend 保存业务状态、接收事件、提供工具。
Agent 负责诊断、决策、生成建议、触发动作。
Console 负责展示业务现场和 Agent 执行链路。
```

---

## 5. 最终目录结构

```text
18-business-capstone-meerkat/
  README.md
  RESUME.md
  ARCHITECTURE.md
  ROADMAP.md
  docker-compose.yml
  Makefile
  .env.example

  meerkat_backend/
    pyproject.toml
    app/
      main.py
      core/
        config.py
        security.py
        logging.py
      db/
        base.py
        session.py
        init_db.py
        seed.py
      models/
        user.py
        live_room.py
        live_session.py
        product.py
        product_alias.py
        inventory.py
        coupon.py
        live_script.py
        owncast_event.py
        live_comment.py
        comment_cluster.py
        stream_probe_run.py
        stream_health_sample.py
        stream_incident.py
        ops_alert.py
        speaker_note.py
        action_proposal.py
        approval_task.py
        agent_task.py
        agent_run.py
        agent_action_log.py
        post_live_report.py
      schemas/
      api/
        v1/
          integrations/
            owncast.py
          live_sessions.py
          products.py
          coupons.py
          inventory.py
          comments.py
          stream_health.py
          incidents.py
          ops_alerts.py
          speaker_notes.py
          approvals.py
          agent_tasks.py
          agent_logs.py
          reports.py
          simulations.py
          dashboard.py
      services/
        owncast_webhook_service.py
        owncast_api_client.py
        stream_probe_service.py
        stream_health_detector.py
        comment_window_service.py
        anomaly_candidate_service.py
        live_session_service.py
        business_rule_service.py
        post_live_report_service.py
      repositories/
      tests/

  meerkat_agent/
    pyproject.toml
    runtime/
      agent_runtime.py
      agent_context.py
      dispatcher.py
      tool_registry.py
      risk_guard.py
      approval_guard.py
      trace_writer.py
      memory_store.py
      structured_output.py
    agents/
      commander/
        AGENT.md
        schema.py
        runner.py
      stream_monitor/
        AGENT.md
        schema.py
        runner.py
      comment_triage/
        AGENT.md
        schema.py
        runner.py
      product/
        AGENT.md
        schema.py
        runner.py
      coupon/
        AGENT.md
        schema.py
        runner.py
      policy/
        AGENT.md
        schema.py
        runner.py
      risk/
        AGENT.md
        schema.py
        runner.py
      script/
        AGENT.md
        schema.py
        runner.py
      report/
        AGENT.md
        schema.py
        runner.py
    tools/
      backend_tools.py
      owncast_tools.py
      stream_tools.py
      tool_schemas.py
    knowledge/
      live_sop.md
      stream_health_sop.md
      coupon_policy.md
      price_policy.md
      inventory_policy.md
      approval_policy.md
    evals/
      cases/
        stream_health.jsonl
        comment_anomaly.jsonl
        tool_safety.jsonl
        workflow.jsonl
        false_positive.jsonl
      graders.py
      run_eval.py
      report.md
    traces/

  meerkat_console/
    README.md
    optional_frontend_or_server_rendered_dashboard/

  scripts/
    run_demo_pre_live_check.py
    run_demo_stream_down.py
    run_demo_no_audio.py
    run_demo_coupon.py
    run_demo_inventory.py
    run_demo_price.py
    run_demo_post_live_report.py
```

---

## 6. 后端领域模型要求

### 6.1 基础直播模型

#### `live_rooms`

用于描述一个 Owncast 直播间。

字段建议：

```text
id
name
owncast_base_url
owncast_stream_url
owncast_api_token_encrypted
status
owner_user_id
created_at
updated_at
```

#### `live_sessions`

用于描述一场直播。

```text
id
live_room_id
title
status: SCHEDULED | LIVE | ENDED | CANCELLED
scheduled_start_at
started_at
ended_at
current_product_id
operator_user_id
created_at
updated_at
```

#### `live_scripts`

用于保存主播口播脚本和讲解顺序。

```text
id
session_id
product_id
sequence_no
spoken_price
spoken_coupon_text
selling_points
risk_notes
created_at
updated_at
```

### 6.2 商品、库存、优惠券模型

#### `products`

```text
id
name
external_product_id
page_url
page_price
status: ACTIVE | INACTIVE | HIDDEN
created_at
updated_at
```

#### `product_aliases`

用于把“3号链接”“蓝色款”“那个锅”等评论表达映射到商品。

```text
id
product_id
alias
session_id
created_at
```

#### `sku_inventory`

```text
id
product_id
sku_name
available_stock
reserved_stock
sold_count
updated_at
```

#### `coupons`

```text
id
name
amount
threshold_amount
start_at
end_at
status
applicable_product_ids
created_at
updated_at
```

### 6.3 评论和异常聚类模型

#### `live_comments`

```text
id
session_id
owncast_message_id
user_name
body
raw_payload_json
created_at
```

#### `comment_clusters`

```text
id
session_id
alert_type
status: CANDIDATE | CONFIRMED | DISMISSED
confidence
evidence_comment_ids
target_product_id
target_coupon_id
summary
created_at
updated_at
```

### 6.4 推流健康模型

#### `stream_probe_runs`

```text
id
session_id
probe_type: OWNCAST_STATUS | HLS | FFPROBE
status: OK | FAILED | PARTIAL
error_message
started_at
finished_at
duration_ms
```

#### `stream_health_samples`

```text
id
session_id
probe_run_id
is_live
video_present
audio_present
bitrate_kbps
fps
width
height
last_segment_age_ms
probe_status
probe_error
sampled_at
```

#### `stream_incidents`

```text
id
session_id
incident_type
severity: P0 | P1 | P2 | P3
status: OPEN | INVESTIGATING | RECOVERED | RESOLVED | FALSE_POSITIVE
evidence_json
created_by: SYSTEM | AGENT | HUMAN
trace_id
created_at
updated_at
resolved_at
```

### 6.5 运营处置模型

#### `ops_alerts`

```text
id
session_id
alert_type
severity
status: OPEN | ACKED | RESOLVED | DISMISSED
title
summary
evidence_json
created_by_agent_run_id
created_at
updated_at
```

#### `speaker_notes`

```text
id
session_id
ops_alert_id
target: ANCHOR | FIELD_CONTROL | OPERATOR
message
risk_level
send_status: DRAFT | DRY_RUN | SENT | APPROVAL_REQUIRED
owncast_message_id
created_by_agent_run_id
created_at
updated_at
```

#### `action_proposals`

```text
id
session_id
ops_alert_id
action_type
risk_level
arguments_json
reason
status: PROPOSED | APPROVAL_REQUIRED | APPROVED | REJECTED | EXECUTED
created_by_agent_run_id
created_at
updated_at
```

#### `approval_tasks`

```text
id
session_id
action_proposal_id
approval_type
risk_level
status: PENDING | APPROVED | REJECTED | CANCELLED
reason
requested_by_agent_run_id
reviewed_by_user_id
created_at
updated_at
```

### 6.6 Agent 执行模型

#### `agent_tasks`

```text
id
session_id
task_type
source_type: OWNCAST_WEBHOOK | STREAM_PROBE | SIMULATION | USER_REQUEST | CRON
payload_json
status: PENDING | RUNNING | SUCCEEDED | FAILED | CANCELLED
created_at
updated_at
```

#### `agent_runs`

```text
id
agent_task_id
root_agent_name
status
trace_id
started_at
ended_at
duration_ms
result_json
error_message
```

#### `agent_action_logs`

```text
id
trace_id
agent_run_id
agent_name
event_type
tool_name
input_summary
output_summary
risk_level
duration_ms
status
error
created_at
```

#### `post_live_reports`

```text
id
session_id
title
summary_markdown
metrics_json
recommendations_json
created_by_agent_run_id
created_at
```

---

## 7. Agent 架构

### 7.1 Agent 列表

最终必须包含：

```text
commander_agent
stream_monitor_agent
comment_triage_agent
product_agent
coupon_agent
policy_agent
risk_agent
script_agent
report_agent
```

### 7.2 commander_agent

职责：

- 接收 AgentTask；
- 判断任务类型；
- 决定要派发哪些子 Agent；
- 汇总子 Agent 输出；
- 决定调用哪些工具；
- 负责最终业务动作；
- 生成 AgentRun 结果。

输入示例：

```json
{
  "task_type": "COMMENT_ANOMALY",
  "session_id": 1,
  "payload": {
    "candidate_comment_ids": [101, 102, 103],
    "alert_type_hint": "COUPON_UNAVAILABLE"
  }
}
```

输出示例：

```json
{
  "decision": "CREATE_ALERT_AND_SPEAKER_NOTE",
  "created_alert_id": 12,
  "created_speaker_note_id": 7,
  "created_approval_task_id": 3,
  "summary": "Detected coupon unavailable issue and created alert."
}
```

### 7.3 stream_monitor_agent

职责：

- 分析推流健康样本；
- 判断异常类型；
- 提取证据；
- 判断是否恢复；
- 给出处理建议。

输入：

```json
{
  "session_id": 1,
  "recent_samples": [
    {
      "is_live": false,
      "probe_status": "FAILED",
      "probe_error": "HLS playlist unavailable"
    }
  ],
  "owncast_events": ["STREAM_STOPPED"]
}
```

输出：

```json
{
  "incident_type": "STREAM_INTERRUPTED",
  "severity": "P1",
  "confidence": 0.92,
  "evidence": [
    "session status is LIVE",
    "received STREAM_STOPPED event",
    "last 3 HLS probes failed"
  ],
  "recommended_actions": [
    "ask field control to check OBS",
    "pause product introduction",
    "send fallback speaker note"
  ]
}
```

### 7.4 comment_triage_agent

职责：

- 聚合评论窗口；
- 判断评论是否指向同一异常；
- 提取证据评论；
- 映射商品别名；
- 输出异常类型和置信度。

输出示例：

```json
{
  "alert_type": "COUPON_UNAVAILABLE",
  "confidence": 0.86,
  "evidence_comment_ids": [101, 104, 108],
  "target": {
    "product_id": 3,
    "coupon_id": 1,
    "alias": "3号链接"
  },
  "summary": "多名用户在 3 分钟内反馈当前讲解商品的 50 元券无法领取。",
  "should_create_alert": true
}
```

### 7.5 product_agent

职责：

- 查询商品；
- 解析商品别名；
- 查询库存；
- 查询页面价；
- 查询直播脚本口播价；
- 判断商品是否处于当前直播挂载状态。

### 7.6 coupon_agent

职责：

- 查询优惠券；
- 检查生效时间；
- 检查失效时间；
- 检查是否适用当前商品；
- 检查门槛金额；
- 判断是否与主播口径一致。

### 7.7 policy_agent

职责：

- 检索直播运营 SOP；
- 检索价格政策；
- 检索优惠券政策；
- 检索库存异常处理政策；
- 检索推流异常处理 SOP；
- 返回引用依据。

输出示例：

```json
{
  "policy_name": "coupon_policy.md",
  "matched_sections": [
    {
      "section": "优惠券未生效处理",
      "evidence": "优惠券未到生效时间时，不得承诺用户当前可领取。"
    }
  ],
  "grounding_summary": "该问题应提示主播修正口径，如需提前生效必须进入审批。"
}
```

### 7.8 risk_agent

职责：

- 判断动作风险；
- 决定是否需要审批；
- 禁止高风险动作直接执行；
- 输出风险解释。

风险等级：

```text
READ_ONLY
LOW_RISK_WRITE
MEDIUM_RISK_WRITE
HIGH_RISK_WRITE
DESTRUCTIVE
```

输出示例：

```json
{
  "risk_level": "HIGH_RISK_WRITE",
  "requires_approval": true,
  "reason": "修改优惠券生效时间会影响实际交易权益，必须人工审批。",
  "allowed_action": "CREATE_APPROVAL_TASK",
  "forbidden_actions": ["CHANGE_COUPON_TIME_DIRECTLY"]
}
```

### 7.9 script_agent

职责：

- 生成主播话术；
- 生成场控话术；
- 生成运营内部备注；
- 保持低风险、谨慎、事实一致；
- 避免承诺未审批动作。

示例输出：

```json
{
  "target": "FIELD_CONTROL",
  "message": "请提醒主播：当前优惠券将在 21:00 生效，请不要承诺用户现在即可领取。",
  "risk_level": "LOW_RISK_WRITE"
}
```

### 7.10 report_agent

职责：

- 汇总下播数据；
- 汇总异常；
- 汇总处理动作；
- 汇总工具调用；
- 生成复盘报告；
- 写入 memory。

---

## 8. ToolRegistry 与工具治理

### 8.1 Tool 定义

每个 tool 必须包含：

```text
name
description
input_schema
output_schema
risk_level
allowed_agents
requires_approval
timeout_ms
retry_policy
idempotency_key_strategy
audit_policy
```

示例：

```json
{
  "name": "create_ops_alert",
  "description": "Create a livestream operations alert.",
  "risk_level": "LOW_RISK_WRITE",
  "allowed_agents": ["commander"],
  "requires_approval": false,
  "timeout_ms": 3000
}
```

### 8.2 工具类型

#### READ_ONLY

```text
get_live_session
get_current_product
get_product_detail
get_product_inventory
get_coupon_detail
search_comments
get_stream_health_latest
search_policy_docs
```

#### LOW_RISK_WRITE

```text
create_ops_alert
create_speaker_note
create_post_live_report
```

#### MEDIUM_RISK_WRITE

```text
send_owncast_system_message
create_action_proposal
```

#### HIGH_RISK_WRITE

```text
change_coupon_time
hide_product_from_live
update_live_script_price
```

#### DESTRUCTIVE

```text
change_product_price
take_down_product
stop_stream
delete_comment
```

### 8.3 调用前检查

ToolRegistry 调用工具前必须执行：

```text
schema validation
agent permission check
risk guard
approval guard
idempotency check
timeout control
retry policy
trace log
```

### 8.4 高风险工具行为

高风险动作不允许直接执行。

正确流程：

```text
Agent requests change_coupon_time
  -> ToolRegistry detects requires_approval=true
  -> ToolRegistry does not execute real action
  -> ToolRegistry creates approval_task
  -> trace records blocked_by_approval_guard
  -> Console shows pending approval
```

验收标准：

```text
1. risk_agent 判断高风险后，ToolRegistry 不能直接执行高风险工具。
2. forbidden tool case 在 eval 中能被拦截。
3. 低风险 speaker_note 可以直接创建。
4. medium risk Owncast system message 根据配置决定 dry-run 或审批。
5. 每次工具调用都能在 agent_action_logs 中追踪。
```

---

## 9. 推流健康检测模块

### 9.1 探测方式

分三级：

#### 第一级：Owncast 事件

```text
STREAM_STARTED
STREAM_STOPPED
STREAM_TITLE_UPDATED
```

#### 第二级：HTTP / HLS 探测

```text
Owncast Web 是否可访问
播放地址是否可访问
HLS playlist 是否存在
HLS segment 是否持续更新
last_segment_age_ms 是否超过阈值
```

#### 第三级：ffprobe 探测

```text
是否有 video stream
是否有 audio stream
bitrate
fps
width
height
duration
```

### 9.2 ProbeResult

```json
{
  "is_live": true,
  "video_present": true,
  "audio_present": true,
  "bitrate_kbps": 2400,
  "fps": 30.0,
  "width": 1920,
  "height": 1080,
  "last_segment_age_ms": 800,
  "probe_status": "OK",
  "probe_error": null
}
```

### 9.3 异常规则

```text
STREAM_UNAVAILABLE:
  连续 3 次 probe failed。

SEGMENT_STALLED:
  HLS segment 超过阈值未更新。

NO_VIDEO:
  ffprobe 没有 video stream。

NO_AUDIO:
  ffprobe 没有 audio stream。

BITRATE_DROP:
  bitrate 低于配置阈值，并持续 N 次。

STREAM_INTERRUPTED:
  session 仍处于 LIVE，但收到 STREAM_STOPPED。

STREAM_RECOVERED:
  异常后连续 N 次 probe OK。
```

### 9.4 验收 demo

```bash
make demo-stream-down
make demo-stream-recover
make demo-no-audio
make demo-segment-stalled
```

---

## 10. 评论异常处理模块

### 10.1 分层设计

不要把关键词规则伪装成 Agent。正确设计是：

```text
live_comments
  -> comment_window_service
  -> anomaly_candidate_service
  -> comment_triage_agent
  -> commander_agent
```

### 10.2 异常类型

```text
COUPON_UNAVAILABLE
INVENTORY_UNAVAILABLE
PRICE_MISMATCH
LINK_BROKEN
PRODUCT_NOT_FOUND
STREAM_QUALITY_COMPLAINT
NOISE_ONLY
UNKNOWN
```

### 10.3 验收标准

```text
1. 单条“券领不了”不直接告警。
2. 多条相同语义评论才创建候选异常。
3. “3号链接拍不了”能通过 product_alias 映射到 product。
4. 噪声评论不创建 alert。
5. 混合异常能拆出 coupon + price 两个候选。
```

---

## 11. Owncast 双向闭环

### 11.1 输入

```text
CHAT
STREAM_STARTED
STREAM_STOPPED
STREAM_TITLE_UPDATED
USER_JOINED
```

### 11.2 输出工具

```text
send_owncast_system_message
send_owncast_standard_message
get_owncast_chat_history
get_owncast_connected_clients
set_owncast_stream_title
```

### 11.3 风险策略

```text
LOW_RISK：
  发送内部场控提示到 Meerkat Console。

MEDIUM_RISK：
  Owncast system message 默认 dry_run。
  运营确认后真实发送。

HIGH_RISK：
  不允许 Agent 直接发对外承诺口径。
  必须创建 approval_task。
```

### 11.4 验收 demo

```bash
make demo-owncast-message
```

期望效果：

```text
1. 评论区刷“券领不了”。
2. Meerkat 生成主播话术。
3. Console 展示话术。
4. 如果 OWNCAST_DRY_RUN=false 且风险低，发送 Owncast system message。
5. trace 记录 message body、risk level、dry_run、tool result。
```

---

## 12. Meerkat Console

### 12.1 目标

Console 是业务画面，不能省略。它可以是轻量前端，也可以先用 server-rendered dashboard，但必须展示 Agent 工作流。

### 12.2 页面结构

左侧：直播状态

```text
当前直播间
当前场次
开播时间
Owncast 连接状态
推流健康状态
当前讲解商品
当前优惠券
```

中间：实时评论和异常聚类

```text
实时评论流
comment cluster
候选异常
确认异常
噪声评论
```

右侧：Agent 操作区

```text
Agent 正在分析什么
子 Agent 执行时间线
工具调用结果
SOP 命中
risk decision
```

底部：处置区

```text
ops_alerts
speaker_notes
approval_tasks
action_proposals
post_live_report
```

### 12.3 验收标准

```text
1. 运行 demo_coupon 时，Console 能看到评论进入、异常形成、Agent 分析、告警创建、话术生成。
2. 运行 demo_stream_down 时，Console 能看到推流健康状态变红、incident 创建、Agent 生成处理建议。
3. 点击某个 alert 能看到完整 trace。
```

---

## 13. Trace、Replay 与可观测性

### 13.1 Trace 事件类型

```text
EVENT_RECEIVED
AGENT_TASK_CREATED
AGENT_RUN_STARTED
SUBAGENT_DISPATCHED
SUBAGENT_RESULT
TOOL_CALL
TOOL_RESULT
POLICY_RETRIEVED
RISK_DECISION
APPROVAL_CREATED
OWNCAST_MESSAGE_SENT
AGENT_RUN_COMPLETED
AGENT_RUN_FAILED
```

### 13.2 Trace 字段

```text
trace_id
agent_run_id
agent_name
event_type
tool_name
input_summary
output_summary
risk_level
duration_ms
status
error
created_at
```

### 13.3 Replay API

```http
GET /api/v1/traces/{trace_id}
```

返回：

```text
完整时间线
每个 Agent 输入输出
每个工具调用
SOP 命中
risk decision
最终动作
```

### 13.4 验收标准

```text
1. 每个 demo 都能打印 trace_id。
2. Console 能按 trace_id 展示 timeline。
3. eval 能检查 trace_completeness。
4. trace 能回答“为什么创建这个审批任务”。
```

---

## 14. 长期记忆与直播复盘

### 14.1 Memory 维度

```text
by_live_room:
  这个直播间历史常见异常。

by_product:
  这个商品历史价格口径、库存、投诉、券问题。

by_coupon:
  某张券历史失效、未生效、不可用问题。

by_anchor:
  主播常见口播风格、易错口径。

by_policy:
  SOP 更新历史。
```

### 14.2 下播复盘报告

`post_live_report` 应包含：

```text
summary
stream_incidents
comment_anomalies
actions_taken
approval_pending
unresolved_issues
suggested_pre_live_checks
memory_updates
```

### 14.3 验收标准

```text
1. 第二次直播同一个商品时，Agent 能提示“该商品上次直播出现过价格口径问题”。
2. 下播报告能生成结构化 Markdown。
3. memory 写入可在 trace 中看到。
```

---

## 15. Eval 体系

### 15.1 Case 分类

```text
stream_health_cases.jsonl
  stream_down
  stream_recovered
  no_audio
  no_video
  segment_stalled
  bitrate_drop
  false_alarm_recover

comment_anomaly_cases.jsonl
  coupon_unavailable
  inventory_unavailable
  price_mismatch
  link_broken
  product_alias
  noisy_comments_no_alert
  mixed_coupon_and_price

tool_safety_cases.jsonl
  should_not_change_price_directly
  should_not_change_coupon_time_directly
  should_not_hide_product_directly
  should_create_approval_for_high_risk_action
  should_send_low_risk_speaker_note

workflow_cases.jsonl
  should_dispatch_stream_monitor
  should_dispatch_policy_agent
  should_dispatch_risk_agent
  should_create_trace
  should_generate_speaker_note

false_positive_cases.jsonl
  one_user_complaint_only
  joke_comment
  resolved_issue
  unrelated_chat
```

### 15.2 指标

```text
stream_incident_detection_accuracy
comment_anomaly_detection_accuracy
tool_selection_precision
tool_selection_recall
forbidden_tool_block_rate
approval_trigger_accuracy
policy_grounding_accuracy
speaker_note_quality
trace_completeness
false_positive_rate
time_to_alert
time_to_recommendation
p95_agent_latency
```

### 15.3 报告

输出：

```text
meerkat_agent/evals/report.md
```

报告必须包含：

```text
总分
分类指标
失败 case
失败原因
下一步修复建议
```

### 15.4 验收标准

```text
1. 至少 50 个 eval case。
2. 不允许只展示 100%。
3. report.md 里必须有失败样例。
4. 简历里的指标必须来自 eval report。
```

---

## 16. 完整建设计划

下面不是简单 MVP 计划，而是把 Meerkat 做成最终简历级 Agent 项目的完整路线。

---

### Phase 0：产品语言和边界重构

目标：把项目从“直播评论异常 demo”统一改成“直播运营现场指挥 Agent”。

要做：

```text
1. README 重写产品定位。
2. ROADMAP.md 写清楚最终形态。
3. RESUME.md 只写真实已实现能力，不提前吹。
4. 统一 Meerkat、Meerkat Backend、Meerkat Agent、Meerkat Console、Owncast Adapter 命名。
5. 明确 Owncast 只负责直播/聊天基础设施，Meerkat 不从零写直播系统。
```

验收标准：

```text
README 第一屏能讲清楚：
- Meerkat 是什么；
- 为什么接 Owncast；
- Agent 在哪里；
- Backend 在哪里；
- 最终 demo 怎么跑；
- 不是什么。
```

---

### Phase 1：后端领域模型升级

目标：让后端成为直播运营业务系统，不只是评论数据库。

要做：

```text
1. 增加 live_rooms。
2. 增加 live_sessions。
3. 增加 products。
4. 增加 product_aliases。
5. 增加 sku_inventory。
6. 增加 coupons。
7. 增加 live_scripts。
8. 增加 stream_probe_runs。
9. 增加 stream_health_samples。
10. 增加 stream_incidents。
11. 增加 post_live_reports。
12. 完善 ops_alerts、speaker_notes、approval_tasks、agent_tasks、agent_runs、agent_action_logs。
```

验收标准：

```text
python -m app.db.seed 后，至少有：
- 1 个 Owncast live_room；
- 2 个 live_session；
- 8 个 product；
- 10 个 product_alias；
- 5 个 coupon；
- 2 份 live_script；
- 可触发 coupon / inventory / price / stream 异常的数据。
```

---

### Phase 2：直播推流健康检测版

目标：Meerkat 能主动发现推流异常。

要做：

```text
1. 实现 stream_probe_service。
2. 实现 stream_health_detector。
3. 实现 stream_incident_service。
4. 接入 Owncast STREAM_STARTED / STREAM_STOPPED。
5. 支持 HLS probe。
6. 支持 ffprobe，或者先提供 mock ffprobe adapter。
7. 生成 stream_health_samples。
8. 异常持续 N 次后创建 stream_incident。
9. 触发 stream_monitor_agent。
```

支持异常：

```text
STREAM_UNAVAILABLE
STREAM_INTERRUPTED
SEGMENT_STALLED
NO_VIDEO
NO_AUDIO
BITRATE_DROP
HIGH_LATENCY
STREAM_RECOVERED
```

验收命令：

```bash
make demo-stream-down
make demo-stream-recover
make demo-no-audio
make demo-segment-stalled
```

验收标准：

```text
停止推流后，Meerkat 自动创建 stream_incident、ops_alert、speaker_note，并写入 trace。
```

---

### Phase 3：评论异常从关键词升级为 Agent 诊断

目标：关键词只做候选召回，真正诊断由 Agent 完成。

要做：

```text
1. comment_classifier 降级为 candidate generator。
2. 实现 comment_window_service。
3. 实现 anomaly_candidate_service。
4. 新增 comment_clusters。
5. comment_triage_agent 输出结构化诊断。
6. 支持商品别名映射。
7. 支持噪声评论过滤。
8. 支持混合异常拆分。
```

验收标准：

```text
1. 单条“券领不了”不直接告警。
2. 多条相同语义评论才创建候选异常。
3. “3号链接拍不了”能映射到 product。
4. 噪声评论不创建 alert。
5. 混合异常能拆出 coupon + price 两个候选。
```

---

### Phase 4：真正接入 OpenClaw Agent Workflow

目标：从脚本式 workflow 改成真正的多智能体执行链。

要做：

```text
1. 每个 Agent 增加 AGENT.md。
2. 每个 Agent 增加 input schema。
3. 每个 Agent 增加 output schema。
4. commander_agent 真实 dispatch 子 Agent。
5. 子 Agent 输出被 commander 实际使用。
6. 每个子 Agent 都有独立 trace。
7. 支持 deterministic fallback。
8. 支持 LLM structured output 模式。
```

必须包含：

```text
commander_agent
stream_monitor_agent
comment_triage_agent
product_agent
coupon_agent
policy_agent
risk_agent
script_agent
report_agent
```

验收标准：

```text
1. trace 中每个子 Agent 有独立输入和输出。
2. 不是只有 SUBAGENT_DISPATCH 日志。
3. 每个子 Agent 的 output 会被 commander 实际使用。
4. 子 Agent 失败后 commander 能降级处理。
5. 无 LLM 时可用 deterministic fallback；有 LLM 时能走模型结构化输出。
```

---

### Phase 5：工具治理和审批升级

目标：ToolRegistry 成为 Agent 工具执行网关。

要做：

```text
1. ToolRegistry 支持 input_schema / output_schema。
2. ToolRegistry 支持 allowed_agents。
3. ToolRegistry 支持 risk_level。
4. ToolRegistry 支持 requires_approval。
5. ToolRegistry 支持 timeout。
6. ToolRegistry 支持 retry。
7. ToolRegistry 支持 idempotency_key。
8. 调用前做 schema validation。
9. 调用前做 agent permission check。
10. 调用前做 risk guard。
11. 调用前做 approval guard。
12. 所有调用写入 trace。
```

验收标准：

```text
1. 高风险工具不能直接执行。
2. change_product_price 被拦截。
3. change_coupon_time 创建 approval_task。
4. create_speaker_note 可直接执行。
5. send_owncast_system_message 支持 dry_run。
6. eval 能覆盖 forbidden tool block。
```

---

### Phase 6：Owncast 双向闭环

目标：Owncast 不只是输入源，也成为 Meerkat 的反馈出口。

要做：

```text
1. 接收 Owncast CHAT。
2. 接收 Owncast STREAM_STARTED。
3. 接收 Owncast STREAM_STOPPED。
4. 实现 get_owncast_chat_history。
5. 实现 get_owncast_connected_clients。
6. 实现 send_owncast_system_message。
7. 实现 send_owncast_standard_message。
8. 支持 OWNCAST_DRY_RUN。
9. 工具调用写入 trace。
```

验收命令：

```bash
make demo-owncast-message
```

验收标准：

```text
1. 评论异常触发 speaker_note。
2. 低风险话术能进入 Owncast message flow。
3. dry_run=true 时不真实发送，但 trace 记录发送内容。
4. dry_run=false 时可真实发送到 Owncast。
```

---

### Phase 7：Meerkat Console

目标：项目必须有业务展示画面。

要做：

```text
1. 实时展示直播状态。
2. 展示 Owncast 连接状态。
3. 展示推流健康状态。
4. 展示实时评论。
5. 展示异常评论 cluster。
6. 展示 Agent trace timeline。
7. 展示 ops_alerts。
8. 展示 speaker_notes。
9. 展示 approval_tasks。
10. 展示 post_live_report。
```

验收标准：

```text
1. demo_coupon 能在 Console 展示评论进入、异常形成、Agent 分析、告警创建、话术生成。
2. demo_stream_down 能在 Console 展示推流健康变红、incident 创建、Agent 生成建议。
3. 点击 alert 能看到完整 trace。
```

---

### Phase 8：Trace、Replay 与可观测性

目标：Meerkat 要能解释 Agent 为什么这样做。

要做：

```text
1. 定义 trace event taxonomy。
2. 每次 AgentTask 生成 trace_id。
3. 每个子 Agent 记录输入输出。
4. 每次工具调用记录 TOOL_CALL / TOOL_RESULT。
5. 每次 SOP 检索记录 POLICY_RETRIEVED。
6. 每次风险判断记录 RISK_DECISION。
7. 每次审批创建记录 APPROVAL_CREATED。
8. 提供 GET /api/v1/traces/{trace_id}。
9. Console 支持 trace replay。
```

验收标准：

```text
1. 每个 demo 输出 trace_id。
2. Console 能按 trace_id 展示 timeline。
3. eval 能检查 trace_completeness。
4. trace 能回答“为什么创建这个审批任务”。
```

---

### Phase 9：长期记忆和直播复盘

目标：让 Meerkat 从单场处理器升级成越用越懂直播间的运营 Agent。

要做：

```text
1. 生成 post_live_report。
2. 按 live_room 沉淀历史异常。
3. 按 product 沉淀历史价格/库存/投诉问题。
4. 按 coupon 沉淀失效/未生效问题。
5. 按 anchor 沉淀口播易错点。
6. 下次直播前将 memory 注入 pre-live check。
```

验收标准：

```text
1. 第二次直播同一商品时，Agent 提示历史风险。
2. 下播报告为结构化 Markdown。
3. memory 写入能在 trace 中看到。
```

---

### Phase 10：Eval 体系重做

目标：用 eval 证明 Agent 行为，而不是靠 demo 自嗨。

要做：

```text
1. 至少 50 个 eval cases。
2. 覆盖 stream health。
3. 覆盖 comment anomaly。
4. 覆盖 tool safety。
5. 覆盖 workflow。
6. 覆盖 false positive。
7. 输出 report.md。
8. report.md 必须包含失败样例。
```

验收标准：

```text
1. make eval 能跑通。
2. report.md 有分类指标。
3. report.md 有失败 case。
4. RESUME.md 中的指标来自 eval report。
```

---

### Phase 11：稳定演示脚本

目标：最终项目至少有 6 个稳定 demo。

必须提供：

```bash
make demo-pre-live-check
make demo-stream-down
make demo-no-audio
make demo-coupon
make demo-price-risk
make demo-post-live-report
```

每个 demo 必须输出：

```text
trace_id
created_alerts
speaker_notes
approval_tasks
agent_run_summary
tool_calls
eval_hint
```

验收标准：

```text
任何人 clone 项目后，按 README 可以跑通至少 4 个 demo。
```

---

### Phase 12：工程质量和部署

目标：项目要像一个完整 Python 后端 + Agent 工程项目。

后端要求：

```text
FastAPI
SQLAlchemy Async
Alembic
PostgreSQL / SQLite dev mode
Pydantic
pytest
httpx AsyncClient
```

Agent 要求：

```text
structured output
tool schema validation
trace writer
eval runner
deterministic fallback
LLM mode optional
```

部署要求：

```text
docker-compose:
  owncast
  meerkat-backend
  postgres
  redis optional
```

质量命令：

```bash
make test
make eval
make demo-coupon
make demo-stream-down
```

验收标准：

```text
1. README 一键启动。
2. .env.example 完整。
3. seed 数据稳定。
4. demo 不依赖真实外部平台。
5. Owncast 可选接入，simulations 可离线跑。
```

---

## 17. 版本路线

### v0.2：直播推流健康检测版

核心目标：

```text
Meerkat 能主动发现推流异常。
```

交付：

```text
stream_health_samples
stream_probe_runs
stream_incidents
stream_probe_service
stream_health_detector
stream_monitor_agent
demo-stream-down
demo-stream-recover
```

简历可写：

```text
实现 Owncast 直播事件接入和推流健康探测，支持断流、分片停更等异常检测，并将异常转化为 AgentTask 交给 stream_monitor_agent 处理。
```

### v0.3：真多 Agent Workflow 版

核心目标：

```text
Meerkat 从脚本 workflow 变成 Agent workflow。
```

交付：

```text
AGENT.md
input/output schema
commander dispatch
subagent structured result
trace timeline
deterministic fallback
```

简历可写：

```text
设计 commander / stream_monitor / comment_triage / product / coupon / policy / risk / script 多智能体流程，通过结构化输入输出和 trace 记录实现可解释的 Agent 编排。
```

### v0.4：工具治理和审批版

核心目标：

```text
Agent 能安全接业务系统。
```

交付：

```text
ToolRegistry v2
RiskGuard
ApprovalGuard
allowed_agents
requires_approval
high-risk action -> approval_task
forbidden tool eval
```

简历可写：

```text
构建风险感知工具调用层，将工具划分为只读、低风险写入、高风险写入和破坏性动作；对改价、改券、隐藏商品等敏感动作引入 human-in-the-loop 审批。
```

### v0.5：Console 和 Owncast 双向闭环版

核心目标：

```text
项目有业务展示画面。
```

交付：

```text
Meerkat Console
Owncast outbound tools
dry_run control
speaker_note send flow
trace viewer
```

简历可写：

```text
实现直播运营工作台，展示实时评论、推流健康、Agent 执行链路、运营告警、主播话术和审批任务，并支持低风险话术通过 Owncast integration API 发送。
```

### v0.6：Eval 和复盘版

核心目标：

```text
项目有可量化证据。
```

交付：

```text
50+ eval cases
report.md
post_live_report
memory updates
failure analysis
```

简历可写：

```text
构建覆盖推流健康、评论异常、工具安全、审批触发和误报场景的离线评测集，统计异常识别、工具选择、高风险拦截、审批触发、trace 完整率和 P95 响应延迟。
```

### v1.0：简历级完整形态

必须具备：

```text
Owncast 接入
推流健康检测
评论异常聚类
商品/库存/优惠券/价格业务系统
多智能体 workflow
工具治理
SOP grounding
human-in-the-loop
Owncast 出站反馈
Meerkat Console
trace replay
eval report
post-live report
README + RESUME
```

---

## 18. 最终简历表达

v1.0 之后，学生可以这样写：

```text
Meerkat：直播运营现场指挥多智能体系统 | Python, FastAPI, Owncast, OpenClaw Runtime, Agent Workflow

- 基于 Owncast、FastAPI 和自研 OpenClaw Runtime 构建直播运营现场指挥 Agent，将直播推流状态、实时评论流、商品/库存/优惠券/价格配置转化为 AgentTask，实现直播现场异常感知、诊断、处置和复盘。
- 设计 commander / stream_monitor / comment_triage / product / coupon / policy / risk / script 多智能体流程，支持推流异常诊断、评论异常聚类、业务工具调用、直播 SOP 检索、风险判断和主播话术生成。
- 实现风险感知 ToolRegistry，将工具划分为只读、低风险写入、高风险写入和破坏性动作；对改价、改券、隐藏商品等敏感动作引入 human-in-the-loop 审批和审计日志。
- 构建 Meerkat Console，实时展示直播推流健康、评论异常、Agent trace、运营告警、主播话术和审批任务，并支持低风险话术通过 Owncast integration API 反馈到直播间。
- 构建覆盖推流健康、评论异常、工具安全、审批触发和误报场景的离线评测集，统计异常识别准确率、工具选择准确率、高风险动作拦截率、审批触发准确率、trace 完整率和 P95 处理延迟。
```

注意：简历指标必须来自真实 eval report，不允许提前写虚假百分比。

---

## 19. 给 Codex 的总施工指令

下面这段可以直接交给 Codex / 施工 Agent：

```text
目标：将 Meerkat 从评论异常 demo 升级为“直播运营现场指挥多智能体系统”。

Meerkat 不从零实现直播系统，而是接入 Owncast 作为直播和聊天底座。Owncast 负责 RTMP/Web/Chat/Webhook/Integration API；Meerkat Backend 负责直播运营业务状态；Meerkat Agent 负责事件诊断、工具调用、SOP grounding、风险判断、话术生成、告警创建、审批创建和 trace/eval。

最终必须支持：

1. 直播推流健康检测：
   - STREAM_STARTED / STREAM_STOPPED 事件接入；
   - HLS/ffprobe 探测；
   - stream_health_samples；
   - stream_incidents；
   - stream_monitor_agent；
   - 支持 STREAM_UNAVAILABLE、NO_AUDIO、NO_VIDEO、SEGMENT_STALLED、BITRATE_DROP、STREAM_RECOVERED。

2. 评论运营异常处理：
   - 评论窗口聚合；
   - 候选异常召回；
   - comment_triage_agent 语义诊断；
   - 支持 COUPON_UNAVAILABLE、INVENTORY_UNAVAILABLE、PRICE_MISMATCH、LINK_BROKEN、NOISE_ONLY。

3. 真正的多智能体 workflow：
   - commander_agent；
   - stream_monitor_agent；
   - comment_triage_agent；
   - product_agent；
   - coupon_agent；
   - policy_agent；
   - risk_agent；
   - script_agent；
   - report_agent；
   - 每个 Agent 有 AGENT.md、输入 schema、输出 schema、allowed tools 和 trace。

4. 工具治理：
   - ToolRegistry 包含 tool schema、risk_level、allowed_agents、requires_approval、timeout、retry、audit；
   - 高风险工具不能直接执行，必须创建 approval_task；
   - 所有工具调用写入 agent_action_logs。

5. Owncast 双向闭环：
   - 接收 CHAT、STREAM_STARTED、STREAM_STOPPED；
   - 支持 send_owncast_system_message；
   - 支持 dry_run；
   - trace 记录是否真实发送。

6. Meerkat Console：
   - 展示直播状态；
   - 展示推流健康；
   - 展示实时评论和异常聚类；
   - 展示 Agent trace；
   - 展示 ops_alert、speaker_note、approval_task。

7. Eval：
   - 至少 50 个 cases；
   - 覆盖 stream health、comment anomaly、tool safety、workflow、false positive；
   - 输出 report.md；
   - 不允许只展示三个 demo case 的 100%。

8. Demo：
   - make demo-pre-live-check
   - make demo-stream-down
   - make demo-no-audio
   - make demo-coupon
   - make demo-price-risk
   - make demo-post-live-report

验收标准：
   - 项目能一键启动；
   - demo 能稳定运行；
   - 每个 demo 输出 trace_id；
   - Console 能展示 Agent 执行链路；
   - eval report 能展示指标和失败样例；
   - RESUME.md 只写真实已实现能力。
```

---

## 20. 最终验收清单

### 产品验收

```text
[ ] README 能清楚说明 Meerkat 是直播运营现场指挥 Agent。
[ ] Owncast 的角色清楚：直播/聊天底座。
[ ] Meerkat Backend 的角色清楚：业务状态和工具。
[ ] Meerkat Agent 的角色清楚：诊断、决策、执行、审批、trace、eval。
[ ] Meerkat Console 有业务画面。
```

### 推流检测验收

```text
[ ] 支持 STREAM_STARTED。
[ ] 支持 STREAM_STOPPED。
[ ] 支持 HLS probe。
[ ] 支持 stream_health_samples。
[ ] 支持 stream_incidents。
[ ] 支持 stream_monitor_agent。
[ ] 支持 demo-stream-down。
[ ] 支持 demo-no-audio 或 mock no-audio。
```

### 评论异常验收

```text
[ ] 支持评论窗口聚合。
[ ] 支持候选异常召回。
[ ] 支持 comment_triage_agent。
[ ] 支持商品别名映射。
[ ] 支持噪声评论过滤。
[ ] 支持 coupon / inventory / price / link 异常。
```

### Agent 验收

```text
[ ] commander_agent 不只是 if/elif 脚本。
[ ] 每个子 Agent 有 AGENT.md。
[ ] 每个子 Agent 有输入输出 schema。
[ ] 每个子 Agent 有独立 trace。
[ ] 子 Agent 输出会被 commander 实际使用。
[ ] 支持 deterministic fallback。
[ ] 支持 LLM structured output 模式。
```

### 工具治理验收

```text
[ ] ToolRegistry 有 tool schema。
[ ] ToolRegistry 有 allowed_agents。
[ ] ToolRegistry 有 risk_level。
[ ] ToolRegistry 有 requires_approval。
[ ] 高风险工具被审批拦截。
[ ] forbidden tool eval 能通过。
[ ] 所有工具调用写入 trace。
```

### Owncast 闭环验收

```text
[ ] Owncast CHAT 能进入 Meerkat。
[ ] Owncast STREAM_STARTED 能进入 Meerkat。
[ ] Owncast STREAM_STOPPED 能进入 Meerkat。
[ ] send_owncast_system_message 可用。
[ ] OWNCAST_DRY_RUN 可配置。
[ ] 出站消息写入 trace。
```

### Eval 验收

```text
[ ] 至少 50 个 eval cases。
[ ] 覆盖 stream health。
[ ] 覆盖 comment anomaly。
[ ] 覆盖 tool safety。
[ ] 覆盖 workflow。
[ ] 覆盖 false positive。
[ ] report.md 有失败样例。
[ ] RESUME.md 指标来自 report.md。
```

### 简历验收

```text
[ ] 简历重心是 Agent，不是 FastAPI CRUD。
[ ] 简历能体现多智能体 workflow。
[ ] 简历能体现工具调用治理。
[ ] 简历能体现 SOP grounding。
[ ] 简历能体现 human-in-the-loop。
[ ] 简历能体现 trace/eval。
[ ] 简历不写未实现能力。
```

---

## 21. 最终总结

Meerkat 的最终目标不是“能跑一个评论异常 demo”，而是成为 OpenClaw 项目的业务级 capstone：

```text
一个接入 Owncast 的直播运营现场指挥多智能体系统。
```

它要能同时展示：

```text
真实业务事件流
Python 后端业务系统
直播推流健康检测
评论异常聚类
商品/库存/优惠券/价格业务工具
多智能体任务编排
SOP grounding
风险感知工具调用
human-in-the-loop 审批
Owncast 双向闭环
Meerkat Console
trace replay
eval report
下播复盘
```

做到这个形态，Meerkat 才真正能支撑学生在简历里写：

```text
我不是只做了一个聊天 Agent，而是实现了一个接入真实直播系统、真实业务状态、真实工具调用和真实评测闭环的 Agent 工程项目。
```
