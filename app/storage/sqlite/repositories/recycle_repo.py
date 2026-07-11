"""回收站：软删快照 + 一键回溯恢复。"""
from __future__ import annotations

import json
from typing import Any

from ..connection import SqliteConnection


class RecycleRepo:
    """所有软删操作走此模块：保存删除前快照，便于一键恢复。"""

    # 允许回溯的表及其主键字段
    RESTORABLE_TABLES: dict[str, str] = {
        "users": "id",
        "orders": "id",
        "sessions": "id",
        "messages": "id",
        "prompt_versions": "id",
        "feedback": "id",
        "feedback_analysis": "id",
        "examples": "id",
        "knowledge_meta": "id",
    }

    @staticmethod
    async def snapshot(table_name: str, record_id: int, record: dict[str, Any],
                       deleted_by: str | None = None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "deleted_records",
            """INSERT INTO deleted_records (table_name, record_id, snapshot, deleted_by)
               VALUES (?,?,?,?)""",
            (table_name, record_id, json.dumps(record, ensure_ascii=False, default=str), deleted_by),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def list_deleted(table_name: str | None = None,
                           limit: int = 100) -> list[dict[str, Any]]:
        sql = "SELECT * FROM deleted_records WHERE restored_at IS NULL"
        params: list[Any] = []
        if table_name:
            sql += " AND table_name=?"
            params.append(table_name)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = await SqliteConnection.fetchall(sql, tuple(params))
        return rows

    @staticmethod
    async def restore(deleted_id: int) -> dict[str, Any]:
        """一键恢复：把快照写回原表，清除 deleted_at。"""
        row = await SqliteConnection.fetchone(
            "SELECT * FROM deleted_records WHERE id=?", (deleted_id,)
        )
        if not row:
            raise ValueError(f"回收站记录 {deleted_id} 不存在")
        if row["restored_at"]:
            raise ValueError(f"记录 {deleted_id} 已恢复过")

        table = row["table_name"]
        record_id = row["record_id"]
        snapshot: dict[str, Any] = json.loads(row["snapshot"])

        if table not in RecycleRepo.RESTORABLE_TABLES:
            raise ValueError(f"表 {table} 不支持回溯")

        # 列名收集（去掉 deleted_at）
        cols = [k for k in snapshot.keys() if k != "deleted_at"]
        col_list = ", ".join(cols)
        placeholder_list = ", ".join(["?"] * len(cols))
        values = [snapshot[c] for c in cols]

        async with SqliteConnection.transaction() as db:
            pk = RecycleRepo.RESTORABLE_TABLES[table]
            existing = await db.execute(
                f"SELECT {pk} FROM {table} WHERE {pk}=?", (record_id,)
            )
            existing_row = await existing.fetchone()
            if existing_row:
                await db.execute(
                    f"UPDATE {table} SET {col_list}, deleted_at=NULL WHERE {pk}=?",
                    (*values, record_id),
                )
            else:
                await db.execute(
                    f"INSERT INTO {table} ({pk}, {col_list}) VALUES (?, {placeholder_list})",
                    (record_id, *values),
                )
            await db.execute(
                "UPDATE deleted_records SET restored_at=datetime('now') WHERE id=?",
                (deleted_id,),
            )
            await db.commit()

        return {"restored": True, "table": table, "record_id": record_id}

    @staticmethod
    async def get_snapshot(deleted_id: int) -> dict[str, Any] | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM deleted_records WHERE id=?", (deleted_id,)
        )
        return dict(row) if row else None


recycle_repo = RecycleRepo()
