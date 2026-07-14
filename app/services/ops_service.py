"""运维观测服务：任务耗时 / 工具成功率 / Token 消耗 / 高频错误 / 系统状态。"""
from __future__ import annotations

import os
import platform
import time
from typing import Any

from app.storage.sqlite.connection import SqliteConnection
from app.storage.qdrant.client import get_qdrant
from app.storage.sqlite.repositories.log_repo import log_repo

START_TIME = time.time()


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

    @staticmethod
    async def system_status() -> dict[str, Any]:
        """系统状态检查：数据库、Qdrant、磁盘、内存、在线客服。"""
        status = {
            "server": {"status": "ok", "label": "服务器", "detail": "运行中"},
            "db": {"status": "ok", "label": "数据库", "detail": "SQLite"},
            "qdrant": {"status": "ok", "label": "Qdrant 向量库", "detail": ""},
            "disk": {"status": "ok", "label": "存储空间", "detail": ""},
            "memory": {"status": "ok", "label": "内存", "detail": ""},
            "online_agents": {"count": 0, "label": "在线客服"},
            "uptime_seconds": int(time.time() - START_TIME),
        }

        # 数据库检查
        try:
            await SqliteConnection.fetchone("SELECT 1")
        except Exception:
            status["db"]["status"] = "error"
            status["db"]["detail"] = "连接失败"

        # Qdrant 检查
        try:
            client = get_qdrant()
            await client.get_collections()
        except Exception:
            status["qdrant"]["status"] = "error"
            status["qdrant"]["detail"] = "连接失败"

        # 磁盘空间
        try:
            usage = os.popen("wmic logicaldisk where DeviceID='C:' get FreeSpace,Size /format:csv 2>nul").read()
            if usage:
                lines = [l for l in usage.strip().split("\n") if l and "Node" not in l]
                if lines:
                    parts = lines[-1].split(",")
                    free = int(parts[-1]) if len(parts) > 1 else 0
                    total = int(parts[-2]) if len(parts) > 2 else 1
                    free_gb = round(free / (1024 ** 3), 1)
                    total_gb = round(total / (1024 ** 3), 1)
                    used_pct = round((1 - free / total) * 100, 1)
                    status["disk"]["detail"] = f"已用 {used_pct}%（{free_gb}G / {total_gb}G）"
                    if used_pct > 90:
                        status["disk"]["status"] = "error"
                    elif used_pct > 70:
                        status["disk"]["status"] = "warning"
        except Exception:
            status["disk"]["status"] = "warning"
            status["disk"]["detail"] = "无法获取"

        # 内存使用
        try:
            mem = os.popen("wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /format:csv 2>nul").read()
            if mem:
                lines = [l for l in mem.strip().split("\n") if l and "Node" not in l]
                if lines:
                    parts = lines[-1].split(",")
                    free_mem = int(parts[-1]) if len(parts) > 1 else 0
                    total_mem = int(parts[-2]) if len(parts) > 2 else 1
                    used_pct = round((1 - free_mem / total_mem) * 100, 1)
                    free_gb = round(free_mem / 1024 / 1024, 1)
                    total_gb = round(total_mem / 1024 / 1024, 1)
                    status["memory"]["detail"] = f"已用 {used_pct}%（{free_gb}G / {total_gb}G）"
                    if used_pct > 90:
                        status["memory"]["status"] = "error"
                    elif used_pct > 70:
                        status["memory"]["status"] = "warning"
        except Exception:
            status["memory"]["status"] = "warning"
            status["memory"]["detail"] = "无法获取"

        # 在线客服数
        try:
            row = await SqliteConnection.fetchone(
                "SELECT COUNT(*) AS cnt FROM users WHERE status='active' AND deleted_at IS NULL"
            )
            status["online_agents"]["count"] = row["cnt"] if row else 0
        except Exception:
            status["online_agents"]["count"] = 0

        return status


ops_service = OpsService()
