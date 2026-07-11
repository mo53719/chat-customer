"""工具层：Agent 可调用的标准化工具。

所有工具签名统一：async def fn(state: AgentState, **params) -> ToolResult
工具自动入库 tool_call_logs。
"""
from .registry import register_tool, get_tool, list_tools, ToolResult

__all__ = ["register_tool", "get_tool", "list_tools", "ToolResult"]
