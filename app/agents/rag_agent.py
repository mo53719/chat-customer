"""RAG 查询 Agent。"""
from __future__ import annotations

from .base import run_business_agent
from .state import AgentState

ALLOWED_TOOLS = ["rag_search"]


async def rag_agent(state: AgentState) -> AgentState:
    return await run_business_agent(state, "rag", ALLOWED_TOOLS)
