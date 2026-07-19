"""系统通用设置仓储。"""
from __future__ import annotations

from ..connection import SqliteConnection
from ..models import SystemConfigDTO


class SystemConfigRepo:
    """系统通用设置仓储，单例模式（只有一条配置记录）。"""

    @staticmethod
    async def get() -> SystemConfigDTO:
        """获取系统配置。"""
        row = await SqliteConnection.fetchone(
            "SELECT * FROM system_config WHERE id=1"
        )
        if not row:
            return SystemConfigDTO()
        return SystemConfigDTO(**{k: row[k] for k in SystemConfigDTO.__annotations__ if k in row})

    @staticmethod
    async def save(system_name: str | None = None,
                   login_timeout: int | None = None,
                   log_retention_days: int | None = None,
                   message_push_enabled: int | None = None,
                   data_backup_enabled: int | None = None,
                   data_backup_time: str | None = None) -> None:
        """保存系统配置（upsert）。"""
        sets: list[str] = []
        params: list = []
        if system_name is not None:
            sets.append("system_name=?")
            params.append(system_name)
        if login_timeout is not None:
            sets.append("login_timeout=?")
            params.append(login_timeout)
        if log_retention_days is not None:
            sets.append("log_retention_days=?")
            params.append(log_retention_days)
        if message_push_enabled is not None:
            sets.append("message_push_enabled=?")
            params.append(message_push_enabled)
        if data_backup_enabled is not None:
            sets.append("data_backup_enabled=?")
            params.append(data_backup_enabled)
        if data_backup_time is not None:
            sets.append("data_backup_time=?")
            params.append(data_backup_time)

        sets.append("updated_at=datetime('now')")

        existing = await SqliteConnection.fetchone("SELECT id FROM system_config WHERE id=1")
        if existing:
            await SqliteConnection.write_with_lock(
                "system_config",
                f"UPDATE system_config SET {', '.join(sets)} WHERE id=1",
                tuple(params),
            )
        else:
            cols = [s.replace("=?", "") for s in sets if s != "updated_at=datetime('now')"]
            placeholders = ", ".join(["?" for _ in cols])
            await SqliteConnection.write_with_lock(
                "system_config",
                f"INSERT INTO system_config ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(params),
            )


system_config_repo = SystemConfigRepo()