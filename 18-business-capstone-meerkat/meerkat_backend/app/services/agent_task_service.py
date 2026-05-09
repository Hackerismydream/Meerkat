from __future__ import annotations

import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AlertType
from app.db.base import AgentTask
from app.services.serialization import dumps
from app.services.trace_service import write_log

CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
if str(CAPSTONE_ROOT) not in sys.path:
    sys.path.insert(0, str(CAPSTONE_ROOT))

from meerkat_agent.runner import MeerkatAgentRunner  # noqa: E402


def new_trace_id() -> str:
    return f"tr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"


async def create_agent_task(
    db: AsyncSession,
    *,
    session_id: int,
    source: str,
    alert_type_hint: AlertType | str | None = None,
    comment_ids: list[int] | None = None,
    input_payload: dict[str, Any] | None = None,
    task_type: str = "COMMENT_WINDOW_ANALYSIS",
) -> AgentTask:
    hint = alert_type_hint.value if isinstance(alert_type_hint, AlertType) else alert_type_hint
    comment_ids = comment_ids or []
    input_payload = input_payload or {}
    task = AgentTask(
        trace_id=new_trace_id(),
        session_id=session_id,
        task_type=task_type,
        source=source,
        alert_type_hint=hint,
        comment_ids_json=dumps(comment_ids),
        input_payload_json=dumps(input_payload),
        status="PENDING",
    )
    db.add(task)
    await db.flush()
    await write_log(
        db,
        trace_id=task.trace_id,
        session_id=session_id,
        agent_name="backend",
        action_type="AGENT_TASK_CREATED",
        output_data={"task_id": task.id, "alert_type_hint": hint, "comment_ids": comment_ids},
    )
    return task


async def run_agent_task(db: AsyncSession, task_id: int) -> dict[str, Any]:
    return await MeerkatAgentRunner(db).run_task(task_id)
