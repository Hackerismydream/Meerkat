from __future__ import annotations

from meerkat_agent.runtime.base_agent import AgentExecutionContext, AgentResult


class RiskRunner:
    name = "risk"
    allowed_tools = []

    async def run(self, input_data: dict, context: AgentExecutionContext) -> AgentResult:
        risk_level = input_data.get("risk_level", "LOW_RISK_WRITE")
        blocked = input_data.get("blocked_tools", [])
        output = {
            "risk_level": risk_level,
            "requires_approval": bool(input_data.get("requires_approval", risk_level in {"HIGH_RISK_WRITE", "DESTRUCTIVE"})),
            "blocked_tools": blocked,
            "allowed_tools": ["create_ops_alert", "create_speaker_note", "create_approval_task"],
            "reason": input_data.get("reason", "Risk policy evaluated proposed live operation."),
        }
        return AgentResult(agent_name=self.name, status="OK", output=output, confidence=0.9)
