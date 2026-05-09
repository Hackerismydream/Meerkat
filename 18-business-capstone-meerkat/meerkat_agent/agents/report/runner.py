from __future__ import annotations

from meerkat_agent.runtime.base_agent import AgentExecutionContext, AgentResult


class ReportRunner:
    name = "report"
    allowed_tools = []

    async def run(self, input_data: dict, context: AgentExecutionContext) -> AgentResult:
        return AgentResult(agent_name=self.name, status="OK", output={"report_scope": input_data.get("report_scope", "post_live")})
