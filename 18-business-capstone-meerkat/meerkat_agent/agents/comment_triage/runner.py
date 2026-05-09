from __future__ import annotations

from meerkat_agent.runtime.base_agent import AgentExecutionContext, AgentResult


class CommentTriageRunner:
    name = "comment_triage"
    allowed_tools = ["search_recent_comments"]

    async def run(self, input_data: dict, context: AgentExecutionContext) -> AgentResult:
        comments = await context.registry.call("search_recent_comments", {"session_id": context.session_id, "limit": 50}, agent_name=self.name)
        clusters = input_data.get("clusters", [])
        output = {"clusters": clusters, "noise_comment_ids": [item["id"] for item in comments.get("items", []) if not item.get("matched_type")]}
        return AgentResult(agent_name=self.name, status="OK", output=output, confidence=0.86, tool_calls=["search_recent_comments"])
