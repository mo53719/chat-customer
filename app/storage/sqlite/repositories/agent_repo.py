"""客服人员仓储。"""
from __future__ import annotations

from typing import Any

from ..connection import SqliteConnection
from ..models import AgentDTO


class AgentRepo:
    """客服人员仓储，提供客服的增删改查操作。"""

    @staticmethod
    async def list_all(department: str | None = None,
                       status: str | None = None,
                       keyword: str | None = None) -> list[AgentDTO]:
        """列出所有客服，支持按部门、状态、关键词筛选。"""
        sql = "SELECT * FROM agents WHERE 1=1"
        params: list[Any] = []
        if department:
            sql += " AND department=?"
            params.append(department)
        if status:
            sql += " AND status=?"
            params.append(status)
        if keyword:
            sql += " AND (name LIKE ? OR account LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw])
        sql += " ORDER BY id ASC"
        rows = await SqliteConnection.fetchall(sql, tuple(params) if params else None)
        return [AgentDTO(**{k: r[k] for k in AgentDTO.__annotations__ if k in r}) for r in rows]

    @staticmethod
    async def get_by_id(agent_id: int) -> AgentDTO | None:
        """按 ID 获取客服。"""
        row = await SqliteConnection.fetchone(
            "SELECT * FROM agents WHERE id=?", (agent_id,)
        )
        if not row:
            return None
        return AgentDTO(**{k: row[k] for k in AgentDTO.__annotations__ if k in row})

    @staticmethod
    async def create(name: str, account: str, department: str = "",
                     status: str = "offline", max_sessions: int = 5,
                     channel: str = "", role: str = "agent") -> int:
        """创建客服。"""
        cur = await SqliteConnection.write_with_lock(
            "agents",
            """INSERT INTO agents (name, account, department, status, max_sessions, channel, role)
               VALUES (?,?,?,?,?,?,?)""",
            (name, account, department, status, max_sessions, channel, role),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def update(agent_id: int, name: str | None = None,
                     department: str | None = None, status: str | None = None,
                     max_sessions: int | None = None, channel: str | None = None,
                     role: str | None = None) -> int:
        """更新客服信息，只更新传入的字段。"""
        sets: list[str] = []
        params: list[Any] = []
        if name is not None:
            sets.append("name=?")
            params.append(name)
        if department is not None:
            sets.append("department=?")
            params.append(department)
        if status is not None:
            sets.append("status=?")
            params.append(status)
        if max_sessions is not None:
            sets.append("max_sessions=?")
            params.append(max_sessions)
        if channel is not None:
            sets.append("channel=?")
            params.append(channel)
        if role is not None:
            sets.append("role=?")
            params.append(role)
        if not sets:
            return 0
        sets.append("updated_at=datetime('now')")
        params.append(agent_id)
        cur = await SqliteConnection.write_with_lock(
            "agents",
            f"UPDATE agents SET {', '.join(sets)} WHERE id=?",
            tuple(params),
        )
        return cur.rowcount

    @staticmethod
    async def update_status(agent_id: int, status: str) -> int:
        """快速切换在线状态。"""
        cur = await SqliteConnection.write_with_lock(
            "agents",
            "UPDATE agents SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, agent_id),
        )
        return cur.rowcount

    @staticmethod
    async def delete(agent_id: int) -> int:
        """删除客服。"""
        cur = await SqliteConnection.write_with_lock(
            "agents",
            "DELETE FROM agents WHERE id=?",
            (agent_id,),
        )
        return cur.rowcount


agent_repo = AgentRepo()