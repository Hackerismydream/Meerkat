from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceConfig:
    backend_url: str = os.getenv("MEERKAT_BACKEND_URL", "http://127.0.0.1:8018")
    owncast_url: str = os.getenv("OWNCAST_BASE_URL", "http://127.0.0.1:8080")
    webhook_url: str = os.getenv("OWNCAST_WEBHOOK_URL", "http://host.docker.internal:8018/api/v1/integrations/owncast/webhook")
    admin_user: str = os.getenv("OWNCAST_ADMIN_USER", "admin")
    admin_password: str = os.getenv("OWNCAST_ADMIN_PASSWORD", "abc123")
