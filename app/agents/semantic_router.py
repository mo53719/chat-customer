"""Layer 2 语义路由：用嵌入模型做意图原型匹配。

复用现有 BAAI/bge-small-zh-v1.5 嵌入模型，
将用户输入与意图原型例句做余弦相似度匹配，
高相似度直接路由，避免 LLM 调用。
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from config.settings import settings
from app.logger import get_logger
from .state import AgentState

_log = get_logger("agents.semantic_router")

# 模块级缓存：原型向量（启动时计算一次）
_prototype_embeddings: dict[str, list[list[float]]] = {}
_prototypes: dict[str, list[str]] = {}
_initialized = False


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_prototypes() -> dict[str, list[str]]:
    """加载意图原型例句。"""
    global _prototypes
    if _prototypes:
        return _prototypes

    proto_path = Path(__file__).resolve().parent.parent.parent / "config" / "prompts" / "intent_prototypes.json"
    try:
        with open(proto_path, "r", encoding="utf-8") as f:
            _prototypes = json.load(f)
        _log.info(f"加载意图原型：{list(_prototypes.keys())}，共 {sum(len(v) for v in _prototypes.values())} 条")
    except Exception as e:
        _log.error(f"加载意图原型失败：{e}")
        _prototypes = {}
    return _prototypes


async def _ensure_initialized():
    """初始化：计算所有原型例句的嵌入向量。"""
    global _prototype_embeddings, _initialized
    if _initialized:
        return

    prototypes = _load_prototypes()
    if not prototypes:
        _log.warning("意图原型为空，语义路由不可用")
        _initialized = True
        return

    try:
        from app.llm.embedding import embed_texts

        for intent, examples in prototypes.items():
            if not examples:
                continue
            embeddings = await embed_texts(examples)
            _prototype_embeddings[intent] = embeddings
            _log.debug(f"意图 {intent}：{len(examples)} 条原型，{len(embeddings)} 条向量")

        _initialized = True
        _log.info(f"语义路由初始化完成：{len(_prototype_embeddings)} 个意图")
    except Exception as e:
        _log.error(f"语义路由初始化失败：{e}")
        _initialized = True  # 标记已初始化，避免反复重试


async def semantic_router(state: AgentState) -> AgentState:
    """语义层路由：嵌入向量相似度匹配。

    命中条件：最高相似度 > SEMANTIC_SIMILARITY_THRESHOLD
    对话历史加成：若上一轮意图与当前匹配意图一致，相似度 + SEMANTIC_HISTORY_BOOST
    """
    if not settings.SEMANTIC_ROUTER_ENABLED:
        _log.debug("语义路由已禁用，跳过")
        return state

    state.current_agent = "semantic_router"

    # 确保初始化
    await _ensure_initialized()

    if not _prototype_embeddings:
        _log.warning("语义路由未初始化，跳过")
        return state

    text = state.user_input.strip()
    if not text:
        return state

    try:
        from app.llm.embedding import embed_texts

        # 嵌入用户输入
        user_embeddings = await embed_texts([text])
        if not user_embeddings:
            return state
        user_vec = user_embeddings[0]

        # 计算与每个意图原型的相似度
        best_intent = None
        best_score = 0.0

        for intent, proto_vecs in _prototype_embeddings.items():
            # 取该意图下所有原型向量的最大相似度
            intent_score = max(_cosine_similarity(user_vec, pv) for pv in proto_vecs)

            if intent_score > best_score:
                best_score = intent_score
                best_intent = intent

        # 对话历史一致性加成
        if state.history:
            last_intent = None
            for msg in reversed(state.history):
                # 从历史消息中提取上一次的意图（存储在 agent 执行结果中）
                # 这里简化：检查 state.intent 是否已有值（由上一轮设置）
                pass
            # 如果当前轮次的 state 已有上一轮 intent（从 session 加载）
            if state.intent and best_intent and state.intent == best_intent:
                best_score += settings.SEMANTIC_HISTORY_BOOST
                _log.debug(f"历史一致性加成 +{settings.SEMANTIC_HISTORY_BOOST}，最终分数={best_score:.3f}")

        threshold = settings.SEMANTIC_SIMILARITY_THRESHOLD
        if best_intent and best_score >= threshold:
            state.intent = best_intent
            state.intent_confidence = best_score
            state.router_layer = "semantic"
            _log.info(f"语义层命中：intent={best_intent} score={best_score:.3f} input={text[:50]}")
        else:
            _log.debug(f"语义层未命中：best={best_intent} score={best_score:.3f} threshold={threshold} input={text[:50]}")

    except Exception as e:
        _log.error(f"语义路由异常：{e}")

    return state


def is_semantic_hit(state: AgentState) -> bool:
    """判断语义层是否命中。"""
    return bool(state.intent and state.router_layer == "semantic")