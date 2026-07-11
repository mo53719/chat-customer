"""售前咨询 Agent。"""
from __future__ import annotations

from .base import run_business_agent
from .state import AgentState

# 售前可用工具：商品精确搜索 / 语义搜索 / 商品详情 / 分类列表 / 通用 RAG
ALLOWED_TOOLS = [
    "product_search",
    "product_search_semantic",
    "product_get_detail",
    "product_list_categories",
    "rag_search",
]


async def presales_agent(state: AgentState) -> AgentState:
    return await run_business_agent(state, "presales", ALLOWED_TOOLS)
