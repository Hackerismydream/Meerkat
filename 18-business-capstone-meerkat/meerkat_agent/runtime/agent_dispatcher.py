from __future__ import annotations

from typing import Any

from app.services.trace_service import write_log

from .base_agent import AgentExecutionContext, AgentResult, BaseAgentRunner


class AgentDispatcher:
    def __init__(self, runners: dict[str, BaseAgentRunner]):
        self.runners = runners

    async def run(self, agent_name: str, input_data: dict[str, Any], context: AgentExecutionContext) -> AgentResult:
        if agent_name not in self.runners:
            raise KeyError(f"unknown subagent: {agent_name}")
        await write_log(
            context.db,
            trace_id=context.trace_id,
            session_id=context.session_id,
            agent_name="commander",
            action_type="SUBAGENT_DISPATCHED",
            output_data={"to": agent_name, **input_data},
        )
        result = await self.runners[agent_name].run(input_data, context)
        await write_log(
            context.db,
            trace_id=context.trace_id,
            session_id=context.session_id,
            agent_name=agent_name,
            parent_agent_name="commander",
            action_type="SUBAGENT_RESULT",
            output_data=result.output,
        )
        return result
