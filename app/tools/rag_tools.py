"""RAG 语义检索工具。"""
from __future__ import annotations

from .registry import register_tool, ToolResult
from app.storage.qdrant.retriever import Retriever


@register_tool(
    name="rag_search",
    description="从知识库中语义检索相关文档片段",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索问题"},
            "top_k": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
)
async def rag_search(state, query: str, top_k: int = 5) -> ToolResult:
    hits = await Retriever.search(query=query, top_k=top_k)
    return ToolResult(data=hits, meta={"count": len(hits)})
