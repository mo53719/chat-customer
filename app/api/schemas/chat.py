"""对话相关 schema。"""
from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    channel: str = "web"
    stream: bool = False


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    intent: str | None = None
    agent: str | None = None
    tool_calls_count: int = 0
    rag_hits: list[dict] | None = None
    latency_ms: int | None = None
    token_input: int = 0
    token_output: int = 0
    error: str | None = None
    trace_id: str | None = None
    message_id: int | None = None
