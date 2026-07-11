"""售后咨询 Agent。"""
from __future__ import annotations

from .base import run_business_agent
from .state import AgentState

ALLOWED_TOOLS = ["query_order", "rag_search"]


async def aftersales_agent(state: AgentState) -> AgentState:
    return await run_business_agent(state, "aftersales", ALLOWED_TOOLS)
