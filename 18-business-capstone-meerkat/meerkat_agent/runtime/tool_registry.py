from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApprovalStatus
from app.db.base import ApprovalTask
from app.services.serialization import dumps, model_to_dict
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
        self._idempotency_cache: dict[str, dict[str, Any]] = {}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    async def call(self, tool_name: str, arguments: dict[str, Any], agent_name: str = "commander") -> dict[str, Any]:
        if tool_name not in self._tools:
            raise KeyError(f"unknown tool: {tool_name}")
        tool = self._tools[tool_name]
        self._validate_schema(tool, arguments)
        if tool.allowed_agents and agent_name not in tool.allowed_agents:
            result = {"status": "DENIED", "reason": "agent_not_allowed", "tool_name": tool.name, "agent_name": agent_name}
            await write_log(
                self.db,
                trace_id=self.trace_id,
                session_id=self.session_id,
                agent_name=agent_name,
                parent_agent_name="commander" if agent_name != "commander" else None,
                action_type="TOOL_DENIED",
                tool_name=tool.name,
                input_data=arguments,
                output_data=result,
                risk_level=tool.risk_level,
                status="DENIED",
            )
            return result
        if self._requires_approval(tool):
            return await self._create_approval_gate(tool, arguments, agent_name)
        idempotency_key = self._idempotency_key(tool, arguments)
        if idempotency_key and idempotency_key in self._idempotency_cache:
            result = self._idempotency_cache[idempotency_key]
            await write_log(
                self.db,
                trace_id=self.trace_id,
                session_id=self.session_id,
                agent_name=agent_name,
                parent_agent_name="commander" if agent_name != "commander" else None,
                action_type="IDEMPOTENCY_HIT",
                tool_name=tool.name,
                input_data=arguments,
                output_data=result,
                risk_level=tool.risk_level,
            )
            return result

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
            if tool.handler is None:
                raise ValueError(f"tool {tool.name} has no handler")
            try:
                async with asyncio.timeout(tool.timeout_ms / 1000):
                    result = await tool.handler(**arguments)
            except TimeoutError:
                result = {"status": "TOOL_TIMEOUT", "tool_name": tool.name}
                await write_log(
                    self.db,
                    trace_id=self.trace_id,
                    session_id=self.session_id,
                    agent_name=agent_name,
                    parent_agent_name="commander" if agent_name != "commander" else None,
                    action_type="TOOL_TIMEOUT",
                    tool_name=tool.name,
                    input_data=arguments,
                    output_data=result,
                    risk_level=tool.risk_level,
                    status="FAILED",
                    duration_ms=getattr(timer, "duration_ms", None),
                )
                return result
        schema_error = self._validate_output_schema(tool, result)
        if schema_error:
            result = {"status": "TOOL_RESULT_SCHEMA_ERROR", "tool_name": tool.name, "error": schema_error, "output": result}
            await write_log(
                self.db,
                trace_id=self.trace_id,
                session_id=self.session_id,
                agent_name=agent_name,
                parent_agent_name="commander" if agent_name != "commander" else None,
                action_type="TOOL_RESULT_SCHEMA_ERROR",
                tool_name=tool.name,
                input_data=arguments,
                output_data=result,
                risk_level=tool.risk_level,
                status="FAILED",
                duration_ms=timer.duration_ms,
            )
            return result
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
        if idempotency_key:
            self._idempotency_cache[idempotency_key] = result
        if tool.name == "send_owncast_system_message":
            action = "OWNCAST_MESSAGE_SENT"
            if result.get("status") == "DRY_RUN" or result.get("dry_run"):
                action = "OWNCAST_MESSAGE_DRY_RUN"
            elif result.get("status") == "FAILED":
                action = "OWNCAST_MESSAGE_FAILED"
            await write_log(
                self.db,
                trace_id=self.trace_id,
                session_id=self.session_id,
                agent_name=agent_name,
                parent_agent_name="commander" if agent_name != "commander" else None,
                action_type=action,
                tool_name=tool.name,
                input_data=arguments,
                output_data=result,
                risk_level=tool.risk_level,
            )
        return result

    def _validate_schema(self, tool: AgentTool, arguments: dict[str, Any]) -> None:
        required = tool.input_schema.get("required", [])
        missing = [key for key in required if key not in arguments]
        if missing:
            raise ValueError(f"tool {tool.name} missing required arguments: {', '.join(missing)}")

    def _requires_approval(self, tool: AgentTool) -> bool:
        if tool.requires_approval:
            return True
        return tool.risk_level in {"DESTRUCTIVE", "HIGH_RISK_WRITE"}

    def _validate_output_schema(self, tool: AgentTool, result: dict[str, Any]) -> str | None:
        if not tool.output_schema:
            return None
        required = tool.output_schema.get("required", [])
        missing = [key for key in required if key not in result]
        if missing:
            return f"missing required output keys: {', '.join(missing)}"
        return None

    def _idempotency_key(self, tool: AgentTool, arguments: dict[str, Any]) -> str | None:
        if not tool.idempotency_key_strategy:
            return None
        if tool.idempotency_key_strategy == "arguments_hash":
            payload = dumps({"tool": tool.name, "arguments": arguments})
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{tool.name}:{tool.idempotency_key_strategy}"

    async def _create_approval_gate(self, tool: AgentTool, arguments: dict[str, Any], agent_name: str) -> dict[str, Any]:
        approval = ApprovalTask(
            proposal_id=arguments.get("proposal_id"),
            session_id=int(arguments.get("session_id") or self.session_id),
            risk_level=tool.risk_level,
            title=self._approval_title(tool.name),
            reason=arguments.get("reason") or f"{tool.name} is gated by ToolRegistry risk policy.",
            payload_json=dumps({"blocked_tool": tool.name, "arguments": arguments}),
            status=ApprovalStatus.PENDING.value,
            trace_id=self.trace_id,
        )
        self.db.add(approval)
        await self.db.flush()
        approval_dict = model_to_dict(approval)
        result = {
            "status": "APPROVAL_REQUIRED",
            "blocked_tool": tool.name,
            "id": approval.id,
            "approval_task_id": approval.id,
            "proposal_id": approval.proposal_id,
        }
        await write_log(
            self.db,
            trace_id=self.trace_id,
            session_id=self.session_id,
            agent_name=agent_name,
            parent_agent_name="commander" if agent_name != "commander" else None,
            action_type="APPROVAL_REQUIRED",
            tool_name=tool.name,
            input_data=arguments,
            output_data=result,
            risk_level=tool.risk_level,
        )
        await write_log(
            self.db,
            trace_id=self.trace_id,
            session_id=self.session_id,
            agent_name=agent_name,
            parent_agent_name="commander" if agent_name != "commander" else None,
            action_type="TOOL_CALL",
            tool_name="create_approval_task",
            input_data={
                "session_id": approval.session_id,
                "proposal_id": approval.proposal_id,
                "title": approval.title,
                "reason": approval.reason,
                "payload": {"blocked_tool": tool.name, "arguments": arguments},
                "risk_level": approval.risk_level,
            },
            risk_level="LOW_RISK_WRITE",
        )
        await write_log(
            self.db,
            trace_id=self.trace_id,
            session_id=self.session_id,
            agent_name=agent_name,
            parent_agent_name="commander" if agent_name != "commander" else None,
            action_type="TOOL_RESULT",
            tool_name="create_approval_task",
            input_data=arguments,
            output_data=approval_dict,
            risk_level="LOW_RISK_WRITE",
        )
        await write_log(
            self.db,
            trace_id=self.trace_id,
            session_id=self.session_id,
            agent_name=agent_name,
            parent_agent_name="commander" if agent_name != "commander" else None,
            action_type="APPROVAL_CREATED",
            output_data={"approval_task_id": approval.id},
            risk_level=tool.risk_level,
        )
        return result

    def _approval_title(self, tool_name: str) -> str:
        titles = {
            "change_coupon_time": "审批优惠券提前生效",
            "change_product_price": "审批价格口径处理方案",
            "hide_product_from_live": "审批隐藏直播商品",
            "stop_stream": "审批停止直播推流",
        }
        return titles.get(tool_name, f"审批 {tool_name}")
