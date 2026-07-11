"""商品知识库索引器：把 SQLite 中的商品向量化后写入 Qdrant 商品集合。"""
from __future__ import annotations

import json
import uuid
from typing import Any

from qdrant_client.http import models as qmodels

from app.logger import get_logger
from config.settings import settings
from app.storage.sqlite import product_repo

from .client import get_qdrant
from .collection import ensure_collection

_log = get_logger("storage.qdrant.product_indexer")


def _build_product_text(p) -> str:
    """把商品各字段拼成一段自然语言，供 embedding。"""
    parts = [
        f"商品名：{p.name}",
        f"品牌：{p.brand or '通用'}",
        f"型号：{p.model or ''}",
        f"分类：{p.category_name or ''}",
    ]
    if p.highlights:
        parts.append(f"卖点：{p.highlights}")
    if p.description:
        parts.append(f"详细描述：{p.description}")
    if p.specs:
        spec_str = "，".join(f"{k}：{v}" for k, v in p.specs.items())
        parts.append(f"参数规格：{spec_str}")
    if p.package_contents:
        parts.append(f"包装清单：{p.package_contents}")
    if p.warranty:
        parts.append(f"保修：{p.warranty}")
    if p.tags:
        parts.append(f"标签：{', '.join(p.tags)}")
    parts.append(f"价格：¥{p.price}")
    if p.original_price and p.original_price > p.price:
        parts.append(f"原价：¥{p.original_price}")
    parts.append(f"库存：{p.stock}件")
    return " | ".join(parts)


async def reindex_all_products(batch_size: int = 10) -> int:
    """全量重建商品索引：删除旧数据，按商品逐条向量化写入。"""
    coll = settings.QDRANT_PRODUCT_COLLECTION
    await ensure_collection(coll)
    client = get_qdrant()

    # 1) 清空旧数据（用 points_selector=None 删全部）
    try:
        await client.delete_collection(collection_name=coll)
        await ensure_collection(coll)
        _log.info("已清空商品集合 %s", coll)
    except Exception as e:
        _log.warning(f"清空商品集合失败: {e}")

    # 2) 拉取全部商品
    products = await product_repo.list_all_for_kb()
    if not products:
        _log.warning("无商品可索引")
        return 0

    # 3) 批量向量化 + 写入
    from app.llm.embedding import embed_texts

    total = 0
    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        texts = [_build_product_text(p) for p in batch]
        vecs = await embed_texts(texts)
        points = []
        for p, vec in zip(batch, vecs):
            payload = {
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "brand": p.brand,
                "model": p.model,
                "category": p.category_name,
                "price": p.price,
                "stock": p.stock,
                "highlights": p.highlights or "",
                "description": p.description or "",
                "specs": json.dumps(p.specs or {}, ensure_ascii=False),
                "text": _build_product_text(p),
            }
            points.append(qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload=payload,
            ))
        await client.upsert(collection_name=coll, points=points, wait=True)
        total += len(batch)
        _log.info(f"商品索引进度 {total}/{len(products)}")

    _log.info(f"商品索引完成，共索引 {total} 条")
    return total


async def index_single_product(product_id: int) -> bool:
    """单条商品新增/更新时调用。"""
    from app.llm.embedding import embed_texts

    p = await product_repo.get_product_by_id(product_id)
    if not p:
        return False
    coll = settings.QDRANT_PRODUCT_COLLECTION
    await ensure_collection(coll)
    text = _build_product_text(p)
    vec = (await embed_texts([text]))[0]
    client = get_qdrant()
    point = qmodels.PointStruct(
        id=str(uuid.uuid4()),
        vector=vec,
        payload={
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "brand": p.brand,
            "model": p.model,
            "category": p.category_name,
            "price": p.price,
            "stock": p.stock,
            "highlights": p.highlights or "",
            "description": p.description or "",
            "specs": json.dumps(p.specs or {}, ensure_ascii=False),
            "text": text,
        },
    )
    await client.upsert(collection_name=coll, points=[point], wait=True)
    return True


async def search_products_semantic(query: str, top_k: int = 5,
                                   score_threshold: float = 0.4) -> list[dict[str, Any]]:
    """商品语义检索：售前 Agent 兜底使用。"""
    from app.llm.embedding import embed_texts

    coll = settings.QDRANT_PRODUCT_COLLECTION
    try:
        await ensure_collection(coll)
    except Exception as e:
        _log.warning(f"商品集合不可用: {e}")
        return []
    vec = (await embed_texts([query]))[0]
    client = get_qdrant()
    res = await client.search(
        collection_name=coll,
        query_vector=vec,
        limit=top_k,
        score_threshold=score_threshold,
    )
    out = []
    for hit in res:
        pl = hit.payload or {}
        out.append({
            "score": float(hit.score),
            "product_id": pl.get("product_id"),
            "sku": pl.get("sku"),
            "name": pl.get("name"),
            "brand": pl.get("brand"),
            "price": pl.get("price"),
            "stock": pl.get("stock"),
            "highlights": pl.get("highlights"),
            "description": pl.get("description"),
        })
    return out
