"""初始化 SQLite：执行 001 + 002 等所有 migration 建表 / 扩展字段。"""
from __future__ import annotations

import asyncio
from pathlib import Path

from app.storage.sqlite.connection import SqliteConnection
from app.logger import setup_logging, get_logger

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "storage" / "sqlite" / "migrations"


async def main() -> None:
    setup_logging()
    log = get_logger("init_db")
    db = await SqliteConnection.get_db()

    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        log.info(f"执行 migration: {sql_file.name}")
        sql = sql_file.read_text(encoding="utf-8")
        # executescript 兼容多条 ALTER / CREATE
        await db.executescript(sql)
        await db.commit()
    log.info("建表完成")

    # 创建默认管理员
    from app.security.auth import hash_password
    from app.storage.sqlite.repositories.user_repo import user_repo
    existing = await user_repo.get_by_username("admin")
    if not existing:
        await user_repo.create("admin", hash_password("admin123"), role="admin",
                                nickname="管理员")
        log.info("已创建默认管理员 admin / admin123")
    await SqliteConnection.close()


if __name__ == "__main__":
    asyncio.run(main())
