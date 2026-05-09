from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AgentExecutionContext:
    db: Any
    trace_id: str
    session_id: int
    registry: Any
    memory: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent_name: str
    status: str
    output: dict[str, Any]
    confidence: float | None = None
    tool_calls: list[str] = field(default_factory=list)
    error: str | None = None


class BaseAgentRunner(Protocol):
    name: str
    allowed_tools: list[str]

    async def run(self, input_data: dict[str, Any], context: AgentExecutionContext) -> AgentResult:
        ...
