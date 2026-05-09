from __future__ import annotations

from time import perf_counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AgentActionLog
from app.services.serialization import dumps


async def write_log(
    db: AsyncSession,
    *,
    trace_id: str,
    session_id: int | None,
    agent_name: str,
    action_type: str,
    status: str = "SUCCESS",
    parent_agent_name: str | None = None,
    tool_name: str | None = None,
    input_data: dict[str, Any] | None = None,
    output_data: dict[str, Any] | None = None,
    risk_level: str | None = None,
    duration_ms: int | None = None,
    error_message: str | None = None,
) -> AgentActionLog:
    log = AgentActionLog(
        trace_id=trace_id,
        session_id=session_id,
        agent_name=agent_name,
        parent_agent_name=parent_agent_name,
        action_type=action_type,
        tool_name=tool_name,
        input_json=dumps(input_data) if input_data is not None else None,
        output_json=dumps(output_data) if output_data is not None else None,
        risk_level=risk_level,
        status=status,
        duration_ms=duration_ms,
        error_message=error_message,
    )
    db.add(log)
    await db.flush()
    return log


class Timer:
    def __enter__(self) -> "Timer":
        self.started = perf_counter()
        return self

    def __exit__(self, *_args: object) -> None:
        self.duration_ms = int((perf_counter() - self.started) * 1000)
