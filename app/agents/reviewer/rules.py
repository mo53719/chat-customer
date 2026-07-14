"""reviewer 规则集：每条规则独立、可插拔。纯本地规则，不调 LLM。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from config.settings import settings


@dataclass
class ReviewResult:
    rule: str
    passed: bool
    severity: str  # "warn" | "fail"
    reason: str


def check_empty(answer: str) -> ReviewResult:
    """规则1：答案不能为空或过短。"""
    if not answer or len(answer.strip()) < 2:
        return ReviewResult("empty", False, "fail", "答案为空")
    return ReviewResult("empty", True, "warn", "")


def check_harmful(answer: str) -> ReviewResult:
    """规则2：不能含违禁词。"""
    BLOCKED = getattr(settings, "BLOCKED_WORDS", [])
    if not BLOCKED:
        return ReviewResult("harmful", True, "warn", "")
    for word in BLOCKED:
        if word in answer:
            return ReviewResult("harmful", False, "fail", f"含违禁词: {word}")
    return ReviewResult("harmful", True, "warn", "")


def check_deflection(answer: str) -> ReviewResult:
    """规则3：不能是推诿话术。"""
    DEFLECT_PHRASES = [
        r"请咨询人工", r"请联系客服", r"无法回答",
        r"暂时没有.*销售", r"我们平台.*不提供",
    ]
    for pattern in DEFLECT_PHRASES:
        if re.search(pattern, answer):
            return ReviewResult("deflection", False, "warn", f"推诿话术: {pattern}")
    return ReviewResult("deflection", True, "warn", "")


def check_on_topic(answer: str, user_input: str) -> ReviewResult:
    """规则4：必须切题（关键词重合度检查）。"""
    q_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", user_input))
    if not q_words:
        return ReviewResult("off_topic", True, "warn", "")
    matched = sum(1 for w in q_words if w in answer)
    overlap = matched / len(q_words)
    if overlap < 0.3:
        return ReviewResult(
            "off_topic", False, "warn",
            f"低重合度: {overlap:.0%} ({matched}/{len(q_words)})"
        )
    return ReviewResult("off_topic", True, "warn", "")


RULES: list[Callable] = [check_empty, check_harmful, check_deflection, check_on_topic]