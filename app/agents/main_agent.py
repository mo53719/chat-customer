"""主 Agent：在 graph 中由 router + 各业务节点协同实现，此处保留语义入口。"""
from __future__ import annotations

from .state import AgentState


async def main_agent(state: AgentState) -> AgentState:
    """主 Agent 逻辑已拆分到 router + 业务 Agent + fallback。

    此函数保留作为语义入口，实际编排由 graph.py 完成。
    """
    return state
