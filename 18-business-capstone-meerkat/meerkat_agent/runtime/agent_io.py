from __future__ import annotations

from typing import Any


def require_keys(payload: dict[str, Any], required: list[str]) -> None:
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"missing required agent keys: {', '.join(missing)}")
