"""安全过滤工具：敏感词 + 简单规则风控。"""
from __future__ import annotations

from .registry import register_tool, ToolResult

# 内置敏感词示例，实际可由配置或 DB 加载
SENSITIVE_WORDS = {
    "色情", "赌博", "毒品", "枪支", "炸弹", "反动",
    "法轮", "六四", "习近平", "毛泽东",
    "fuck", "shit", "bitch",
}


@register_tool(
    name="safety_check",
    description="对输入文本进行敏感词 / 违规内容风控判定",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)
async def safety_check(state, text: str) -> ToolResult:
    low = text.lower()
    hit = [w for w in SENSITIVE_WORDS if w.lower() in low]
    if hit:
        return ToolResult(
            success=False,
            data={"safe": False, "category": "sensitive_word", "hit": hit},
            error="命中敏感词",
        )
    return ToolResult(data={"safe": True, "category": None, "hit": []})
