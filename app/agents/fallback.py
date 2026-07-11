"""兜底节点：模型报错 / 无匹配意图 / 违规 / 超轮次 / 超时。"""
from __future__ import annotations

from config.settings import settings
from app.logger import get_logger

from .state import AgentState

_log = get_logger("agents.fallback")


async def fallback_node(state: AgentState) -> AgentState:
    reason = state.error or "未知原因"
    _log.warning(f"触发兜底：{reason} | session={state.session_id} | intent={state.intent}")
    state.final_answer = settings.FALLBACK_TEXT
    state.current_agent = "fallback"
    return state


async def timeout_fallback(state: AgentState, exc: Exception) -> AgentState:
    state.error = f"任务超时: {exc}"
    return await fallback_node(state)
