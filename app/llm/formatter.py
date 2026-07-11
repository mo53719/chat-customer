"""输出格式自修复：当模型返回的 JSON 工具调用坏掉时尝试修复。"""
from __future__ import annotations

import json
import re

from app.logger import get_logger

_log = get_logger("llm.formatter")


def repair_json(text: str) -> str | None:
    """尝试从混乱文本中提取并修复 JSON。失败返回 None。"""
    if not text:
        return None
    text = text.strip()

    # 直接尝试
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # 提取 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    # 提取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        # 去除尾部多余逗号
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    _log.debug(f"JSON 修复失败：{text[:80]}")
    return None


def repair_output(text: str) -> str:
    """排版自修复：去除多余空行 / 修正缩进 / 去除控制字符。"""
    if not text:
        return text
    # 去除控制字符
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    # 多个空行压成一个
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 行尾空白
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()
