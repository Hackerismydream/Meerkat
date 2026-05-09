from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentTool:
    name: str
    risk_level: str
    description: str
    handler: Any
