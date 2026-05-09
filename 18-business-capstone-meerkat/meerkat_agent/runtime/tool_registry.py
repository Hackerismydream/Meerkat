from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.trace_service import Timer, write_log

from .risk_guard import RiskGuard
from .schemas import AgentTool


class ToolRegistry:
    def __init__(self, db: AsyncSession, trace_id: str, session_id: int):
        self.db = db
        self.trace_id = trace_id
        self.session_id = session_id
        self.risk_guard = RiskGuard()
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    async def call(self, tool_name: str, arguments: dict[str, Any], agent_name: str = "commander") -> dict[str, Any]:
        if tool_name not in self._tools:
            raise KeyError(f"unknown tool: {tool_name}")
        tool = self._tools[tool_name]
        if tool.risk_level == "DESTRUCTIVE":
            self.risk_guard.assert_allowed(tool.name, tool.risk_level)

        await write_log(
            self.db,
            trace_id=self.trace_id,
            session_id=self.session_id,
            agent_name=agent_name,
            parent_agent_name="commander" if agent_name != "commander" else None,
            action_type="TOOL_CALL",
            tool_name=tool.name,
            input_data=arguments,
            risk_level=tool.risk_level,
        )
        with Timer() as timer:
            result = await tool.handler(**arguments)
        await write_log(
            self.db,
            trace_id=self.trace_id,
            session_id=self.session_id,
            agent_name=agent_name,
            parent_agent_name="commander" if agent_name != "commander" else None,
            action_type="TOOL_RESULT",
            tool_name=tool.name,
            input_data=arguments,
            output_data=result,
            risk_level=tool.risk_level,
            duration_ms=timer.duration_ms,
        )
        return result
