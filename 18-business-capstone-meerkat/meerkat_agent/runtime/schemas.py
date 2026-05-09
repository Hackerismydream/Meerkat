from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentTool:
    name: str
    risk_level: str
    description: str
    handler: Any | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    allowed_agents: list[str] = field(default_factory=list)
    requires_approval: bool = False
    timeout_ms: int = 3000
    retry_policy: dict[str, Any] | None = None
    idempotency_key_strategy: str | None = None
    audit_policy: dict[str, Any] | None = None
