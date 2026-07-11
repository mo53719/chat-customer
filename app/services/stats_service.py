"""统计服务：聚合 SQLite 数据供可视化看板。"""
from __future__ import annotations

from typing import Any

from app.storage.sqlite.connection import SqliteConnection


class StatsService:
    @staticmethod
    async def overview(days: int = 7) -> dict[str, Any]:
        """看板总览：接待量 / 转人工 / 投诉 / 反馈。"""
        rows = await SqliteConnection.fetchall(
            """SELECT date(created_at) AS d,
                      COUNT(DISTINCT session_id) AS sessions,
                      COUNT(*) AS msgs
               FROM messages
               WHERE created_at >= datetime('now', ?)
               GROUP BY d ORDER BY d""",
            (f"-{days} days",),
        )
        transfer = await SqliteConnection.fetchone(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE transferred_to_human=1 AND created_at >= datetime('now', ?)",
            (f"-{days} days",),
        )
        good = await SqliteConnection.fetchone(
            "SELECT COUNT(*) AS cnt FROM feedback WHERE rating='good' AND created_at >= datetime('now', ?)",
            (f"-{days} days",),
        )
        bad = await SqliteConnection.fetchone(
            "SELECT COUNT(*) AS cnt FROM feedback WHERE rating='bad' AND created_at >= datetime('now', ?)",
            (f"-{days} days",),
        )
        return {
            "daily": rows,
            "transfer_human": transfer["cnt"] if transfer else 0,
            "good_feedback": good["cnt"] if good else 0,
            "bad_feedback": bad["cnt"] if bad else 0,
        }

    @staticmethod
    async def top_intents(days: int = 7, limit: int = 10) -> list[dict[str, Any]]:
        return await SqliteConnection.fetchall(
            """SELECT intent_summary AS intent, COUNT(*) AS cnt
               FROM sessions
               WHERE intent_summary IS NOT NULL
                 AND created_at >= datetime('now', ?)
               GROUP BY intent_summary ORDER BY cnt DESC LIMIT ?""",
            (f"-{days} days", limit),
        )

    @staticmethod
    async def daily_sessions(days: int = 30) -> list[dict[str, Any]]:
        return await SqliteConnection.fetchall(
            """SELECT date(created_at) AS d, COUNT(*) AS cnt
               FROM sessions
               WHERE created_at >= datetime('now', ?)
               GROUP BY d ORDER BY d""",
            (f"-{days} days",),
        )


stats_service = StatsService()
