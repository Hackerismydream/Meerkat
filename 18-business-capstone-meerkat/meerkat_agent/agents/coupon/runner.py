from __future__ import annotations

from meerkat_agent.runtime.base_agent import AgentExecutionContext, AgentResult


class CouponRunner:
    name = "coupon"
    allowed_tools = ["get_coupon_detail"]

    async def run(self, input_data: dict, context: AgentExecutionContext) -> AgentResult:
        coupon = await context.registry.call("get_coupon_detail", {"coupon_id": input_data.get("coupon_id", 1)}, agent_name=self.name)
        return AgentResult(agent_name=self.name, status="OK", output={"coupon_context": coupon}, tool_calls=["get_coupon_detail"])
