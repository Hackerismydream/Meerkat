from __future__ import annotations

import httpx

from app.core.config import settings


async def send_owncast_system_message(body: str, dry_run: bool | None = None) -> dict:
    if dry_run is None:
        dry_run = settings.owncast_dry_run
    if dry_run or not settings.auto_send_owncast:
        return {"dry_run": True, "body": body}
    if not settings.owncast_access_token:
        return {"dry_run": True, "error": "OWNCAST_ACCESS_TOKEN missing", "body": body}
    async with httpx.AsyncClient(base_url=settings.owncast_base_url, timeout=5) as client:
        response = await client.post(
            "/api/integrations/chat/system",
            headers={"Authorization": f"Bearer {settings.owncast_access_token}"},
            json={"body": body},
        )
        if response.status_code >= 400:
            return {"dry_run": True, "error": f"Owncast returned {response.status_code}", "status_code": response.status_code, "body": body}
        return {"dry_run": False, "status_code": response.status_code, "body": body}
