"""Layer 1 规则路由：关键词 + 正则匹配，毫秒级响应。

规则从 main_agent.md 提取并固化到代码中，
拦截问候、告别、明确业务指令等高频明确意图。
"""
from __future__ import annotations

import re
from typing import Optional

from config.settings import settings
from app.logger import get_logger
from .state import AgentState

_log = get_logger("agents.rule_router")

# 意图优先级：更具体的意图优先（冲突时优先选择）
# e.g. "你好，我要退货" 同时匹配 presales 和 aftersales → 选 aftersales
INTENT_PRIORITY = ["aftersales", "order", "rag", "presales"]

# 意图规则表：每个意图对应一组正则
INTENT_RULES: dict[str, list[str]] = {
    "presales": [
        # 问候
        r"^(你好|您好|hi|hello|嗨|在吗|在不在|有人在吗|哈喽|嗨喽)",
        r"^(早上好|下午好|晚上好|早安|晚安|中午好)",
        # 告别
        r"^(谢谢|感谢|多谢|再见|拜拜|bye|88|谢了|3q|thanks)",
        # 自我介绍 / 能力询问
        r"^(你是谁|你是做什么的|你能做什么|介绍一下你自己|你是干嘛的|你有什么功能)",
        # 商品咨询
        r"(价格|多少钱|怎么卖|优惠|折扣|活动|促销|套餐|有什么|有什么产品|有哪些商品)",
    ],
    "aftersales": [
        r"(退货|退换|退款|换货|维修|保修|售后)",
        r"(质量问题|坏了|破损|瑕疵|有毛病|用不了|打不开|不能用)",
        r"(投诉|差评|不满|投诉你|举报|维权)",
        r"(补偿|赔偿|赔付|索赔)",
    ],
    "order": [
        r"(订单|物流|快递|发货|到哪了|还没到|催单|催发货|没收到|签收)",
        r"(订单号|运单号|查订单|查物流|快递单号|单号)",
        r"\b\d{12,}\b",  # 长数字（12位以上）可能是订单号
    ],
    "rag": [
        r"(怎么用|如何使用|使用说明|文档|教程|帮助|功能说明|操作指南)",
        r"(有没有.*(教程|文档|说明)|怎么(设置|配置|操作))",
    ],
}

# 编译正则，避免每次匹配都重新编译
_COMPILED_RULES: dict[str, list[re.Pattern]] = {}


def _get_compiled() -> dict[str, list[re.Pattern]]:
    """懒加载编译正则，首次调用时编译。"""
    if not _COMPILED_RULES:
        for intent, patterns in INTENT_RULES.items():
            _COMPILED_RULES[intent] = [re.compile(p) for p in patterns]
    return _COMPILED_RULES


def _match_rules(text: str) -> Optional[tuple[str, float]]:
    """尝试匹配所有规则，返回 (intent, confidence) 或 None。

    多个意图匹配时，按优先级选择最具体的意图。
    """
    compiled = _get_compiled()
    hits: list[tuple[str, float]] = []

    for intent, patterns in compiled.items():
        for pattern in patterns:
            if pattern.search(text):
                # 匹配计数：匹配到的模式越多，置信度越高
                hits.append((intent, 0.95))
                break  # 该意图已命中，跳到下一个意图

    if not hits:
        return None

    if len(hits) == 1:
        return hits[0]

    # 多意图冲突：按优先级选择
    priority_map = {intent: i for i, intent in enumerate(INTENT_PRIORITY)}
    hits.sort(key=lambda x: priority_map.get(x[0], 99))
    return hits[0]


async def rule_router(state: AgentState) -> AgentState:
    """规则层路由：关键词/正则匹配明确指令。

    命中则直接设置 intent 和 confidence，跳过后续层。
    未命中则保持 intent 为空，交给下一层处理。
    """
    if not settings.RULE_ROUTER_ENABLED:
        _log.debug("规则路由已禁用，跳过")
        return state

    state.current_agent = "rule_router"
    text = state.user_input.strip()

    if not text:
        return state

    result = _match_rules(text)
    if result:
        intent, confidence = result
        state.intent = intent
        state.intent_confidence = confidence
        state.router_layer = "rule"
        _log.info(f"规则层命中：intent={intent} input={text[:50]}")
    else:
        _log.debug(f"规则层未命中：{text[:50]}")

    return state


def is_rule_hit(state: AgentState) -> bool:
    """判断规则层是否命中。"""
    return bool(state.intent and state.router_layer == "rule")