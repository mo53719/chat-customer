"""兜底节点：三级兜底策略。"""
from __future__ import annotations

import asyncio

from config.settings import settings
from app.logger import get_logger
from app.llm import chat
from .state import AgentState

_log = get_logger("agents.fallback")


async def fallback_node(state: AgentState) -> AgentState:
    """三级兜底：Level 1 RAG → Level 2 LLM 引导 → Level 3 转人工。"""
    reason = state.error or "未知原因"
    _log.warning(f"触发兜底：{reason} | session={state.session_id} | intent={state.intent}")
    state.current_agent = "fallback"

    # Level 1：尝试 RAG 搜索
    _log.info("兜底 Level 1：尝试 RAG 搜索")
    try:
        from app.tools.rag_tools import _search_kb
        search_result = await asyncio.wait_for(
            _search_kb(state.user_input, limit=3), timeout=settings.RAG_TIMEOUT
        )
        if search_result and len(search_result) > 0 and search_result[0].get("content"):
            _log.info("兜底 Level 1 命中：RAG 找到相关内容")
            context = "\n".join([h.get("content", "") for h in search_result[:3]])
            state.rag_context = context
            state.rag_hits = search_result[:3]
            resp = await chat(
                messages=[
                    {"role": "system", "content": "你是智能客服助手，请根据提供的知识库内容回答用户问题。如果知识库内容不相关，请诚实告知。"},
                    {"role": "user", "content": f"知识库内容：\n{context}\n\n用户问题：{state.user_input}"},
                ],
                temperature=0.7,
                agent_name="fallback",
                session_id=state.session_id,
            )
            state.final_answer = resp.content
            return state
    except (asyncio.TimeoutError, Exception):
        _log.warning("兜底 Level 1 RAG 超时或失败，降级到 Level 2")

    # Level 2：LLM 友好引导
    _log.info("兜底 Level 2：LLM 友好引导")
    try:
        resp = await chat(
            messages=[
                {"role": "system", "content": (
                    "你是智能客服助手。用户输入无法被准确识别意图。请友好地回复用户，"
                    "说明你能提供的帮助：售前咨询（商品、价格、活动）、售后处理（退货、换货、投诉）、"
                    "订单查询。请引导用户提供更具体的问题。"
                )},
                {"role": "user", "content": state.user_input},
            ],
            temperature=0.7,
            agent_name="fallback",
            session_id=state.session_id,
        )
        state.final_answer = resp.content
        return state
    except Exception as e:
        _log.error(f"兜底 Level 2 失败：{e}")

    # Level 3：转人工
    _log.info("兜底 Level 3：转人工")
    state.final_answer = settings.FALLBACK_TEXT
    return state


async def timeout_fallback(state: AgentState, exc: Exception) -> AgentState:
    state.error = f"任务超时: {exc}"
    return await fallback_node(state)
