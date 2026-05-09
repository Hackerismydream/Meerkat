from __future__ import annotations

from meerkat_agent.runtime.base_agent import AgentExecutionContext, AgentResult


class ProductRunner:
    name = "product"
    allowed_tools = ["get_live_products", "get_product_detail", "get_product_inventory"]

    async def run(self, input_data: dict, context: AgentExecutionContext) -> AgentResult:
        products = await context.registry.call("get_live_products", {"session_id": context.session_id}, agent_name=self.name)
        return AgentResult(agent_name=self.name, status="OK", output={"product_context": products}, tool_calls=["get_live_products"])
