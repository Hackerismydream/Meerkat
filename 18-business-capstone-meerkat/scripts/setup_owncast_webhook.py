from __future__ import annotations

import asyncio
import os

import httpx


async def main() -> None:
    base_url = os.getenv("OWNCAST_BASE_URL", "http://127.0.0.1:8080")
    user = os.getenv("OWNCAST_ADMIN_USER", "admin")
    password = os.getenv("OWNCAST_ADMIN_PASSWORD", "")
    webhook_url = os.getenv("OWNCAST_WEBHOOK_URL", "http://host.docker.internal:8018/api/v1/integrations/owncast/webhook")
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0, auth=(user, password)) as client:
        response = await client.get("/api/admin/webhooks")
    print(f"owncast={base_url}")
    print(f"webhook_url={webhook_url}")
    print(f"GET /api/admin/webhooks -> {response.status_code}")
    if response.status_code == 200:
        print(response.text)
        print("Owncast admin webhook API is reachable. Create or verify the webhook in Admin UI if the desired URL is absent.")
    else:
        print("Could not verify Owncast webhook admin API. Configure it manually at /admin/webhooks instead of guessing a write endpoint.")


if __name__ == "__main__":
    asyncio.run(main())
