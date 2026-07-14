"""售前咨询 Agent。
在调 LLM 前强制预取 RAG 知识库内容，注入到 system prompt，
确保 LLM 不会因为优先调 product_search 而漏掉知识库里的产品介绍。
"""
from __future__ import annotations

from app.logger import get_logger
from app.storage.qdrant.retriever import Retriever
from .base import run_business_agent
from .state import AgentState

_log = get_logger("agents.presales")

# 售前可用工具：RAG 知识库优先，商品搜索次之
ALLOWED_TOOLS = [
    "rag_search",
    "product_search",
    "product_search_semantic",
    "product_get_detail",
    "product_list_categories",
]


async def presales_agent(state: AgentState) -> AgentState:
    # 强制预取 RAG：确保 LLM 在思考前已经看到知识库相关内容
    if not state.rag_context:
        try:
            hits = await Retriever.search(query=state.user_input, top_k=5, use_rerank=True)
            if hits:
                chunks = []
                for h in hits:
                    text = h.get("text", "")[:500]
                    score = h.get("score", 0)
                    chunks.append(f"[相关度 {score:.2f}] {text}")
                state.rag_context = "\n\n---\n\n".join(chunks)
                _log.info(f"预取 RAG 上下文：{len(hits)} 条，总长 {len(state.rag_context)} 字")
        except Exception as e:
            _log.warning(f"RAG 预取失败，降级为无上下文：{e}")

    return await run_business_agent(state, "presales", ALLOWED_TOOLS)
