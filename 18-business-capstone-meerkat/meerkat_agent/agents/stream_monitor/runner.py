from __future__ import annotations

from meerkat_agent.runtime.base_agent import AgentExecutionContext, AgentResult


class StreamMonitorRunner:
    name = "stream_monitor"
    allowed_tools = ["get_stream_incident_context"]

    async def run(self, input_data: dict, context: AgentExecutionContext) -> AgentResult:
        incident_id = input_data["stream_incident_id"]
        payload = await context.registry.call("get_stream_incident_context", {"stream_incident_id": incident_id}, agent_name=self.name)
        incident = payload.get("incident") or {}
        samples = payload.get("recent_samples") or []
        output = {
            "incident_type": incident.get("incident_type", input_data.get("incident_type", "STREAM_INTERRUPTED")),
            "severity": incident.get("severity", "P1"),
            "confidence": 0.92,
            "evidence": {
                "sample_ids": [sample.get("id") for sample in samples if sample.get("id")],
                "probe_errors": [sample.get("probe_error") for sample in samples if sample.get("probe_error")],
                "last_segment_age_ms": next((sample.get("last_segment_age_ms") for sample in samples if sample.get("last_segment_age_ms") is not None), None),
            },
            "diagnosis": "Stream probe samples indicate the live signal is degraded or interrupted.",
            "recommended_actions": ["check_obs_connection", "pause_product_promise", "notify_operator"],
            "needs_policy": True,
        }
        return AgentResult(agent_name=self.name, status="OK", output=output, confidence=0.92, tool_calls=["get_stream_incident_context"])
