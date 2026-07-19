"""Layer 3 LLM 路由节点：大模型兜底意图识别。

只在规则层（Layer 1）和语义层（Layer 2）都无法命中时触发。
"""
from __future__ import annotations

import json
from collections import OrderedDict
from typing import Optional

from config.settings import settings
from app.logger import get_logger
from app.llm import chat
from app.llm.formatter import repair_json
from app.prompts.loader import load_prompt
from .state import AgentState

_log = get_logger("agents.router")


class IntentCache:
    """LRU 缓存意图识别结果，避免相同输入重复 LLM 调用。"""
    def __init__(self, max_size: int = None):
        self._cache = OrderedDict()
        self._max_size = max_size or settings.INTENT_CACHE_SIZE
    
    def get(self, text: str) -> Optional[dict]:
        """获取缓存结果，异常时返回 None 降级。"""
        try:
            key = text.strip().lower()
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
        except Exception:
            _log.warning("缓存读取失败，降级为 LLM 调用")
            return None
    
    def set(self, text: str, result: dict):
        """存储缓存结果。"""
        try:
            key = text.strip().lower()
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                self._cache[key] = result
                if len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)
        except Exception:
            _log.warning("缓存写入失败，跳过缓存")


# 全局单例缓存
_intent_cache = IntentCache()


async def llm_router(state: AgentState) -> AgentState:
    """LLM 兜底意图识别，低置信度走 fallback。"""
    state.current_agent = "router"
    state.router_layer = "llm"
    
    # 尝试缓存命中
    cached = _intent_cache.get(state.user_input)
    if cached is not None:
        _log.info(f"意图缓存命中：{cached['intent']} conf={cached['confidence']:.2f}")
        state.intent = cached["intent"]
        state.intent_confidence = cached["confidence"]
        state.needs_decomposition = cached["needs_decomposition"]
        return state
    
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
            # 写入缓存
            _intent_cache.set(state.user_input, {
                "intent": state.intent,
                "confidence": state.intent_confidence,
                "needs_decomposition": state.needs_decomposition,
            })
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
    if state.intent_confidence < 0.5:
        return "fallback"
    if state.needs_decomposition:
        return "orchestrator"
    mapping = {
        "presales": "presales",
        "greeting": "presales",      # greeting 归类到 presales
        "aftersales": "aftersales",
        "order": "order",
        "rag": "rag",
        "safety": "fallback",
        "fallback": "fallback",
    }
    return mapping.get(state.intent, "fallback")
