# Meerkat：直播运营现场指挥多智能体系统

## 一句话简介

基于 Owncast、FastAPI 和自研 OpenClaw Runtime 构建直播运营现场指挥多智能体系统，将实时评论流和推流健康样本转化为 AgentTask，通过 commander agent 编排 stream_monitor / triage / product / coupon / policy / risk / script / report 等子 Agent，完成业务工具调用、SOP 检索、风险审批、trace 回放、下播复盘和离线 eval。

## 简历项目名称

```text
Meerkat：基于 OpenClaw Runtime 的直播运营现场指挥 Agent Workflow 平台
```

## Agent-first bullets

- 基于 OpenClaw Runtime 实现事件驱动多智能体 workflow，将 Owncast 实时评论流和 HLS/ffprobe 推流健康样本转换为 AgentTask，由 commander agent 编排 stream_monitor / triage / product / coupon / policy / risk / script / report 子 Agent 处理直播现场异常。
- 将商品、库存、优惠券、评论检索、告警创建、主播话术、审批任务和 Owncast 消息发送等接口封装为风险感知 Agent tools，并通过 ToolRegistry 统一执行、记录 trace 和处理失败。
- 结合直播运营 SOP 检索和 risk agent，实现优惠券不可领取、库存售罄、价格口径不一致、断流、无声、分片停更等场景的异常识别、证据收集、处理建议生成和高风险动作 human-in-the-loop 审批。
- 构建 trace/eval/report 体系，回放 Agent 决策、子 Agent 派发、工具调用、SOP 命中、风险判断和业务状态变更，评估工具调用召回率、禁用工具拦截率、审批触发准确率、trace 完整率和失败样例。

## Python 后端补充 bullets

- 基于 FastAPI、SQLAlchemy Async 和 SQLite 实现 Meerkat Backend，覆盖直播间、直播场次、商品别名、商品、库存、优惠券、口播脚本、评论 cluster、推流健康样本、stream incident、AgentTask、AgentRun、运营告警、主播话术、审批任务、下播复盘和审计日志等模块。
- 接入 Owncast 自托管直播服务，通过 Webhook 捕获 CHAT、STREAM_STARTED、STREAM_STOPPED 等事件，并提供模拟评论 API，保证 demo 与 eval 可在本地稳定复现。

## 本地 eval 指标

来源：`cd meerkat_agent/evals && python run_eval.py`。

```text
alert_type_accuracy = 94%
subagent_dispatch_coverage = 96%
tool_call_recall = 96%
tool_call_precision = 96%
tool_execution_success_rate = 100%
forbidden_tool_block_rate = 100%
risk_gate_accuracy = 96%
approval_trigger_accuracy = 100%
policy_grounding_accuracy = 94%
trace_completeness = 100%
p95_agent_run_latency = 21 ms
```

当前 eval 覆盖 50 个 case，包含 comment anomaly、stream health、tool safety、workflow 和 false positive。报告中保留失败样例，主要缺口是更自然的库存表达召回和混合异常拆分。

## 面试讲解顺序

1. 业务问题：直播评论流实时、异常类型多、运营动作有风险，单纯客服问答不够。
2. 事件入口：Owncast Webhook / simulation comments / stream health probe -> AgentTask -> commander agent。
3. 多 Agent 分工：stream_monitor 判断推流异常，triage 识别评论异常，product/coupon 查询证据，policy 检索 SOP，risk 做风控，script 生成话术，report 做复盘。
4. 工具调用：所有业务读写都通过 ToolRegistry，工具有 schema、risk_level、trace。
5. 风险边界：改价、改券、下架、发公屏消息都不能直接执行，只能创建审批。
6. 可信度：SOP grounding + trace replay + eval，不只看最终回复。
7. 工程能力：FastAPI 后端、状态持久化、Owncast 接入、本地 demo 和可复现测试。
