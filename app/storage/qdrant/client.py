"""Qdrant 客户端单例。支持 local（本地服务）和 embed（嵌入式）两种模式。"""
from __future__ import annotations

from qdrant_client import AsyncQdrantClient

from config.settings import settings

_qdrant: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        if settings.QDRANT_MODE == "embed":
            # 嵌入式：数据存放在本地文件夹，无需单独启动 Qdrant 服务
            _qdrant = AsyncQdrantClient(
                path=str(settings.qdrant_abs_path),
                timeout=30.0,
            )
        else:
            # 本地服务：需要先启动 Qdrant 服务（http://localhost:6333）
            _qdrant = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
                timeout=30.0,
            )
    return _qdrant


async def close_qdrant() -> None:
    global _qdrant
    if _qdrant is not None:
        await _qdrant.close()
        _qdrant = None


qdrant_client = get_qdrant  # 兼容导出（懒加载）