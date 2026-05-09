from __future__ import annotations

import httpx


class OwncastClient:
    def __init__(self, base_url: str, admin_user: str, admin_password: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (admin_user, admin_password)

    async def status(self) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10) as client:
            response = await client.get("/api/status")
        response.raise_for_status()
        return response.json()

    async def webhooks(self) -> list[dict]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10, auth=self.auth) as client:
            response = await client.get("/api/admin/webhooks")
        response.raise_for_status()
        return response.json()
