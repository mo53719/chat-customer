"""敏感词过滤：内容风控，搜索/输入/输出都过一遍。"""
from __future__ import annotations

import re
from typing import Iterable

from app.logger import get_logger

_log = get_logger("security.sensitive")

# 基础敏感词库（演示用，生产环境建议用专业词库 + 第三方服务）
_DEFAULT_SENSITIVE_WORDS = [
    "法轮功", "反动", "色情", "暴力恐怖", "毒品", "枪支", "赌博",
    "傻逼", "操你", "草你", "fuck", "shit", "asshole", "cunt",
    "习近平", "毛泽东",  # 演示用，生产应由专有词库
]

_word_set: set[str] = set(w.lower() for w in _DEFAULT_SENSITIVE_WORDS)
_word_patterns: list[re.Pattern] = [re.compile(re.escape(w), re.IGNORECASE) for w in _DEFAULT_SENSITIVE_WORDS]


def add_words(words: Iterable[str]) -> None:
    """动态添加敏感词。"""
    for w in words:
        if not w:
            continue
        _word_set.add(w.lower())
        _word_patterns.append(re.compile(re.escape(w), re.IGNORECASE))


def is_sensitive(text: str) -> bool:
    """判断文本是否包含敏感词。"""
    if not text:
        return False
    low = text.lower()
    for w in _word_set:
        if w in low:
            return True
    return False


def filter_sensitive(text: str, replace_char: str = "**") -> str:
    """把敏感词替换为 replace_char。"""
    if not text:
        return text
    out = text
    for p in _word_patterns:
        out = p.sub(lambda m: replace_char * len(m.group(0)), out)
    return out


def list_sensitive_words() -> list[str]:
    """返回当前词库（去重）。"""
    return sorted(_word_set)
