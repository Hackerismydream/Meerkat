import asyncio
import sys

from app.db.base import Base
from app.db.session import engine


async def init_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def reset_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def main() -> None:
    if "--reset" in sys.argv:
        asyncio.run(reset_database())
    else:
        asyncio.run(init_database())


if __name__ == "__main__":
    main()
