from __future__ import annotations

import asyncio
import os

import httpx


async def main() -> None:
    base_url = os.getenv("OWNCAST_BASE_URL", "http://127.0.0.1:8080")
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        response = await client.get("/api/status")
    response.raise_for_status()
    payload = response.json()
    print(f"owncast={base_url}")
    print(f"online={payload.get('online')}")
    print(f"viewer_count={payload.get('viewerCount')}")


if __name__ == "__main__":
    asyncio.run(main())
