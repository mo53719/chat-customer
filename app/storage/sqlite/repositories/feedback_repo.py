"""反馈与原因分析仓储。"""
from __future__ import annotations

from typing import Any

from ..connection import SqliteConnection
from ..models import FeedbackDTO, FeedbackAnalysisDTO


class FeedbackRepo:
    @staticmethod
    async def create(message_id: int | None, session_id: str | None,
                     user_id: int | None, rating: str, comment: str | None,
                     question: str | None, answer: str | None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "feedback",
            """INSERT INTO feedback
               (message_id, session_id, user_id, rating, comment, question, answer)
               VALUES (?,?,?,?,?,?,?)""",
            (message_id, session_id, user_id, rating, comment, question, answer),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def get(feedback_id: int) -> FeedbackDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM feedback WHERE id=? AND deleted_at IS NULL", (feedback_id,)
        )
        if not row:
            return None
        return FeedbackDTO(**{k: row[k] for k in FeedbackDTO.__annotations__ if k in row})

    @staticmethod
    async def list_all(limit: int = 100, rating: str | None = None) -> list[FeedbackDTO]:
        sql = "SELECT * FROM feedback WHERE deleted_at IS NULL"
        params: list[Any] = []
        if rating:
            sql += " AND rating=?"
            params.append(rating)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = await SqliteConnection.fetchall(sql, tuple(params))
        return [
            FeedbackDTO(**{k: r[k] for k in FeedbackDTO.__annotations__ if k in r})
            for r in rows
        ]

    @staticmethod
    async def list_by_session(session_id: str) -> list[FeedbackDTO]:
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM feedback WHERE session_id=? AND deleted_at IS NULL ORDER BY id DESC",
            (session_id,),
        )
        return [
            FeedbackDTO(**{k: r[k] for k in FeedbackDTO.__annotations__ if k in r})
            for r in rows
        ]

    @staticmethod
    async def soft_delete(feedback_id: int, deleted_by: str | None = None) -> None:
        from .recycle_repo import recycle_repo
        row = await SqliteConnection.fetchone(
            "SELECT * FROM feedback WHERE id=?", (feedback_id,)
        )
        if row:
            await recycle_repo.snapshot("feedback", feedback_id, dict(row), deleted_by)
        await SqliteConnection.write_with_lock(
            "feedback",
            "UPDATE feedback SET deleted_at=datetime('now') WHERE id=?",
            (feedback_id,),
        )


class FeedbackAnalysisRepo:
    @staticmethod
    async def create(feedback_id: int, category: str | None, reason: str | None,
                     suggestion: str | None,
                     optimized_prompt_version_id: int | None = None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "feedback_analysis",
            """INSERT INTO feedback_analysis
               (feedback_id, category, reason, suggestion, optimized_prompt_version_id)
               VALUES (?,?,?,?,?)""",
            (feedback_id, category, reason, suggestion, optimized_prompt_version_id),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def get_by_feedback(feedback_id: int) -> FeedbackAnalysisDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM feedback_analysis WHERE feedback_id=? AND deleted_at IS NULL",
            (feedback_id,),
        )
        if not row:
            return None
        return FeedbackAnalysisDTO(
            **{k: row[k] for k in FeedbackAnalysisDTO.__annotations__ if k in row}
        )

    @staticmethod
    async def list_all(limit: int = 100) -> list[FeedbackAnalysisDTO]:
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM feedback_analysis WHERE deleted_at IS NULL ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [
            FeedbackAnalysisDTO(
                **{k: r[k] for k in FeedbackAnalysisDTO.__annotations__ if k in r}
            )
            for r in rows
        ]


feedback_repo = FeedbackRepo()
feedback_analysis_repo = FeedbackAnalysisRepo()
