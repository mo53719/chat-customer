"""初始化 Qdrant 集合。"""
from __future__ import annotations

import asyncio

from config.settings import settings
from app.storage.qdrant.collection import ensure_collection
from app.logger import setup_logging, get_logger


async def main() -> None:
    setup_logging()
    log = get_logger("init_qdrant")
    await ensure_collection(settings.QDRANT_COLLECTION)
    await ensure_collection(settings.QDRANT_LONG_TERM_COLLECTION)
    log.info(f"Qdrant 集合就绪：{settings.QDRANT_COLLECTION}, {settings.QDRANT_LONG_TERM_COLLECTION}")


if __name__ == "__main__":
    asyncio.run(main())
