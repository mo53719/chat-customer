"""失败案例仓储：reviewer 检测到不合格回答时自动入库。"""
from __future__ import annotations

import json
from typing import Any

from ..connection import SqliteConnection
from ..models import BadcaseDTO
from app.logger import get_logger

_log = get_logger("storage.badcase_repo")


class BadcaseRepo:
    @staticmethod
    async def _ensure_table() -> None:
        db = await SqliteConnection.get_db()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS badcases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                user_input TEXT NOT NULL,
                agent_answer TEXT,
                intent TEXT,
                agent_name TEXT,
                failed_rules TEXT,
                review_details TEXT,
                trace_id TEXT,
                status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'fixed', 'ignored')),
                note TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                reviewed_at TEXT,
                reviewed_by TEXT
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_badcases_status ON badcases(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_badcases_session ON badcases(session_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_badcases_created ON badcases(created_at DESC)")
        await db.commit()

    @staticmethod
    async def create(
        session_id: str | None,
        user_input: str,
        agent_answer: str | None,
        intent: str | None,
        agent_name: str | None,
        failed_rules: list[str] | None,
        review_details: list[dict] | None,
        trace_id: str | None,
    ) -> int:
        await BadcaseRepo._ensure_table()
        cur = await SqliteConnection.write_with_lock(
            "badcases",
            """INSERT INTO badcases
               (session_id, user_input, agent_answer, intent, agent_name,
                failed_rules, review_details, trace_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                session_id, user_input, agent_answer, intent, agent_name,
                json.dumps(failed_rules, ensure_ascii=False) if failed_rules else None,
                json.dumps(review_details, ensure_ascii=False) if review_details else None,
                trace_id,
            ),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def list_by_status(
        status: str = "new", limit: int = 50, offset: int = 0,
    ) -> list[BadcaseDTO]:
        await BadcaseRepo._ensure_table()
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM badcases WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        )
        return [_row_to_dto(r) for r in rows]

    @staticmethod
    async def search(
        keyword: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BadcaseDTO]:
        await BadcaseRepo._ensure_table()
        sql = "SELECT * FROM badcases WHERE 1=1"
        params: list[Any] = []
        if status:
            sql += " AND status=?"
            params.append(status)
        if keyword:
            sql += " AND (user_input LIKE ? OR agent_answer LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw])
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = await SqliteConnection.fetchall(sql, tuple(params))
        return [_row_to_dto(r) for r in rows]

    @staticmethod
    async def mark(
        badcase_id: int, status: str, note: str | None = None,
        reviewed_by: str | None = None,
    ) -> None:
        await BadcaseRepo._ensure_table()
        await SqliteConnection.write_with_lock(
            "badcases",
            """UPDATE badcases SET status=?, note=?, reviewed_at=datetime('now'),
               reviewed_by=? WHERE id=?""",
            (status, note, reviewed_by, badcase_id),
        )

    @staticmethod
    async def get(badcase_id: int) -> BadcaseDTO | None:
        await BadcaseRepo._ensure_table()
        row = await SqliteConnection.fetchone(
            "SELECT * FROM badcases WHERE id=?", (badcase_id,)
        )
        return _row_to_dto(row) if row else None


def _row_to_dto(row: dict[str, Any]) -> BadcaseDTO:
    return BadcaseDTO(
        id=row.get("id"),
        session_id=row.get("session_id"),
        user_input=row.get("user_input", ""),
        agent_answer=row.get("agent_answer"),
        intent=row.get("intent"),
        agent_name=row.get("agent_name"),
        failed_rules=_json_loads(row.get("failed_rules")),
        review_details=_json_loads(row.get("review_details")),
        trace_id=row.get("trace_id"),
        status=row.get("status", "new"),
        note=row.get("note"),
        created_at=row.get("created_at"),
        reviewed_at=row.get("reviewed_at"),
        reviewed_by=row.get("reviewed_by"),
    )


def _json_loads(s: str | None) -> Any:
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


badcase_repo = BadcaseRepo()