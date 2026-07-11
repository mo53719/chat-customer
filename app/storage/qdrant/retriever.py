"""语义检索：向量召回 top-k。"""
from __future__ import annotations

from typing import Any

from config.settings import settings
from app.logger import get_logger

from .client import get_qdrant

_log = get_logger("storage.qdrant.retriever")


class Retriever:
    @staticmethod
    async def search(query: str, top_k: int = 5, score_threshold: float | None = None,
                     collection: str | None = None,
                     filter_dict: dict[str, Any] | None = None,
                     use_rerank: bool | None = None) -> list[dict[str, Any]]:
        """向量召回 + 可选 rerank 精排。

        use_rerank:
          None -> 跟随 settings.RERANK_ENABLED
          True/False -> 强制开/关
        """
        from app.llm.embedding import embed_texts

        coll = collection or settings.QDRANT_COLLECTION
        vec = (await embed_texts([query]))[0]

        must_filters = []
        if filter_dict:
            for k, v in filter_dict.items():
                must_filters.append({"key": k, "match": {"value": v}})

        # 若启用 rerank，优先保召回，不在向量阶段做硬阈值过滤。
        rerank_on = settings.RERANK_ENABLED if use_rerank is None else use_rerank
        recall_k = settings.RERANK_TOP_N if rerank_on else top_k
        vector_threshold = None if rerank_on else (0.5 if score_threshold is None else score_threshold)

        client = get_qdrant()
        res = await client.search(
            collection_name=coll,
            query_vector=vec,
            limit=recall_k,
            score_threshold=vector_threshold,
            query_filter={"must": must_filters} if must_filters else None,
        )

        out = []
        for hit in res:
            payload = hit.payload or {}
            out.append({
                "score": float(hit.score),
                "vector_score": float(hit.score),
                "doc_id": payload.get("doc_id"),
                "title": payload.get("title"),
                "chunk_idx": payload.get("chunk_idx"),
                "text": payload.get("text"),
                "source": payload.get("source"),
                "sheet": payload.get("sheet"),
                "row": payload.get("row"),
                "heading_path": payload.get("heading_path"),
            })
        _log.debug(
            f"检索 {query[:30]}... 向量召回 {len(out)} 段 "
            f"(rerank_on={rerank_on}, vector_threshold={vector_threshold})"
        )

        if rerank_on and out:
            try:
                from app.llm.reranker import rerank
                out = await rerank(query, out, top_k=top_k)
            except Exception as e:
                _log.warning(f"rerank 降级：{e}")
                out = out[:top_k]
        else:
            out = out[:top_k]
        return out
