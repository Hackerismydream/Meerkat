from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AlertSeverity, AlertType
from app.db.base import AgentRun, AgentTask
from app.services.serialization import dumps, loads
from app.services.trace_service import write_log
from app.services.post_live_report_service import create_post_live_report
from meerkat_agent.runtime.schemas import AgentTool
from meerkat_agent.runtime.tool_registry import ToolRegistry
from meerkat_agent.tools.meerkat_tools import MeerkatTools


class MeerkatAgentRunner:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_task(self, task_id: int) -> dict[str, Any]:
        task = await self.db.get(AgentTask, task_id)
        if task is None:
            raise ValueError(f"agent_task {task_id} not found")

        trace_id = task.trace_id
        task.status = "RUNNING"
        task.started_at = datetime.now(timezone.utc)
        run = AgentRun(task_id=task.id, trace_id=trace_id, root_agent="commander", status="RUNNING")
        self.db.add(run)
        await self.db.flush()
        await write_log(self.db, trace_id=trace_id, session_id=task.session_id, agent_name="commander", action_type="AGENT_RUN_STARTED", output_data={"task_id": task.id, "run_id": run.id})

        try:
            result = await self._run_workflow(task, run.id)
            run.status = "SUCCEEDED"
            run.finished_at = datetime.now(timezone.utc)
            run.final_output_json = dumps(result)
            task.status = "SUCCEEDED"
            task.finished_at = datetime.now(timezone.utc)
            await write_log(self.db, trace_id=trace_id, session_id=task.session_id, agent_name="commander", action_type="AGENT_RUN_FINISHED", output_data=result)
            await self.db.commit()
            return {"run_id": run.id, **result}
        except Exception as exc:
            run.status = "FAILED"
            task.status = "FAILED"
            task.error_message = str(exc)
            await write_log(self.db, trace_id=trace_id, session_id=task.session_id, agent_name="commander", action_type="ERROR", status="FAILED", error_message=str(exc))
            await self.db.commit()
            raise

    async def _run_workflow(self, task: AgentTask, run_id: int) -> dict[str, Any]:
        alert_type = AlertType(task.alert_type_hint or AlertType.UNKNOWN.value)
        comment_ids = loads(task.comment_ids_json) or []
        input_payload = loads(task.input_payload_json) or {}
        product_id = input_payload.get("product_id")
        coupon_id = input_payload.get("coupon_id")

        tools = MeerkatTools(self.db, task.trace_id, settings.knowledge_dir)
        registry = ToolRegistry(self.db, task.trace_id, task.session_id)
        for name, risk, handler in [
            ("search_recent_comments", "READ_ONLY", tools.search_recent_comments),
            ("get_live_products", "READ_ONLY", tools.get_live_products),
            ("get_product_detail", "READ_ONLY", tools.get_product_detail),
            ("get_product_inventory", "READ_ONLY", tools.get_product_inventory),
            ("get_coupon_detail", "READ_ONLY", tools.get_coupon_detail),
            ("get_stream_incident_context", "READ_ONLY", tools.get_stream_incident_context),
            ("search_policy_docs", "READ_ONLY", tools.search_policy_docs),
            ("create_ops_alert", "LOW_RISK_WRITE", tools.create_ops_alert),
            ("create_speaker_note", "LOW_RISK_WRITE", tools.create_speaker_note),
            ("create_action_proposal", "LOW_RISK_WRITE", tools.create_action_proposal),
            ("create_approval_task", "LOW_RISK_WRITE", tools.create_approval_task),
        ]:
            registry.register(AgentTool(name=name, risk_level=risk, description=name, handler=handler))

        if task.task_type == "STREAM_HEALTH_ANALYSIS":
            return await self._handle_stream_health(task, registry, input_payload.get("stream_incident_id"))
        if task.task_type == "POST_LIVE_REPORT":
            return await self._handle_post_live_report(task, run_id)
        if task.task_type == "PRE_LIVE_CHECK":
            return await self._handle_pre_live_check(task, registry)

        await self._dispatch(task, "live_triage", {"comment_ids": comment_ids})
        await registry.call("search_recent_comments", {"session_id": task.session_id, "q": alert_type.value, "limit": 50}, agent_name="live_triage")
        await self._dispatch(task, "product", {"session_id": task.session_id, "purpose": "resolve live product context"})
        await registry.call("get_live_products", {"session_id": task.session_id}, agent_name="product")
        await self._subagent_result(task, "live_triage", {"alert_type": alert_type.value, "confidence": 0.9})

        if alert_type == AlertType.COUPON_UNAVAILABLE:
            return await self._handle_coupon(task, registry, comment_ids, coupon_id or 1)
        if alert_type == AlertType.INVENTORY_UNAVAILABLE:
            return await self._handle_inventory(task, registry, comment_ids, product_id or 2)
        if alert_type == AlertType.PRICE_MISMATCH:
            return await self._handle_price(task, registry, comment_ids, product_id or 3)

        return {"trace_id": task.trace_id, "alert_created": False, "reason": "unknown alert type"}

    async def _handle_pre_live_check(self, task: AgentTask, registry: ToolRegistry) -> dict[str, Any]:
        await self._dispatch(task, "product", {"purpose": "pre-live product and inventory check"})
        products = await registry.call("get_live_products", {"session_id": task.session_id}, agent_name="product")
        await self._dispatch(task, "coupon", {"purpose": "pre-live coupon validity check"})
        coupon = await registry.call("get_coupon_detail", {"coupon_id": 1}, agent_name="coupon")
        inventory = await registry.call("get_product_inventory", {"product_id": 2}, agent_name="product")
        policies = await self._policy(task, registry, "开播前 价格 优惠券 库存 巡检")
        await self._risk(task, "DESTRUCTIVE", True, ["change_coupon_time", "change_product_price"])
        await self._action_plan(
            task,
            {
                "checks": ["商品上架", "库存", "优惠券生效时间", "口播价与页面价"],
                "issues": ["2 号链接库存为 0", "C50 优惠券尚未生效", "3 号链接口播价与页面价不一致"],
            },
        )
        alert = await registry.call(
            "create_ops_alert",
            {
                "session_id": task.session_id,
                "alert_type": AlertType.PRICE_MISMATCH.value,
                "severity": AlertSeverity.P1.value,
                "title": "开播前巡检发现价格、券和库存风险",
                "summary": "开播前巡检发现库存不足、优惠券未生效和口播价不一致，需人工确认后再开播。",
                "evidence": {"products": products["items"], "coupon": coupon, "inventory": inventory, "policies": policies["items"]},
                "product_id": 3,
                "coupon_id": 1,
            },
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="commander", action_type="ALERT_CREATED", output_data={"alert_id": alert["id"]})
        proposal = await registry.call(
            "create_action_proposal",
            {
                "session_id": task.session_id,
                "alert_id": alert["id"],
                "action_type": "PRE_LIVE_FIX_APPROVAL",
                "risk_level": "DESTRUCTIVE",
                "arguments": {"coupon_id": 1, "product_id": 3, "checks": ["coupon_time", "spoken_price"]},
                "reason": "开播前调整优惠券时间或价格口径会影响交易承诺，必须人工审批。",
                "status": "APPROVAL_CREATED",
                "created_by_agent": "risk",
            },
            agent_name="risk",
        )
        note = await registry.call(
            "create_speaker_note",
            {"session_id": task.session_id, "alert_id": alert["id"], "body": "开播前请先确认 3 号链接价格口径和 C50 优惠券生效时间，2 号链接库存不足暂缓讲解。", "target": "operator"},
            agent_name="script",
        )
        approval = await registry.call(
            "create_approval_task",
            {
                "session_id": task.session_id,
                "proposal_id": proposal["id"],
                "title": "审批开播前价格和优惠券修正",
                "reason": "开播前巡检发现高风险业务口径，需要人工确认。",
                "payload": {"alert_id": alert["id"], "coupon_id": 1, "product_id": 3},
                "risk_level": "DESTRUCTIVE",
            },
            agent_name="risk",
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="risk", parent_agent_name="commander", action_type="APPROVAL_CREATED", output_data={"approval_task_id": approval["id"]}, risk_level="DESTRUCTIVE")
        return {
            "trace_id": task.trace_id,
            "session_id": task.session_id,
            "workflow_name": "meerkat.liveops.pre_live_check",
            "created_entities": {
                "ops_alert_id": alert["id"],
                "speaker_note_id": note["id"],
                "approval_task_id": approval["id"],
            },
            "issues": ["inventory_shortage", "coupon_not_started", "price_mismatch"],
            "alert_created": True,
        }

    async def _handle_post_live_report(self, task: AgentTask, run_id: int) -> dict[str, Any]:
        await self._dispatch(task, "report", {"session_id": task.session_id})
        report = await create_post_live_report(
            self.db,
            task.session_id,
            trace_id=task.trace_id,
            created_by_agent_run_id=run_id,
            commit=False,
        )
        await self._subagent_result(
            task,
            "report",
            {
                "report_id": report["report_id"],
                "metrics": report["metrics"],
                "memory_updates": report["memory_updates"],
            },
        )
        return {
            "trace_id": task.trace_id,
            "session_id": task.session_id,
            "workflow_name": "meerkat.liveops.post_live_report",
            "report_id": report["report_id"],
            "created_entities": {"post_live_report_id": report["report_id"]},
            "metrics": report["metrics"],
            "memory_updates": report["memory_updates"],
            "summary_markdown": report["summary_markdown"],
            "alert_created": False,
        }

    async def _handle_stream_health(self, task: AgentTask, registry: ToolRegistry, stream_incident_id: int | None) -> dict[str, Any]:
        if stream_incident_id is None:
            return {"trace_id": task.trace_id, "alert_created": False, "reason": "missing stream_incident_id"}
        alert_type = AlertType(task.alert_type_hint or AlertType.STREAM_INTERRUPTED.value)
        await self._dispatch(task, "stream_monitor", {"stream_incident_id": stream_incident_id})
        context = await registry.call("get_stream_incident_context", {"stream_incident_id": stream_incident_id}, agent_name="stream_monitor")
        await self._subagent_result(
            task,
            "stream_monitor",
            {
                "incident_type": alert_type.value,
                "confidence": 0.92,
                "recommended_actions": ["检查 OBS 连接", "暂停商品讲解", "使用备用话术安抚观众"],
            },
        )
        policies = await self._policy(task, registry, "推流 异常 断流 黑屏 无声 HLS")
        await self._risk(task, "LOW_RISK_WRITE", False, [])
        await self._action_plan(
            task,
            {
                "recommended_actions": ["创建推流异常告警", "生成场控话术", "持续观察恢复状态"],
                "incident_type": alert_type.value,
            },
        )
        alert = await registry.call(
            "create_ops_alert",
            {
                "session_id": task.session_id,
                "alert_type": alert_type.value,
                "severity": AlertSeverity.P1.value,
                "title": f"直播推流异常：{alert_type.value}",
                "summary": "stream_monitor_agent 已根据推流健康样本识别异常，并生成场控处理建议。",
                "evidence": {"stream_incident_id": stream_incident_id, "context": context, "policies": policies["items"]},
            },
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="commander", action_type="ALERT_CREATED", output_data={"alert_id": alert["id"]})
        note = await registry.call(
            "create_speaker_note",
            {
                "session_id": task.session_id,
                "alert_id": alert["id"],
                "body": "当前直播信号出现波动，请场控确认 OBS 和网络状态，主播先暂停关键商品承诺，等待恢复确认。",
                "target": "field_control",
            },
            agent_name="script",
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="script", parent_agent_name="commander", action_type="SPEAKER_NOTE_CREATED", output_data={"speaker_note_id": note["id"]})
        return {
            "trace_id": task.trace_id,
            "session_id": task.session_id,
            "workflow_name": "meerkat.liveops.handle_stream_health",
            "incident_type": alert_type.value,
            "tool_calls": ["get_stream_incident_context", "search_policy_docs", "create_ops_alert", "create_speaker_note"],
            "risk_level": "LOW_RISK_WRITE",
            "created_entities": {
                "stream_incident_id": stream_incident_id,
                "ops_alert_id": alert["id"],
                "speaker_note_id": note["id"],
                "approval_task_id": None,
            },
            "alert_created": True,
        }

    async def _handle_coupon(self, task: AgentTask, registry: ToolRegistry, comment_ids: list[int], coupon_id: int) -> dict[str, Any]:
        await self._dispatch(task, "coupon", {"coupon_id": coupon_id})
        coupon = await registry.call("get_coupon_detail", {"coupon_id": coupon_id}, agent_name="coupon")
        policies = await self._policy(task, registry, "优惠券 未生效 领不了")
        await self._risk(task, "DESTRUCTIVE", True, ["change_coupon_time"])
        await self._action_plan(
            task,
            {
                "recommended_actions": ["提示主播说明优惠券生效时间", "发起优惠券提前生效审批"],
                "forbidden_actions": ["change_coupon_time"],
            },
        )
        note_body = f"刚刚有用户反馈优惠券暂时领不了，我们核实到该券将在 {coupon.get('starts_at')} 生效，请大家稍后再领取。运营同学正在确认是否可以提前生效。"
        alert = await registry.call(
            "create_ops_alert",
            {
                "session_id": task.session_id,
                "alert_type": AlertType.COUPON_UNAVAILABLE.value,
                "severity": AlertSeverity.P1.value,
                "title": "优惠券未生效，用户反馈不可领取",
                "summary": "评论窗口内多次出现优惠券不可领取反馈，Agent 已查询券状态并触发审批。",
                "evidence": {"comment_ids": comment_ids, "coupon": coupon, "policies": policies["items"]},
                "coupon_id": coupon_id,
            },
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="commander", action_type="ALERT_CREATED", output_data={"alert_id": alert["id"]})
        proposal = await registry.call(
            "create_action_proposal",
            {
                "session_id": task.session_id,
                "alert_id": alert["id"],
                "action_type": "CHANGE_COUPON_TIME",
                "risk_level": "DESTRUCTIVE",
                "arguments": {"coupon_id": coupon_id, "requested_change": "start_now"},
                "reason": "优惠券未生效导致直播间多名用户反馈不可领取。",
                "status": "APPROVAL_CREATED",
                "created_by_agent": "risk",
            },
            agent_name="risk",
        )
        note = await registry.call("create_speaker_note", {"session_id": task.session_id, "alert_id": alert["id"], "body": note_body, "target": "anchor"}, agent_name="script")
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="script", parent_agent_name="commander", action_type="SPEAKER_NOTE_CREATED", output_data={"speaker_note_id": note["id"]})
        approval = await registry.call(
            "create_approval_task",
            {
                "session_id": task.session_id,
                "proposal_id": proposal["id"],
                "title": "审批优惠券提前生效",
                "reason": "修改优惠券生效时间属于破坏性动作，Meerkat Agent 只创建审批任务。",
                "payload": {"forbidden_tool": "change_coupon_time", "coupon_id": coupon_id},
                "risk_level": "DESTRUCTIVE",
            },
            agent_name="risk",
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="risk", parent_agent_name="commander", action_type="APPROVAL_CREATED", output_data={"approval_task_id": approval["id"]}, risk_level="DESTRUCTIVE")
        return self._result(task, AlertType.COUPON_UNAVAILABLE, ["search_recent_comments", "get_live_products", "get_coupon_detail", "search_policy_docs", "create_ops_alert", "create_action_proposal", "create_speaker_note", "create_approval_task"], alert, note, approval, "DESTRUCTIVE")

    async def _handle_inventory(self, task: AgentTask, registry: ToolRegistry, comment_ids: list[int], product_id: int) -> dict[str, Any]:
        await self._dispatch(task, "product", {"product_id": product_id})
        product = await registry.call("get_product_detail", {"product_id": product_id}, agent_name="product")
        inventory = await registry.call("get_product_inventory", {"product_id": product_id}, agent_name="product")
        policies = await self._policy(task, registry, "库存 拍不了 下不了单")
        await self._risk(task, "LOW_RISK_WRITE", False, ["hide_product_from_live"])
        await self._action_plan(
            task,
            {
                "recommended_actions": ["创建库存告警", "提示主播暂停讲解或切换替代商品"],
                "forbidden_actions": ["hide_product_from_live"],
            },
        )
        alert = await registry.call(
            "create_ops_alert",
            {
                "session_id": task.session_id,
                "alert_type": AlertType.INVENTORY_UNAVAILABLE.value,
                "severity": AlertSeverity.P1.value,
                "title": "商品库存不足，用户反馈无法下单",
                "summary": f"{product.get('name')} 库存为 {inventory.get('total_available')}，建议主播暂停讲解或切换替代商品。",
                "evidence": {"comment_ids": comment_ids, "product": product, "inventory": inventory, "policies": policies["items"]},
                "product_id": product_id,
            },
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="commander", action_type="ALERT_CREATED", output_data={"alert_id": alert["id"]})
        await registry.call(
            "create_action_proposal",
            {
                "session_id": task.session_id,
                "alert_id": alert["id"],
                "action_type": "PAUSE_PRODUCT_INTRO",
                "risk_level": "LOW_RISK_WRITE",
                "arguments": {"product_id": product_id, "total_available": inventory.get("total_available")},
                "reason": "库存不足时建议主播暂停讲解或切换替代商品，不直接下架商品。",
                "created_by_agent": "risk",
            },
            agent_name="risk",
        )
        note = await registry.call(
            "create_speaker_note",
            {"session_id": task.session_id, "alert_id": alert["id"], "body": f"当前 {product.get('name')} 部分规格库存已经售罄，大家可以先查看其他规格或等待运营补货信息。", "target": "anchor"},
            agent_name="script",
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="script", parent_agent_name="commander", action_type="SPEAKER_NOTE_CREATED", output_data={"speaker_note_id": note["id"]})
        return self._result(task, AlertType.INVENTORY_UNAVAILABLE, ["search_recent_comments", "get_live_products", "get_product_detail", "get_product_inventory", "search_policy_docs", "create_ops_alert", "create_action_proposal", "create_speaker_note"], alert, note, None, "LOW_RISK_WRITE")

    async def _handle_price(self, task: AgentTask, registry: ToolRegistry, comment_ids: list[int], product_id: int) -> dict[str, Any]:
        await self._dispatch(task, "product", {"product_id": product_id})
        product = await registry.call("get_product_detail", {"product_id": product_id}, agent_name="product")
        policies = await self._policy(task, registry, "价格 口播 页面价 虚假宣传")
        await self._risk(task, "DESTRUCTIVE", True, ["change_product_price"])
        await self._action_plan(
            task,
            {
                "recommended_actions": ["生成价格口径补救话术", "发起价格处理审批"],
                "forbidden_actions": ["change_product_price"],
            },
        )
        alert = await registry.call(
            "create_ops_alert",
            {
                "session_id": task.session_id,
                "alert_type": AlertType.PRICE_MISMATCH.value,
                "severity": AlertSeverity.P0.value,
                "title": "主播口播价与页面价不一致",
                "summary": f"{product.get('name')} 口播价 {product.get('script_price')}，页面价 {product.get('page_price')}，需要人工确认活动口径。",
                "evidence": {"comment_ids": comment_ids, "product": product, "policies": policies["items"]},
                "product_id": product_id,
            },
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="commander", action_type="ALERT_CREATED", output_data={"alert_id": alert["id"]})
        note = await registry.call(
            "create_speaker_note",
            {"session_id": task.session_id, "alert_id": alert["id"], "body": "刚才价格口径需要核实，请大家以商品详情页展示为准，我们马上确认活动价格。", "target": "anchor"},
            agent_name="script",
        )
        proposal = await registry.call(
            "create_action_proposal",
            {
                "session_id": task.session_id,
                "alert_id": alert["id"],
                "action_type": "CHANGE_PRICE",
                "risk_level": "DESTRUCTIVE",
                "arguments": {"product_id": product_id, "script_price": product.get("script_price"), "page_price": product.get("page_price")},
                "reason": "主播口播价和页面价不一致，改价必须进入人工审批。",
                "status": "APPROVAL_CREATED",
                "created_by_agent": "risk",
            },
            agent_name="risk",
        )
        approval = await registry.call(
            "create_approval_task",
            {
                "session_id": task.session_id,
                "proposal_id": proposal["id"],
                "title": "审批价格口径处理方案",
                "reason": "改价属于破坏性动作，Agent 不直接执行 change_product_price。",
                "payload": {"forbidden_tool": "change_product_price", "product_id": product_id},
                "risk_level": "DESTRUCTIVE",
            },
            agent_name="risk",
        )
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="risk", parent_agent_name="commander", action_type="APPROVAL_CREATED", output_data={"approval_task_id": approval["id"]}, risk_level="DESTRUCTIVE")
        return self._result(task, AlertType.PRICE_MISMATCH, ["search_recent_comments", "get_live_products", "get_product_detail", "search_policy_docs", "create_ops_alert", "create_speaker_note", "create_action_proposal", "create_approval_task"], alert, note, approval, "DESTRUCTIVE")

    async def _policy(self, task: AgentTask, registry: ToolRegistry, query: str) -> dict[str, Any]:
        await self._dispatch(task, "policy", {"query": query})
        policies = await registry.call("search_policy_docs", {"query": query, "top_k": 3}, agent_name="policy")
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="policy", parent_agent_name="commander", action_type="POLICY_RETRIEVED", output_data=policies)
        return policies

    async def _risk(self, task: AgentTask, risk_level: str, requires_approval: bool, forbidden_actions: list[str]) -> None:
        await self._dispatch(task, "risk", {"risk_level": risk_level, "forbidden_actions": forbidden_actions})
        await write_log(
            self.db,
            trace_id=task.trace_id,
            session_id=task.session_id,
            agent_name="risk",
            parent_agent_name="commander",
            action_type="RISK_DECISION",
            output_data={"risk_level": risk_level, "requires_approval": requires_approval, "forbidden_actions": forbidden_actions},
            risk_level=risk_level,
        )
        await self._dispatch(task, "script", {"risk_level": risk_level})

    async def _action_plan(self, task: AgentTask, payload: dict[str, Any]) -> None:
        await write_log(
            self.db,
            trace_id=task.trace_id,
            session_id=task.session_id,
            agent_name="commander",
            action_type="ACTION_PLAN_CREATED",
            output_data=payload,
        )

    async def _dispatch(self, task: AgentTask, agent_name: str, payload: dict[str, Any]) -> None:
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name="commander", action_type="SUBAGENT_DISPATCH", output_data={"to": agent_name, **payload})

    async def _subagent_result(self, task: AgentTask, agent_name: str, payload: dict[str, Any]) -> None:
        await write_log(self.db, trace_id=task.trace_id, session_id=task.session_id, agent_name=agent_name, parent_agent_name="commander", action_type="SUBAGENT_RESULT", output_data=payload)

    def _result(
        self,
        task: AgentTask,
        alert_type: AlertType,
        tool_calls: list[str],
        alert: dict[str, Any],
        note: dict[str, Any],
        approval: dict[str, Any] | None,
        risk_level: str,
    ) -> dict[str, Any]:
        return {
            "trace_id": task.trace_id,
            "session_id": task.session_id,
            "workflow_name": "meerkat.liveops.handle_anomaly",
            "alert_type": alert_type.value,
            "tool_calls": tool_calls,
            "risk_level": risk_level,
            "created_entities": {
                "ops_alert_id": alert["id"],
                "speaker_note_id": note["id"],
                "approval_task_id": approval["id"] if approval else None,
            },
            "alert_created": True,
        }
