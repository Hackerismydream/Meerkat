from __future__ import annotations

import httpx


class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def get(self, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10) as client:
            response = await client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, json: dict | None = None) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=20) as client:
            response = await client.post(path, json=json or {})
        response.raise_for_status()
        return response.json()
