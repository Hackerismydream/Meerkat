# 风险控制规则

- READ_ONLY 工具可以直接执行。
- LOW_RISK_WRITE 工具可以写入业务对象，但必须记录审计日志。
- HIGH_RISK_WRITE 工具默认 dry-run 或转审批。
- DESTRUCTIVE 工具禁止直接执行，只能创建 action proposal 或 approval task。
