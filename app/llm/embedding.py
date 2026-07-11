"""文本向量化模块。可插拔后端：local（fastembed + Qdrant ONNX）/ openai（兼容协议）。"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from openai import AsyncOpenAI

from config.settings import settings
from app.logger import get_logger
from .circuit_breaker import llm_circuit
from .retry import with_retry

_log = get_logger("llm.embedding")

# ============ 本地后端单例 ============
_local_model: Any | None = None
_local_lock = asyncio.Lock()


def _load_local_model():
    """懒加载 fastembed 模型（首次调用时执行）。"""
    global _local_model
    if _local_model is not None:
        return _local_model
    from fastembed import TextEmbedding

    cache_dir = str(settings.embedding_local_abs_path)
    if not os.path.isdir(cache_dir):
        raise FileNotFoundError(
            f"本地 embedding 模型目录不存在：{cache_dir}\n"
            f"请将 Qdrant/bge-small-zh-v1.5 模型文件放入该目录。"
        )

    # 关键：HF_HUB_OFFLINE=1 让 fastembed 不联网，直接用 cache_dir 下的本地模型
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    model_name = getattr(settings, "EMBEDDING_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
    _log.info(f"加载 fastembed 模型：{model_name} cache={cache_dir}")
    _local_model = TextEmbedding(
        model_name=model_name,
        cache_dir=cache_dir,
        threads=0,  # 0=自动选择线程数
    )
    return _local_model


# ============ 云端后端单例 ============
_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        base_url = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL
        api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        _openai_client = AsyncOpenAI(base_url=base_url, api_key=api_key or "empty")
    return _openai_client


# ============ 公开 API ============

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化。根据 EMBEDDING_BACKEND 自动选择本地 / 云端路径。"""
    if not texts:
        return []
    if not llm_circuit.allow():
        raise RuntimeError("熔断器开启，拒绝 embedding 请求")

    backend = (settings.EMBEDDING_BACKEND or "local").lower()
    try:
        if backend == "local":
            vecs = await _embed_local(texts)
        elif backend == "openai":
            vecs = await _embed_openai(texts)
        else:
            raise ValueError(f"未知 EMBEDDING_BACKEND={backend!r}（仅支持 local / openai）")
    except Exception as e:
        llm_circuit.record_failure()
        _log.error(f"embedding 失败（backend={backend}）：{e}")
        raise
    llm_circuit.record_success()
    return vecs


# ============ 本地实现 ============

async def _embed_local(texts: list[str]) -> list[list[float]]:
    """fastembed 编码。在线程池中跑避免阻塞事件循环。"""
    model = await asyncio.to_thread(_load_local_model)

    def _encode():
        # fastembed.embed() 是惰性生成器，必须 list() 物化
        return list(model.embed(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            parallel=0,  # 0=不强制并行，单线程稳定
        ))

    raw_vecs = await asyncio.to_thread(_encode)
    # numpy.ndarray → list[list[float]]
    vecs = [v.tolist() if hasattr(v, "tolist") else list(v) for v in raw_vecs]

    # L2 归一化：bge + cosine 推荐归一化输入向量，避免距离分数偏差
    if settings.EMBEDDING_NORMALIZE and vecs:
        try:
            import numpy as np
            arr = np.asarray(vecs, dtype="float32")
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            arr = arr / norms
            vecs = arr.tolist()
        except Exception as e:
            _log.warning(f"L2 归一化失败，返回原始向量：{e}")
    return vecs


# ============ 云端实现 ============

async def _embed_openai(texts: list[str]) -> list[list[float]]:
    """OpenAI 兼容协议。DashScope 单批最多 10 条。"""
    BATCH = 10

    async def _call(batch: list[str]):
        extra_params = {}
        if settings.EMBEDDING_DIM:
            extra_params["dimensions"] = settings.EMBEDDING_DIM
        try:
            return await _get_openai_client().embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=batch,
                **extra_params,
            )
        except TypeError:
            return await _get_openai_client().embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=batch,
            )

    all_vecs: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i + BATCH]
        resp = await with_retry(lambda b=batch: _call(b))
        all_vecs.extend(item.embedding for item in resp.data)
    return all_vecs


# ============ 健康检查（可选） ============

async def warmup() -> dict:
    """预热本地模型 + 探测维度。可在启动时手动调用。"""
    if (settings.EMBEDDING_BACKEND or "local").lower() != "local":
        return {"backend": "openai", "dim": settings.EMBEDDING_DIM}
    try:
        vecs = await embed_texts(["warmup"])
        actual_dim = len(vecs[0]) if vecs else 0
        return {
            "backend": "local",
            "path": str(settings.embedding_local_abs_path),
            "model": getattr(settings, "EMBEDDING_MODEL_NAME", "Qdrant/bge-small-zh-v1.5"),
            "dim": actual_dim,
            "expected_dim": settings.EMBEDDING_DIM,
            "ok": actual_dim == settings.EMBEDDING_DIM,
        }
    except Exception as e:
        return {"backend": "local", "error": str(e)}
