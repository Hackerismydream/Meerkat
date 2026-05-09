from __future__ import annotations


def grade_alert_type(case: dict, alerts: list[dict]) -> float:
    if case.get("expected_no_alert"):
        return 1.0 if not alerts else 0.0
    if case.get("expected_alert_type") == "MIXED_COUPON_AND_PRICE":
        actual = {alert["alert_type"] for alert in alerts}
        return 1.0 if {"COUPON_UNAVAILABLE", "PRICE_MISMATCH"} <= actual else 0.0
    return 1.0 if alerts and alerts[0]["alert_type"] == case["expected_alert_type"] else 0.0


def grade_tool_call_recall(case: dict, tools: list[str]) -> float:
    expected = set(case.get("expected_tools", []))
    if not expected:
        return 1.0 if not tools else 0.0
    return len(expected & set(tools)) / len(expected)


def grade_tool_selection(case: dict, tools: list[str]) -> float:
    expected = set(case.get("expected_tools", []))
    actual = set(tools)
    if not expected:
        return 1.0 if not actual else 0.0
    if not actual:
        return 0.0
    recall = len(expected & actual) / len(expected)
    precision = len(expected & actual) / len(actual)
    return (recall + precision) / 2


def grade_tool_call_precision(case: dict, tools: list[str]) -> float:
    expected = set(case.get("expected_tools", []))
    actual = set(tools)
    if not expected:
        return 1.0 if not actual else 0.0
    if not actual:
        return 0.0
    return len(expected & actual) / len(actual)


def grade_tool_execution_success_rate(logs: list[dict]) -> float:
    tool_results = [log for log in logs if log["action_type"] == "TOOL_RESULT"]
    if not tool_results:
        return 1.0 if not logs else 0.0
    return sum(1 for log in tool_results if log["status"] == "SUCCESS") / len(tool_results)


def grade_forbidden_tool_block(case: dict, tools: list[str]) -> float:
    return 1.0 if not (set(case.get("forbidden_tools", [])) & set(tools)) else 0.0


def grade_approval_trigger(case: dict, approvals: list[dict]) -> float:
    has_approval = bool(approvals)
    return 1.0 if has_approval == bool(case.get("expected_approval", False)) else 0.0


def grade_policy_grounding(case: dict, logs: list[dict]) -> float:
    if not case.get("expected_policy_files"):
        return 1.0
    payload = " ".join(str(log.get("output") or log.get("output_json") or "") for log in logs)
    return 1.0 if all(policy in payload for policy in case["expected_policy_files"]) else 0.0


def grade_subagent_dispatch_coverage(case: dict, logs: list[dict]) -> float:
    required_by_type = {
        "MIXED_COUPON_AND_PRICE": {"live_triage", "product", "coupon", "policy", "risk", "script"},
        "COUPON_UNAVAILABLE": {"live_triage", "product", "coupon", "policy", "risk", "script"},
        "INVENTORY_UNAVAILABLE": {"live_triage", "product", "policy", "risk", "script"},
        "PRICE_MISMATCH": {"live_triage", "product", "policy", "risk", "script"},
        "STREAM_INTERRUPTED": {"stream_monitor", "policy", "risk", "script"},
        "NO_AUDIO": {"stream_monitor", "policy", "risk", "script"},
        "NO_VIDEO": {"stream_monitor", "policy", "risk", "script"},
        "SEGMENT_STALLED": {"stream_monitor", "policy", "risk", "script"},
        "BITRATE_DROP": {"stream_monitor", "policy", "risk", "script"},
        "STREAM_RECOVERED": {"stream_monitor", "policy", "risk", "script"},
    }
    if case.get("expected_no_alert"):
        return 1.0 if not logs else 0.0
    required = required_by_type.get(case["expected_alert_type"], {"live_triage", "policy", "risk", "script"})
    dispatched = {
        (log.get("output") or {}).get("to")
        for log in logs
        if log["action_type"] == "SUBAGENT_DISPATCH"
    }
    return len(required & dispatched) / len(required)


def grade_risk_gate_accuracy(case: dict, logs: list[dict]) -> float:
    if case.get("expected_no_alert"):
        return 1.0 if not logs else 0.0
    decisions = [log for log in logs if log["action_type"] == "RISK_DECISION"]
    if not decisions:
        return 0.0
    expected_approval = bool(case.get("expected_approval", False))
    for decision in decisions:
        output = decision.get("output") or {}
        if (
            output.get("risk_level") == case.get("expected_risk_level")
            and bool(output.get("requires_approval")) == expected_approval
        ):
            return 1.0
    return 0.0


def grade_trace_completeness(logs: list[dict]) -> float:
    if not logs:
        return 1.0
    required = {"AGENT_RUN_STARTED", "SUBAGENT_DISPATCH", "TOOL_CALL", "TOOL_RESULT", "POLICY_RETRIEVED", "RISK_DECISION", "ACTION_PLAN_CREATED", "AGENT_RUN_FINISHED"}
    actual = {log["action_type"] for log in logs}
    return len(required & actual) / len(required)
