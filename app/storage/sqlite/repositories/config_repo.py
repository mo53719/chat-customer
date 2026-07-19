"""配置项仓储。"""
from __future__ import annotations

import json
from typing import Any

from ..connection import SqliteConnection
from ..models import ConfigItemDTO, ConfigChangeLogDTO


class ConfigRepo:
    """配置项仓储，提供配置项的增删改查和变更日志。"""

    @staticmethod
    async def list_all(config_type: str | None = None,
                       keyword: str | None = None) -> list[ConfigItemDTO]:
        """列出所有配置项，支持按类型和名称筛选。"""
        sql = "SELECT * FROM config_items WHERE 1=1"
        params: list[Any] = []
        if config_type:
            sql += " AND config_type=?"
            params.append(config_type)
        if keyword:
            sql += " AND name LIKE ?"
            params.append(f"%{keyword}%")
        sql += " ORDER BY id ASC"
        rows = await SqliteConnection.fetchall(sql, tuple(params) if params else None)
        return [ConfigItemDTO(**{k: r[k] for k in ConfigItemDTO.__annotations__ if k in r}) for r in rows]

    @staticmethod
    async def get_by_id(config_id: int) -> ConfigItemDTO | None:
        """按 ID 获取配置项。"""
        row = await SqliteConnection.fetchone(
            "SELECT * FROM config_items WHERE id=?", (config_id,)
        )
        if not row:
            return None
        return ConfigItemDTO(**{k: row[k] for k in ConfigItemDTO.__annotations__ if k in row})

    @staticmethod
    async def create(name: str, config_type: str, config_value: str,
                     description: str = "", updated_by: str | None = None) -> int:
        """创建配置项。"""
        cur = await SqliteConnection.write_with_lock(
            "config_items",
            """INSERT INTO config_items (name, config_type, config_value, description, updated_by)
               VALUES (?,?,?,?,?)""",
            (name, config_type, config_value, description, updated_by),
        )
        config_id = cur.lastrowid or 0
        # 记录变更日志
        if config_id and updated_by:
            await ConfigRepo._log_change(config_id, "create", None, config_value, updated_by)
        return config_id

    @staticmethod
    async def update(config_id: int, name: str | None = None,
                     config_type: str | None = None, config_value: str | None = None,
                     description: str | None = None, is_enabled: int | None = None,
                     updated_by: str | None = None) -> int:
        """更新配置项，只更新传入的字段。"""
        old = await ConfigRepo.get_by_id(config_id)
        if not old:
            return 0

        sets: list[str] = []
        params: list[Any] = []
        changes: list[tuple[str, str | None, str | None]] = []

        if name is not None:
            sets.append("name=?")
            params.append(name)
            changes.append(("name", old.name, name))
        if config_type is not None:
            sets.append("config_type=?")
            params.append(config_type)
            changes.append(("config_type", old.config_type, config_type))
        if config_value is not None:
            sets.append("config_value=?")
            params.append(config_value)
            changes.append(("config_value", old.config_value, config_value))
        if description is not None:
            sets.append("description=?")
            params.append(description)
            changes.append(("description", old.description, description))
        if is_enabled is not None:
            sets.append("is_enabled=?")
            params.append(is_enabled)
            changes.append(("is_enabled", str(old.is_enabled), str(is_enabled)))

        if not sets:
            return 0

        sets.append("updated_at=datetime('now')")
        if updated_by:
            sets.append("updated_by=?")
            params.append(updated_by)

        params.append(config_id)
        cur = await SqliteConnection.write_with_lock(
            "config_items",
            f"UPDATE config_items SET {', '.join(sets)} WHERE id=?",
            tuple(params),
        )

        # 记录变更日志
        if updated_by:
            for field_name, old_val, new_val in changes:
                await ConfigRepo._log_change(config_id, field_name, old_val, new_val, updated_by)

        return cur.rowcount

    @staticmethod
    async def delete(config_id: int) -> int:
        """删除配置项。"""
        cur = await SqliteConnection.write_with_lock(
            "config_items",
            "DELETE FROM config_items WHERE id=?",
            (config_id,),
        )
        return cur.rowcount

    @staticmethod
    async def get_change_logs(config_id: int, limit: int = 5) -> list[ConfigChangeLogDTO]:
        """获取配置项的最近 N 次变更记录。"""
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM config_change_logs WHERE config_id=? ORDER BY id DESC LIMIT ?",
            (config_id, limit),
        )
        return [ConfigChangeLogDTO(**{k: r[k] for k in ConfigChangeLogDTO.__annotations__ if k in r}) for r in rows]

    @staticmethod
    async def _log_change(config_id: int, field_name: str,
                          old_value: str | None, new_value: str | None,
                          changed_by: str) -> None:
        """记录变更日志。"""
        await SqliteConnection.write_with_lock(
            "config_change_logs",
            """INSERT INTO config_change_logs (config_id, field_name, old_value, new_value, changed_by)
               VALUES (?,?,?,?,?)""",
            (config_id, field_name, old_value, new_value, changed_by),
        )


config_repo = ConfigRepo()