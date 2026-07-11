"""提示词版本仓储：永久保存所有版本，支持启用切换。"""
from __future__ import annotations

from ..connection import SqliteConnection
from ..models import PromptVersionDTO


class PromptRepo:
    @staticmethod
    async def create_version(agent_name: str, content: str, change_note: str | None = None,
                             created_by: str | None = None,
                             auto_generated: int = 0,
                             source_feedback_id: int | None = None) -> int:
        """创建新版本，自动累加 version_no，并把同 agent 旧版本置为 inactive。"""
        row = await SqliteConnection.fetchone(
            "SELECT MAX(version_no) AS max_v FROM prompt_versions WHERE agent_name=?",
            (agent_name,),
        )
        next_v = (row["max_v"] or 0) + 1 if row else 1

        async with SqliteConnection.transaction() as db:
            await db.execute(
                "UPDATE prompt_versions SET is_active=0 WHERE agent_name=?",
                (agent_name,),
            )
            cur = await db.execute(
                """INSERT INTO prompt_versions
                   (agent_name, version_no, content, change_note, is_active,
                    auto_generated, source_feedback_id, created_by)
                   VALUES (?,?,?,?,1,?,?,?)""",
                (agent_name, next_v, content, change_note,
                 auto_generated, source_feedback_id, created_by),
            )
            await db.commit()
            return cur.lastrowid or 0

    @staticmethod
    async def get_active(agent_name: str) -> PromptVersionDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM prompt_versions WHERE agent_name=? AND is_active=1 AND deleted_at IS NULL",
            (agent_name,),
        )
        if not row:
            return None
        return PromptVersionDTO(**{k: row[k] for k in PromptVersionDTO.__annotations__ if k in row})

    @staticmethod
    async def get_by_id(version_id: int) -> PromptVersionDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM prompt_versions WHERE id=? AND deleted_at IS NULL", (version_id,)
        )
        if not row:
            return None
        return PromptVersionDTO(**{k: row[k] for k in PromptVersionDTO.__annotations__ if k in row})

    @staticmethod
    async def list_versions(agent_name: str) -> list[PromptVersionDTO]:
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM prompt_versions WHERE agent_name=? AND deleted_at IS NULL ORDER BY version_no DESC",
            (agent_name,),
        )
        return [
            PromptVersionDTO(**{k: r[k] for k in PromptVersionDTO.__annotations__ if k in r})
            for r in rows
        ]

    @staticmethod
    async def list_all_agents() -> list[str]:
        rows = await SqliteConnection.fetchall(
            "SELECT DISTINCT agent_name FROM prompt_versions WHERE deleted_at IS NULL"
        )
        return [r["agent_name"] for r in rows]

    @staticmethod
    async def activate(version_id: int) -> None:
        row = await SqliteConnection.fetchone(
            "SELECT agent_name FROM prompt_versions WHERE id=?", (version_id,)
        )
        if not row:
            return
        agent_name = row["agent_name"]
        async with SqliteConnection.transaction() as db:
            await db.execute(
                "UPDATE prompt_versions SET is_active=0 WHERE agent_name=?", (agent_name,)
            )
            await db.execute(
                "UPDATE prompt_versions SET is_active=1 WHERE id=?", (version_id,)
            )
            await db.commit()

    @staticmethod
    async def soft_delete(version_id: int, deleted_by: str | None = None) -> None:
        from .recycle_repo import recycle_repo
        row = await SqliteConnection.fetchone(
            "SELECT * FROM prompt_versions WHERE id=?", (version_id,)
        )
        if row:
            await recycle_repo.snapshot("prompt_versions", version_id, dict(row), deleted_by)
        await SqliteConnection.write_with_lock(
            "prompt_versions",
            "UPDATE prompt_versions SET deleted_at=datetime('now'), is_active=0 WHERE id=?",
            (version_id,),
        )


prompt_repo = PromptRepo()
