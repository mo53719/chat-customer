"""售后咨询 Agent。
在调 LLM 前强制预取 RAG 知识库内容，注入到 system prompt。
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from config.settings import settings
from app.logger import get_logger
from app.storage.qdrant.retriever import Retriever
from .base import run_business_agent
from .state import AgentState

_log = get_logger("agents.aftersales")

ALLOWED_TOOLS = ["query_order", "rag_search"]


async def aftersales_agent(state: AgentState) -> AgentState:
    if not state.rag_context:
        try:
            state.rag_context = await asyncio.wait_for(
                _prefetch_rag(state.user_input), timeout=settings.RAG_TIMEOUT
            )
        except asyncio.TimeoutError:
            _log.warning("RAG 预取超时，降级为无上下文")
        except Exception as e:
            _log.warning(f"RAG 预取失败，降级为无上下文：{e}")

    return await run_business_agent(state, "aftersales", ALLOWED_TOOLS)


async def _prefetch_rag(query: str) -> str:
    """RAG 预取，带超时保护。"""
    hits = await Retriever.search(query=query, top_k=5, use_rerank=True)
    if hits:
        chunks = []
        for h in hits:
            text = h.get("text", "")[:500]
            score = h.get("score", 0)
            chunks.append(f"[相关度 {score:.2f}] {text}")
        result = "\n\n---\n\n".join(chunks)
        _log.info(f"预取 RAG 上下文：{len(hits)} 条，总长 {len(result)} 字")
        return result
    return ""


async def aftersales_agent_stream(state: AgentState) -> AsyncIterator[str]:
    """流式输出：直接使用 LLM chat_stream 生成回答。"""
    from app.prompts.loader import load_prompt
    from app.memory.manager import memory_manager
    from app.llm import chat_stream

    sys_prompt = await load_prompt("aftersales_agent")
    if not sys_prompt:
        sys_prompt = "你是售后客服 Agent，请回应用户请求。"
    if state.rag_context:
        sys_prompt += "\n\n## 知识库检索结果\n" + state.rag_context

    messages = memory_manager.build_context(
        history=state.history,
        system_prompt=sys_prompt,
        user_input=state.user_input,
    )
    async for chunk in chat_stream(
        messages=messages, agent_name="aftersales_agent",
        session_id=state.session_id,
    ):
        yield chunk
