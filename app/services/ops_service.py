"""运维观测服务：任务耗时 / 工具成功率 / Token 消耗 / 高频错误。"""
from __future__ import annotations

from typing import Any

from app.storage.sqlite.repositories.log_repo import log_repo


class OpsService:
    @staticmethod
    async def tool_stats(days: int = 7) -> list[dict[str, Any]]:
        return await log_repo.tool_call_stats(days)

    @staticmethod
    async def token_stats(days: int = 7) -> list[dict[str, Any]]:
        return await log_repo.token_usage_stats(days)

    @staticmethod
    async def top_errors(days: int = 7, limit: int = 20) -> list[dict[str, Any]]:
        return await log_repo.top_errors(days, limit)

    @staticmethod
    async def task_latency(days: int = 7) -> list[dict[str, Any]]:
        return await log_repo.task_latency_stats(days)


ops_service = OpsService()
