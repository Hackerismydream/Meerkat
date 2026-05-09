from __future__ import annotations

import asyncio
import argparse
import os
import sqlite3
from pathlib import Path

import httpx


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--configure", action="store_true")
    args = parser.parse_args()
    base_url = os.getenv("OWNCAST_BASE_URL", "http://127.0.0.1:8080")
    user = os.getenv("OWNCAST_ADMIN_USER", "admin")
    password = os.getenv("OWNCAST_ADMIN_PASSWORD", "abc123")
    webhook_url = os.getenv("OWNCAST_WEBHOOK_URL", "http://host.docker.internal:8018/api/v1/integrations/owncast/webhook")
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0, auth=(user, password)) as client:
        response = await client.get("/api/admin/webhooks")
        hooks = response.json() if response.status_code == 200 else []
        found = any(hook.get("url") == webhook_url for hook in hooks if isinstance(hook, dict))
        if args.configure and response.status_code == 200 and not found:
            create = await client.post("/api/admin/webhooks", json={"url": webhook_url, "events": ["CHAT", "STREAM_STARTED", "STREAM_STOPPED", "STREAM_TITLE_UPDATED"]})
            if create.status_code < 400:
                response = await client.get("/api/admin/webhooks")
                hooks = response.json()
                found = any(hook.get("url") == webhook_url for hook in hooks if isinstance(hook, dict))
            elif create.status_code == 405:
                db_path = Path(os.getenv("OWNCAST_DB_PATH", "owncast_data/owncast.db"))
                if db_path.exists():
                    with sqlite3.connect(db_path) as db:
                        db.execute(
                            "insert into webhooks(url, events) select ?, ? where not exists (select 1 from webhooks where url = ?)",
                            (webhook_url, "CHAT,STREAM_STARTED,STREAM_STOPPED,STREAM_TITLE_UPDATED", webhook_url),
                        )
                    response = await client.get("/api/admin/webhooks")
                    hooks = response.json()
                    found = any(hook.get("url") == webhook_url for hook in hooks if isinstance(hook, dict))
    print(f"owncast={base_url}")
    print(f"webhook_url={webhook_url}")
    print(f"GET /api/admin/webhooks -> {response.status_code}")
    if response.status_code == 200:
        print(hooks)
        if found:
            print("webhook_configured=true")
        else:
            print("webhook_configured=false")
            print("Manual step: open /admin/webhooks and add the URL above with CHAT, STREAM_STARTED, STREAM_STOPPED, STREAM_TITLE_UPDATED.")
    else:
        print("Could not verify Owncast webhook admin API. Configure it manually at /admin/webhooks instead of guessing a write endpoint.")


if __name__ == "__main__":
    asyncio.run(main())
