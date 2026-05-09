class RiskGuard:
    blocked_tools = {
        "change_coupon_time",
        "change_product_price",
        "hide_product_from_live",
    }

    def assert_allowed(self, tool_name: str, risk_level: str) -> None:
        if tool_name in self.blocked_tools or risk_level == "DESTRUCTIVE":
            raise PermissionError(f"{tool_name} is blocked by Meerkat risk guard")
