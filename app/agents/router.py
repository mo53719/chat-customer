"""意图路由节点：调 LLM 输出意图标签 + 置信度。"""
from __future__ import annotations

import json

from app.logger import get_logger
from app.llm import chat
from app.llm.formatter import repair_json
from app.prompts.loader import load_prompt
from .state import AgentState

_log = get_logger("agents.router")


async def intent_router(state: AgentState) -> AgentState:
    """识别意图，低置信度走 fallback。"""
    state.current_agent = "router"
    sys_prompt = await load_prompt("main_agent")

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"用户输入：{state.user_input}\n\n请输出意图 JSON。"},
    ]
    try:
        resp = await chat(messages=messages, temperature=0.1, agent_name="router",
                          session_id=state.session_id)
        parsed = repair_json(resp.content)
        if parsed:
            data = json.loads(parsed)
            state.intent = data.get("intent", "fallback")
            state.intent_confidence = float(data.get("confidence", 0.0))
            state.needs_decomposition = bool(data.get("needs_decomposition", False))
            _log.info(f"意图识别：{state.intent} conf={state.intent_confidence:.2f}")
        else:
            state.intent = "fallback"
            state.intent_confidence = 0.0
    except Exception as e:
        _log.error(f"意图识别失败：{e}")
        state.intent = "fallback"
        state.error = str(e)

    return state


def route_by_intent(state: AgentState) -> str:
    """根据意图分发到对应业务 Agent。"""
    if state.intent_confidence < 0.6:
        return "fallback"
    if state.needs_decomposition:
        return "orchestrator"
    mapping = {
        "presales": "presales",
        "aftersales": "aftersales",
        "order": "order",
        "rag": "rag",
        "safety": "fallback",
        "fallback": "fallback",
    }
    return mapping.get(state.intent, "fallback")
