"""全链路 trace_id 上下文管理。"""
from __future__ import annotations

import uuid
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


def gen_trace_id() -> str:
    """生成新的 trace_id。"""
    return uuid.uuid4().hex[:16]


class TraceContext:
    """上下文管理器：设置 trace_id 并在退出时还原。"""

    def __init__(self, trace_id: str | None = None):
        self._trace_id = trace_id or gen_trace_id()
        self._token = None

    def __enter__(self) -> str:
        self._token = trace_id_var.set(self._trace_id)
        return self._trace_id

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._token is not None:
            trace_id_var.reset(self._token)

    async def __aenter__(self) -> str:
        self._token = trace_id_var.set(self._trace_id)
        return self._trace_id

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._token is not None:
            trace_id_var.reset(self._token)

    @classmethod
    def current(cls) -> str:
        return trace_id_var.get()
