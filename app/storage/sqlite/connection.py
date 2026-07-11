"""SQLite 异步连接管理 + 全局写锁（按表维度，防并发写错乱）。"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from config.settings import settings
from app.logger import get_logger

_log = get_logger("storage.sqlite")

# 全局写锁池：按表名获取锁，避免多人并发写同一表导致数据错乱
_table_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


async def _get_table_lock(table: str) -> asyncio.Lock:
    async with _locks_guard:
        if table not in _table_locks:
            _table_locks[table] = asyncio.Lock()
        return _table_locks[table]


class SqliteConnection:
    """SQLite 连接管理器（aiosqlite 单连接 + WAL）。"""

    _db: aiosqlite.Connection | None = None
    _init_lock = asyncio.Lock()

    @classmethod
    async def get_db(cls) -> aiosqlite.Connection:
        if cls._db is None:
            async with cls._init_lock:
                if cls._db is None:
                    p: Path = settings.sqlite_abs_path
                    _log.info(f"打开 SQLite: {p}")
                    cls._db = await aiosqlite.connect(str(p))
                    cls._db.row_factory = aiosqlite.Row
                    await cls._db.execute("PRAGMA journal_mode = WAL;")
                    await cls._db.execute("PRAGMA foreign_keys = ON;")
                    await cls._db.execute("PRAGMA busy_timeout = 5000;")
                    await cls._db.commit()
        return cls._db

    @classmethod
    async def close(cls) -> None:
        if cls._db is not None:
            await cls._db.close()
            cls._db = None

    @classmethod
    @asynccontextmanager
    async def transaction(cls) -> AsyncIterator[aiosqlite.Connection]:
        db = await cls.get_db()
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def execute(
        cls, sql: str, params: tuple[Any, ...] | list[Any] | None = None
    ) -> aiosqlite.Cursor:
        db = await cls.get_db()
        cur = await db.execute(sql, params or ())
        await db.commit()
        return cur

    @classmethod
    async def executemany(
        cls, sql: str, params_seq: list[tuple[Any, ...]]
    ) -> aiosqlite.Cursor:
        db = await cls.get_db()
        cur = await db.executemany(sql, params_seq)
        await db.commit()
        return cur

    @classmethod
    async def fetchone(
        cls, sql: str, params: tuple[Any, ...] | list[Any] | None = None
    ) -> dict[str, Any] | None:
        db = await cls.get_db()
        cur = await db.execute(sql, params or ())
        row = await cur.fetchone()
        return dict(row) if row else None

    @classmethod
    async def fetchall(
        cls, sql: str, params: tuple[Any, ...] | list[Any] | None = None
    ) -> list[dict[str, Any]]:
        db = await cls.get_db()
        cur = await db.execute(sql, params or ())
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    @classmethod
    async def write_with_lock(
        cls,
        table: str,
        sql: str,
        params: tuple[Any, ...] | list[Any] | None = None,
    ) -> Any:
        """带表级写锁的写操作，防止并发写错乱。"""
        lock = await _get_table_lock(table)
        async with lock:
            return await cls.execute(sql, params)


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def json_loads(s: str | None) -> Any:
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None
