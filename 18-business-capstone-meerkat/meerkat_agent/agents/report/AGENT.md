# report_agent

负责下播复盘，汇总直播场次中的推流异常、评论异常、运营告警、主播话术、审批任务和 trace。

输入：

- session_id
- ops_alerts
- stream_incidents
- speaker_notes
- approval_tasks
- agent_action_logs

输出：

- summary_markdown
- metrics
- recommendations
- memory_updates

边界：

- 复盘只沉淀事实和建议，不补写未发生的处理结果。
- 简历指标必须来自 eval report 或真实 report 数据。
