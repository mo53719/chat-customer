"""上下文长度控制：基于 tiktoken 估算 token，滑动窗口。"""
from __future__ import annotations

import tiktoken

from config.settings import settings

_enc = None


def _get_encoder():
    global _enc
    if _enc is None:
        try:
            _enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _enc = tiktoken.get_encoding("gpt2")
    return _enc


def count_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        return len(_get_encoder().encode(text))
    except Exception:
        return len(text) // 2  # 粗略估算


def trim_by_tokens(messages: list[dict], max_tokens: int | None = None,
                   keep_system: bool = True) -> list[dict]:
    """按 token 上限滑动窗口截断，保留 system 消息和最近若干条。"""
    limit = max_tokens or settings.CONTEXT_MAX_TOKENS
    if not messages:
        return []

    system_msgs = [m for m in messages if m.get("role") == "system"] if keep_system else []
    non_system = [m for m in messages if m.get("role") != "system"] if keep_system else messages[:]

    system_tokens = sum(count_tokens(m.get("content", "")) for m in system_msgs)
    remaining = limit - system_tokens

    kept: list[dict] = []
    total = 0
    for m in reversed(non_system):
        t = count_tokens(m.get("content", ""))
        if total + t > remaining:
            break
        kept.insert(0, m)
        total += t

    return system_msgs + kept
