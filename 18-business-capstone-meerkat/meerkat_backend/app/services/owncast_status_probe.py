from __future__ import annotations

from time import perf_counter
from typing import Any

import httpx


async def probe_owncast_status(base_url: str) -> dict[str, Any]:
    started = perf_counter()
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=2.0) as client:
            response = await client.get("/api/status")
        duration_ms = int((perf_counter() - started) * 1000)
        response.raise_for_status()
        payload = response.json()
        return {
            "probe_type": "OWNCAST_STATUS",
            "status": "OK",
            "duration_ms": duration_ms,
            "is_live": bool(payload.get("online", False)),
            "raw": payload,
            "error": None,
        }
    except Exception as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        return {
            "probe_type": "OWNCAST_STATUS",
            "status": "FAILED",
            "duration_ms": duration_ms,
            "is_live": False,
            "raw": {},
            "error": f"{base_url}: {exc}",
        }
