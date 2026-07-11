"""日志落库 handler：错误日志写入 run_logs 表，供运维面板查询。

为避免循环依赖，此处采用延迟导入 storage 模块。
"""
from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from .tracer import TraceContext


async def write_run_log(
    level: str,
    message: str,
    trace_id: str | None = None,
    module: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """异步写入 run_logs 表。

    失败时仅输出控制台日志，不抛异常，避免日志层影响主流程。
    """
    try:
        from app.storage.sqlite.repositories.log_repo import log_repo

        await log_repo.insert_run_log(
            level=level,
            message=message,
            trace_id=trace_id or TraceContext.current(),
            module=module,
            extra=extra,
        )
    except Exception as e:
        logger.bind(module="log_handler").warning(f"写入 run_logs 失败: {e}")


def schedule_write_run_log(*args, **kwargs) -> None:
    """同步接口：派发异步写库任务（fire and forget）。"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(write_run_log(*args, **kwargs))
    except RuntimeError:
        # 无运行中的事件循环，仅打印
        logger.bind(module="log_handler").debug("无事件循环，跳过 run_logs 写入")
