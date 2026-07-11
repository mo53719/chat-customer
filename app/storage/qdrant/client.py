"""Qdrant 客户端单例。"""
from __future__ import annotations

from qdrant_client import AsyncQdrantClient

from config.settings import settings

_qdrant: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            # 默认 5s 太短，云端经常超时；给读写 30s 容差
            timeout=30.0,
        )
    return _qdrant


async def close_qdrant() -> None:
    global _qdrant
    if _qdrant is not None:
        await _qdrant.close()
        _qdrant = None


qdrant_client = get_qdrant  # 兼容导出（懒加载）
