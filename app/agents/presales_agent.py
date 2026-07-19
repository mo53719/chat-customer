"""售前咨询 Agent。
在调 LLM 前强制预取 RAG 知识库内容，注入到 system prompt，
确保 LLM 不会因为优先调 product_search 而漏掉知识库里的产品介绍。
"""
from __future__ import annotations

import asyncio
import re
from typing import AsyncIterator

from config.settings import settings
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

# greeting 类关键词（不需要 RAG 搜索）
_GREETING_PATTERNS = [
    r"^(你好|您好|hi|hello|嗨|哈喽|在吗|在不在|有人在吗)",
    r"^(谢谢|感谢|多谢|thanks|thank)",
    r"^(再见|拜拜|bye|晚安|回头见)",
    r"^(早上好|下午好|晚上好|早安|午安)",
    r"^(你是谁|你叫什么|自我介绍|介绍下你自己)",
]


def _is_greeting(text: str) -> bool:
    """判断是否为问候/闲聊，不需要 RAG。"""
    text = text.strip().lower()
    for pattern in _GREETING_PATTERNS:
        if re.match(pattern, text):
            return True
    return False


async def presales_agent(state: AgentState) -> AgentState:
    # greeting/闲聊 不需要 RAG
    if _is_greeting(state.user_input):
        state.need_rag = False
        _log.info("识别为 greeting/闲聊，跳过 RAG 预取")
    elif not state.rag_context:
        # 需要 RAG，并行化：RAG 搜索和后续 LLM 调用的准备同时进行
        try:
            state.rag_context = await asyncio.wait_for(
                _prefetch_rag(state.user_input), timeout=settings.RAG_TIMEOUT
            )
        except asyncio.TimeoutError:
            _log.warning("RAG 预取超时，降级为无上下文")
        except Exception as e:
            _log.warning(f"RAG 预取失败，降级为无上下文：{e}")

    return await run_business_agent(state, "presales", ALLOWED_TOOLS)


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


async def presales_agent_stream(state: AgentState) -> AsyncIterator[str]:
    """流式输出：直接使用 LLM chat_stream 生成回答。"""
    # 加载提示词和上下文
    from app.prompts.loader import load_prompt
    from app.memory.manager import memory_manager
    from app.llm import chat_stream

    sys_prompt = await load_prompt("presales_agent")
    if not sys_prompt:
        sys_prompt = "你是售前客服 Agent，请回应用户请求。"
    if state.rag_context:
        sys_prompt += "\n\n## 知识库检索结果\n" + state.rag_context

    messages = memory_manager.build_context(
        history=state.history,
        system_prompt=sys_prompt,
        user_input=state.user_input,
    )
    async for chunk in chat_stream(
        messages=messages, agent_name="presales_agent",
        session_id=state.session_id,
    ):
        yield chunk
