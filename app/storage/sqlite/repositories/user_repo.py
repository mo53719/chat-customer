"""用户仓储：账号 + API Key。"""
from __future__ import annotations

from typing import Any

from ..connection import SqliteConnection, json_dumps
from ..models import UserDTO


class UserRepo:
    @staticmethod
    async def create(username: str, password_hash: str, role: str = "user",
                     nickname: str | None = None, email: str | None = None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "users",
            "INSERT INTO users (username, password_hash, role, nickname, email) VALUES (?,?,?,?,?)",
            (username, password_hash, role, nickname, email),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def get_by_username(username: str) -> UserDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM users WHERE username=? AND deleted_at IS NULL", (username,)
        )
        if not row:
            return None
        return UserDTO(
            id=row["id"], username=row["username"], role=row["role"],
            nickname=row["nickname"], email=row["email"], status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    async def get_by_id(user_id: int) -> UserDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM users WHERE id=? AND deleted_at IS NULL", (user_id,)
        )
        if not row:
            return None
        return UserDTO(
            id=row["id"], username=row["username"], role=row["role"],
            nickname=row["nickname"], email=row["email"], status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    async def list_all() -> list[UserDTO]:
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM users WHERE deleted_at IS NULL ORDER BY id DESC"
        )
        return [
            UserDTO(id=r["id"], username=r["username"], role=r["role"],
                    nickname=r["nickname"], email=r["email"], status=r["status"],
                    created_at=r["created_at"])
            for r in rows
        ]

    @staticmethod
    async def soft_delete(user_id: int, deleted_by: str | None = None) -> None:
        from .recycle_repo import recycle_repo
        row = await SqliteConnection.fetchone(
            "SELECT * FROM users WHERE id=?", (user_id,)
        )
        if row:
            await recycle_repo.snapshot("users", user_id, dict(row), deleted_by)
        await SqliteConnection.write_with_lock(
            "users",
            "UPDATE users SET deleted_at=datetime('now'), status='disabled' WHERE id=?",
            (user_id,),
        )


class ApiKeyRepo:
    @staticmethod
    async def create(key_value: str, name: str | None = None, user_id: int | None = None,
                     rate_limit: int = 60) -> int:
        cur = await SqliteConnection.write_with_lock(
            "api_keys",
            "INSERT INTO api_keys (key_value, name, user_id, rate_limit_per_minute) VALUES (?,?,?,?)",
            (key_value, name, user_id, rate_limit),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def get_by_key(key_value: str) -> dict[str, Any] | None:
        return await SqliteConnection.fetchone(
            "SELECT * FROM api_keys WHERE key_value=? AND status='active' AND deleted_at IS NULL",
            (key_value,),
        )

    @staticmethod
    async def touch_last_used(key_value: str) -> None:
        await SqliteConnection.write_with_lock(
            "api_keys",
            "UPDATE api_keys SET last_used_at=datetime('now') WHERE key_value=?",
            (key_value,),
        )

    @staticmethod
    async def list_all() -> list[dict[str, Any]]:
        return await SqliteConnection.fetchall(
            "SELECT * FROM api_keys WHERE deleted_at IS NULL ORDER BY id DESC"
        )


user_repo = UserRepo()
api_key_repo = ApiKeyRepo()
