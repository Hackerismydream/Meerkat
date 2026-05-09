from __future__ import annotations

import httpx

from app.core.config import settings


async def send_owncast_system_message(body: str, dry_run: bool | None = None) -> dict:
    if dry_run is None:
        dry_run = settings.owncast_dry_run
    if dry_run or not settings.auto_send_owncast:
        return {"status": "DRY_RUN", "dry_run": True, "message": body, "body": body, "owncast_message_id": None, "error": None}
    if not settings.owncast_access_token:
        return {"status": "FAILED", "dry_run": False, "error": "OWNCAST_ACCESS_TOKEN missing", "message": body, "body": body, "owncast_message_id": None}
    try:
        async with httpx.AsyncClient(base_url=settings.owncast_base_url, timeout=5) as client:
            response = await client.post(
                "/api/integrations/chat/system",
                headers={"Authorization": f"Bearer {settings.owncast_access_token}"},
                json={"body": body},
            )
    except httpx.HTTPError as exc:
        return {"status": "FAILED", "dry_run": False, "error": str(exc), "message": body, "body": body, "owncast_message_id": None}
    if response.status_code >= 400:
        return {"status": "FAILED", "dry_run": False, "error": f"Owncast returned {response.status_code}", "status_code": response.status_code, "message": body, "body": body, "owncast_message_id": None}
    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") and response.content else {}
    return {"status": "SENT", "dry_run": False, "status_code": response.status_code, "message": body, "body": body, "owncast_message_id": payload.get("id")}
