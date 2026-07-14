"""渠道配置仓储。"""
from __future__ import annotations

from typing import Any

from ..connection import SqliteConnection


class ChannelRepo:
    @staticmethod
    async def list_all() -> list[dict[str, Any]]:
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM channel_configs WHERE deleted_at IS NULL ORDER BY id ASC"
        )
        return [dict(r) for r in rows]

    @staticmethod
    async def get_by_key(channel_key: str) -> dict[str, Any] | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM channel_configs WHERE channel_key=? AND deleted_at IS NULL",
            (channel_key,),
        )
        return dict(row) if row else None

    @staticmethod
    async def update(channel_key: str, **kwargs) -> None:
        now = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()
        kwargs["updated_at"] = now
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [channel_key]
        await SqliteConnection.write_with_lock(
            "channel_configs",
            f"UPDATE channel_configs SET {sets} WHERE channel_key=?",
            tuple(vals),
        )

    @staticmethod
    async def create(**kwargs) -> None:
        now = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        cols = ", ".join(kwargs.keys())
        phs = ", ".join("?" for _ in kwargs)
        await SqliteConnection.write_with_lock(
            "channel_configs",
            f"INSERT INTO channel_configs ({cols}) VALUES ({phs})",
            tuple(kwargs.values()),
        )

    @staticmethod
    async def delete(channel_key: str) -> None:
        await SqliteConnection.write_with_lock(
            "channel_configs",
            "UPDATE channel_configs SET deleted_at=datetime('now') WHERE channel_key=?",
            (channel_key,),
        )


channel_repo = ChannelRepo()