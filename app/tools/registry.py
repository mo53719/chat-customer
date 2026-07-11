"""工具注册中心。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.logger import get_logger
from app.logger.tracer import TraceContext
from app.storage.sqlite.repositories.log_repo import log_repo

_log = get_logger("tools.registry")

ToolFunc = Callable[..., Awaitable["ToolResult"]]


@dataclass
class ToolResult:
    success: bool = True
    data: Any = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema
    func: ToolFunc


_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(name: str, description: str, parameters: dict[str, Any]):
    """装饰器：注册工具。"""
    def decorator(func: ToolFunc) -> ToolFunc:
        async def wrapper(state: Any = None, **kwargs) -> ToolResult:
            t0 = time.time()
            trace_id = getattr(state, "trace_id", None) or TraceContext.current()
            session_id = getattr(state, "session_id", None) if state else None
            agent_name = getattr(state, "current_agent", None) if state else None
            try:
                result = await func(state, **kwargs)
                latency = int((time.time() - t0) * 1000)
                await log_repo.insert_tool_call(
                    trace_id=trace_id, session_id=session_id,
                    tool_name=name, agent_name=agent_name,
                    input_data=kwargs, output_data=result.data if result else None,
                    success=result.success, error=result.error,
                    latency_ms=latency,
                )
                return result
            except Exception as e:
                latency = int((time.time() - t0) * 1000)
                _log.exception(f"工具 {name} 执行异常：{e}")
                await log_repo.insert_tool_call(
                    trace_id=trace_id, session_id=session_id,
                    tool_name=name, agent_name=agent_name,
                    input_data=kwargs, output_data=None,
                    success=False, error=str(e), latency_ms=latency,
                )
                return ToolResult(success=False, error=str(e))

        _REGISTRY[name] = ToolSpec(
            name=name, description=description,
            parameters=parameters, func=wrapper,
        )
        _log.debug(f"注册工具：{name}")
        return wrapper
    return decorator


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def list_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def to_openai_tools() -> list[dict[str, Any]]:
    """导出为 OpenAI function-calling 格式。"""
    return [
        {"type": "function", "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        }}
        for spec in _REGISTRY.values()
    ]
