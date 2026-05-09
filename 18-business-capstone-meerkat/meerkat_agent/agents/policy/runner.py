from __future__ import annotations

from meerkat_agent.runtime.base_agent import AgentExecutionContext, AgentResult


class PolicyRunner:
    name = "policy"
    allowed_tools = ["search_policy_docs"]

    async def run(self, input_data: dict, context: AgentExecutionContext) -> AgentResult:
        hits = await context.registry.call("search_policy_docs", {"query": input_data.get("query", ""), "top_k": 3}, agent_name=self.name)
        return AgentResult(agent_name=self.name, status="OK", output={"policy_hits": hits.get("items", [])}, tool_calls=["search_policy_docs"])
