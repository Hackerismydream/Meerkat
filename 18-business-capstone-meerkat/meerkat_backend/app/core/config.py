import os
from pathlib import Path


class Settings:
    app_name = "meerkat-backend"
    database_url = os.getenv("MEERKAT_DATABASE_URL", "sqlite+aiosqlite:///./meerkat.db")
    owncast_base_url = os.getenv("OWNCAST_BASE_URL", "http://localhost:8080")
    owncast_access_token = os.getenv("OWNCAST_ACCESS_TOKEN", "")
    auto_send_owncast = os.getenv("MEERKAT_AUTO_SEND_OWNCAST", "false").lower() == "true"

    backend_dir = Path(__file__).resolve().parents[2]
    capstone_dir = backend_dir.parent
    knowledge_dir = capstone_dir / "meerkat_agent" / "knowledge"


settings = Settings()
