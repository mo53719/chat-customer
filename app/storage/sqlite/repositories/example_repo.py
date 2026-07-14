"""优质 / 差评示例库仓储。"""
from __future__ import annotations

from ..connection import SqliteConnection
from ..models import ExampleDTO


class ExampleRepo:
    """优质/差评示例库仓储，提供示例的增删查操作。"""
    @staticmethod
    async def create(agent_name: str | None, question: str, answer: str,
                     tag: str, source_feedback_id: int | None = None) -> int:
        """创建一条示例记录。"""
        cur = await SqliteConnection.write_with_lock(
            "examples",
            """INSERT INTO examples (agent_name, question, answer, tag, source_feedback_id)
               VALUES (?,?,?,?,?)""",
            (agent_name, question, answer, tag, source_feedback_id),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def list_by_agent(agent_name: str, tag: str | None = None,
                            limit: int = 20) -> list[ExampleDTO]:
        """按 Agent 名称列出示例，可按 tag 筛选。"""
        sql = "SELECT * FROM examples WHERE agent_name=? AND deleted_at IS NULL"
        params: list = [agent_name]
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = await SqliteConnection.fetchall(sql, tuple(params))
        return [
            ExampleDTO(**{k: r[k] for k in ExampleDTO.__annotations__ if k in r})
            for r in rows
        ]

    @staticmethod
    async def list_all(limit: int = 100, tag: str | None = None) -> list[ExampleDTO]:
        """列出所有示例，可按 tag 筛选。"""
        sql = "SELECT * FROM examples WHERE deleted_at IS NULL"
        params: list = []
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = await SqliteConnection.fetchall(sql, tuple(params))
        return [
            ExampleDTO(**{k: r[k] for k in ExampleDTO.__annotations__ if k in r})
            for r in rows
        ]

    @staticmethod
    async def soft_delete(example_id: int, deleted_by: str | None = None) -> None:
        """软删除示例，删除前快照到回收站。"""
        from .recycle_repo import recycle_repo
        row = await SqliteConnection.fetchone(
            "SELECT * FROM examples WHERE id=?", (example_id,)
        )
        if row:
            await recycle_repo.snapshot("examples", example_id, dict(row), deleted_by)
        await SqliteConnection.write_with_lock(
            "examples",
            "UPDATE examples SET deleted_at=datetime('now') WHERE id=?",
            (example_id,),
        )


example_repo = ExampleRepo()
