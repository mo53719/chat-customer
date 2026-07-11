"""订单查询 Agent。"""
from __future__ import annotations

from .base import run_business_agent
from .state import AgentState

ALLOWED_TOOLS = ["query_order", "update_order_address", "urge_shipment", "urge_refund"]


async def order_agent(state: AgentState) -> AgentState:
    return await run_business_agent(state, "order", ALLOWED_TOOLS)
