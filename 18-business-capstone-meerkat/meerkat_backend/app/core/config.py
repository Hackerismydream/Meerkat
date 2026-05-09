import os
from pathlib import Path


class Settings:
    app_name = "meerkat-backend"
    database_url = os.getenv("MEERKAT_DATABASE_URL", "sqlite+aiosqlite:///./meerkat.db")
    owncast_base_url = os.getenv("OWNCAST_BASE_URL", "http://localhost:8080")
    owncast_public_url = os.getenv("OWNCAST_PUBLIC_URL", owncast_base_url)
    owncast_admin_user = os.getenv("OWNCAST_ADMIN_USER", "admin")
    owncast_admin_password = os.getenv("OWNCAST_ADMIN_PASSWORD", "")
    owncast_webhook_url = os.getenv("OWNCAST_WEBHOOK_URL", "http://host.docker.internal:8000/api/v1/integrations/owncast/webhook")
    owncast_access_token = os.getenv("OWNCAST_ACCESS_TOKEN", "")
    owncast_dry_run = os.getenv("OWNCAST_DRY_RUN", "true").lower() == "true"
    auto_send_owncast = os.getenv("OWNCAST_AUTO_SEND", os.getenv("MEERKAT_AUTO_SEND_OWNCAST", "false")).lower() == "true"
    backend_url = os.getenv("MEERKAT_BACKEND_URL", "http://localhost:8000")
    stream_probe_enabled = os.getenv("STREAM_PROBE_ENABLED", "false").lower() == "true"
    stream_probe_interval_seconds = int(os.getenv("STREAM_PROBE_INTERVAL_SECONDS", "10"))
    hls_playlist_url = os.getenv("HLS_PLAYLIST_URL", f"{owncast_base_url}/hls/stream.m3u8")

    backend_dir = Path(__file__).resolve().parents[2]
    capstone_dir = backend_dir.parent
    knowledge_dir = capstone_dir / "meerkat_agent" / "knowledge"


settings = Settings()
