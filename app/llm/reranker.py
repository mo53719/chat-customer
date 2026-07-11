"""Rerank 模块：基于 fastembed CrossEncoder 对向量召回结果做精排。

入口：rerank(query, candidates, top_k) -> 排序后的 candidates
- candidates 元素需有 "text" 字段
- 失败/关闭时直接返回原始 candidates 前 top_k 条
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from config.settings import settings, PROJECT_ROOT
from app.logger import get_logger

_log = get_logger("llm.reranker")

_model: Any | None = None
_load_lock = asyncio.Lock()


def _load_model():
    global _model
    if _model is not None:
        return _model
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    # 项目内缓存目录，避免依赖系统临时目录
    cache_dir = PROJECT_ROOT / "models" / "reranker_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 走国内镜像，否则连不上 huggingface.co
    # 直接赋值（不依赖外部已设置），确保 fastembed 内部的 huggingface_hub 用这个 endpoint
    os.environ["HF_ENDPOINT"] = os.environ.get("HF_ENDPOINT") or "https://hf-mirror.com"
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    # 离线模式：和 embedding 一致，禁止联网，全部走本地 cache_dir
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    name = settings.RERANK_MODEL
    _log.info(f"加载 fastembed reranker：{name} cache={cache_dir}")
    _model = TextCrossEncoder(
        model_name=name,
        cache_dir=str(cache_dir),
        local_files_only=True,  # 强制仅使用本地文件
    )
    return _model


async def rerank(query: str, candidates: list[dict[str, Any]],
                 top_k: int | None = None) -> list[dict[str, Any]]:
    """对召回结果重排。失败/关闭时降级返回原序前 top_k。

    Args:
        query: 用户原始 query
        candidates: Retriever 返回的 chunk 列表，需含 "text"
        top_k: 最终返回数量，默认 settings.RERANK_FINAL_K
    """
    if not candidates:
        return []
    final_k = top_k or settings.RERANK_FINAL_K

    if not settings.RERANK_ENABLED:
        return candidates[:final_k]

    # 候选少于等于 final_k，无需 rerank
    if len(candidates) <= final_k:
        return candidates

    try:
        model = await asyncio.to_thread(_load_model)
        docs = [c.get("text", "") for c in candidates]

        def _score():
            return list(model.rerank(query=query, documents=docs))

        scores = await asyncio.to_thread(_score)

        # 联合排序：rerank score 降序
        ranked = sorted(zip(candidates, scores),
                        key=lambda x: float(x[1]), reverse=True)
        out = []
        for c, s in ranked[:final_k]:
            c2 = dict(c)
            c2["rerank_score"] = float(s)
            out.append(c2)
        _log.debug(f"rerank 输入 {len(candidates)} 输出 {len(out)} "
                  f"top1_score={out[0]['rerank_score']:.3f}")
        return out
    except Exception as e:
        _log.warning(f"rerank 失败降级：{e}")
        return candidates[:final_k]
