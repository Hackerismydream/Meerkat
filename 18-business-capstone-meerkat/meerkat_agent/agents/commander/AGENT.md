# commander agent

主控 Agent。接收 `live.comment.window_ready` 事件，创建执行计划，派发 live_triage/product/coupon/policy/risk/script 子 Agent，最后通过 ToolRegistry 调用业务写工具。
