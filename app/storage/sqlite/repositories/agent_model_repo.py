"""Agent 模型配置仓储：每个 Agent 可独立设置模型、API 地址、温度等。"""
from __future__ import annotations

from typing import Any

from ..connection import SqliteConnection
from app.logger import get_logger

_log = get_logger("storage.agent_model_repo")


class AgentModelRepo:
    @staticmethod
    async def _ensure_table() -> None:
        db = await SqliteConnection.get_db()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_model_config (
                agent_name TEXT PRIMARY KEY,
                model TEXT,
                base_url TEXT,
                api_key TEXT,
                temperature REAL,
                max_tokens INTEGER,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.commit()

    @staticmethod
    async def get_config(agent_name: str) -> dict[str, Any] | None:
        """查单个 Agent 配置，返回 None 表示未配置。"""
        await AgentModelRepo._ensure_table()
        row = await SqliteConnection.fetchone(
            "SELECT * FROM agent_model_config WHERE agent_name=?", (agent_name,)
        )
        if not row:
            return None
        return dict(row)

    @staticmethod
    async def get_all_configs() -> list[dict[str, Any]]:
        """查所有 Agent 配置。"""
        await AgentModelRepo._ensure_table()
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM agent_model_config ORDER BY agent_name"
        )
        return [dict(r) for r in rows]

    @staticmethod
    async def save_config(
        agent_name: str,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        """保存/更新某个 Agent 的模型配置。"""
        await AgentModelRepo._ensure_table()
        await SqliteConnection.write_with_lock(
            "agent_model_config",
            """INSERT OR REPLACE INTO agent_model_config
               (agent_name, model, base_url, api_key, temperature, max_tokens, updated_at)
               VALUES (?,?,?,?,?,?, datetime('now'))""",
            (agent_name, model, base_url, api_key, temperature, max_tokens),
        )
        _log.info(f"保存 Agent 模型配置: {agent_name} model={model}")

    @staticmethod
    async def delete_config(agent_name: str) -> None:
        """删除某个 Agent 的配置（恢复默认）。"""
        await AgentModelRepo._ensure_table()
        await SqliteConnection.write_with_lock(
            "agent_model_config",
            "DELETE FROM agent_model_config WHERE agent_name=?",
            (agent_name,),
        )
        _log.info(f"重置 Agent 模型配置: {agent_name}")


agent_model_repo = AgentModelRepo()