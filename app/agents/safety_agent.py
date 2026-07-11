"""安全过滤 Agent：入口风控，敏感词 + LLM 双重判定。"""
from __future__ import annotations

from app.logger import get_logger
from app.tools.safety_tools import safety_check
from .state import AgentState

_log = get_logger("agents.safety")


async def safety_agent(state: AgentState) -> AgentState:
    """入口安全过滤：命中敏感词直接拦截。"""
    state.current_agent = "safety"
    result = await safety_check(state, text=state.user_input)
    if not result.success:
        from config.settings import settings
        state.intent = "safety"
        state.final_answer = settings.FALLBACK_TEXT
        state.error = f"安全拦截：{result.error}"
        _log.info(f"安全拦截命中：{result.data}")
    return state


def is_blocked(state: AgentState) -> str:
    """路由条件：被拦截走 fallback。"""
    return "fallback" if state.error and "安全拦截" in state.error else "router"
