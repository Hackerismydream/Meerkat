from __future__ import annotations

import asyncio

from _demo_common import run_demo


async def main() -> None:
    await run_demo("owncast-message", ["券领不了", "为什么没有 50 元券", "点进去没有券啊"])


if __name__ == "__main__":
    asyncio.run(main())
