import asyncio
import sys
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = CAPSTONE_DIR / "meerkat_backend"
for path in (CAPSTONE_DIR, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sqlalchemy import select

from app.db.base import AgentActionLog, ApprovalTask, LiveComment, OpsAlert, SpeakerNote
from app.db.session import SessionLocal
from app.services.serialization import model_to_dict


async def main() -> None:
    async with SessionLocal() as session:
        for model in (LiveComment, OpsAlert, SpeakerNote, ApprovalTask, AgentActionLog):
            rows = list((await session.scalars(select(model).limit(20))).all())
            print(f"\n{model.__tablename__}")
            for row in rows:
                print(model_to_dict(row))


asyncio.run(main())
