"""Qdrant 集合管理。维度变化时自动重建。"""
from __future__ import annotations

from config.settings import settings
from app.logger import get_logger

from .client import get_qdrant

_log = get_logger("storage.qdrant")


async def _get_existing_dim(client, name: str) -> int | None:
    """异步读取已存在集合的向量维度；不存在或读取失败返回 None。"""
    try:
        info = await client.get_collection(collection_name=name)
        # 不同 qdrant-client 版本结构可能不同：优先取 vectors_config
        vc = getattr(info, "config", None)
        if vc is not None:
            params = getattr(vc, "params", None)
            if params is not None:
                vectors = getattr(params, "vectors", None)
                if isinstance(vectors, dict) and "size" in vectors:
                    return int(vectors["size"])
                if hasattr(vectors, "size"):
                    return int(vectors.size)
        # 旧版兜底
        vc = getattr(info, "vectors_config", None)
        if isinstance(vc, dict) and "size" in vc:
            return int(vc["size"])
        if hasattr(vc, "size"):
            return int(vc.size)
    except Exception as e:
        _log.debug(f"读取集合 {name} 维度失败：{e}")
    return None


async def ensure_collection(name: str, vector_dim: int | None = None) -> None:
    """确保集合存在。如果集合已存在但维度不匹配，自动删旧建新。"""
    dim = vector_dim or settings.EMBEDDING_DIM
    client = get_qdrant()
    cols = await client.get_collections()
    collection_list = getattr(cols, "collections", cols)
    names = [c.name for c in collection_list]

    if name in names:
        existing_dim = await _get_existing_dim(client, name)
        if existing_dim == dim:
            _log.debug(f"集合 {name} 已存在，维度 {dim} 匹配")
            await _ensure_payload_indexes(client, name)
            return
        if existing_dim is not None:
            # 维度明确不匹配 → 删旧建新
            _log.warning(
                f"集合 {name} 维度不匹配（existing={existing_dim}, expected={dim}），"
                f"删除旧集合并重建"
            )
            await client.delete_collection(collection_name=name)
        else:
            # 无法读取维度（集合可能正在被其他操作影响），保留并复用
            _log.debug(f"集合 {name} 已存在但维度不可读，跳过重建")
            await _ensure_payload_indexes(client, name)
            return

    await client.create_collection(
        collection_name=name,
        vectors_config={"size": dim, "distance": "Cosine"},
    )
    _log.info(f"创建集合 {name} 维度 {dim}")
    await _ensure_payload_indexes(client, name)


async def _ensure_payload_indexes(client, name: str) -> None:
    """对已存在集合补建 payload 索引；已存在则跳过。"""
    from qdrant_client.http import models as qmodels
    indexed_fields = {
        "doc_id": qmodels.PayloadSchemaType.KEYWORD,
        "source": qmodels.PayloadSchemaType.KEYWORD,
        "sheet": qmodels.PayloadSchemaType.KEYWORD,
        "heading_path": qmodels.PayloadSchemaType.KEYWORD,
        "chunk_idx": qmodels.PayloadSchemaType.INTEGER,
        "row": qmodels.PayloadSchemaType.INTEGER,
    }
    for field, ftype in indexed_fields.items():
        try:
            await client.create_payload_index(
                collection_name=name, field_name=field, field_schema=ftype,
            )
            _log.info(f"补建索引 {name}.{field} ({ftype})")
        except Exception as e:
            # 已存在索引或字段不存在 → 跳过
            _log.debug(f"创建索引 {name}.{field} 跳过：{e}")


async def delete_collection(name: str) -> None:
    client = get_qdrant()
    await client.delete_collection(collection_name=name)
    _log.info(f"删除集合 {name}")
