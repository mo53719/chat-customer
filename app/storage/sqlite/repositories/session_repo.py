"""会话与消息仓储。"""
from __future__ import annotations

from typing import Any

from ..connection import SqliteConnection, json_dumps, json_loads
from ..models import SessionDTO, MessageDTO


class SessionRepo:
    @staticmethod
    async def create(session_id: str, user_id: int | None = None,
                     customer_id: int | None = None, title: str | None = None,
                     channel: str = "web",
                     visitor_ip: str | None = None,
                     visitor_region: str | None = None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "sessions",
            """INSERT INTO sessions
               (session_id, user_id, customer_id, title, channel,
                visitor_ip, visitor_region, last_active_at)
               VALUES (?,?,?,?,?,?,?, datetime('now'))""",
            (session_id, user_id, customer_id, title, channel,
             visitor_ip, visitor_region),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def get(session_id: str) -> SessionDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM sessions WHERE session_id=? AND deleted_at IS NULL", (session_id,)
        )
        if not row:
            return None
        return _row_to_dto(row)

    @staticmethod
    async def list_by_user(user_id: int, keyword: str | None = None,
                           limit: int = 100) -> list[SessionDTO]:
        sql = "SELECT * FROM sessions WHERE user_id=? AND deleted_at IS NULL"
        params: list[Any] = [user_id]
        if keyword:
            sql += " AND (title LIKE ? OR intent_summary LIKE ? OR visitor_ip LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        sql += " ORDER BY COALESCE(last_active_at, created_at) DESC LIMIT ?"
        params.append(limit)
        rows = await SqliteConnection.fetchall(sql, tuple(params))
        return [_row_to_dto(r) for r in rows]

    @staticmethod
    async def list_recent(limit: int = 50) -> list[SessionDTO]:
        """访客工作台用：返回所有未删除会话，按最近活跃倒序。"""
        sql = ("SELECT * FROM sessions WHERE deleted_at IS NULL "
               "ORDER BY COALESCE(last_active_at, created_at) DESC LIMIT ?")
        rows = await SqliteConnection.fetchall(sql, (limit,))
        return [_row_to_dto(r) for r in rows]

    @staticmethod
    async def update_status(session_id: str, status: str,
                            transferred: bool = False) -> None:
        extra = ", transferred_to_human=1" if transferred else ""
        await SqliteConnection.write_with_lock(
            "sessions",
            f"UPDATE sessions SET status=?, closed_at=CASE WHEN ?='closed' THEN datetime('now') ELSE closed_at END{extra} WHERE session_id=?",
            (status, status, session_id),
        )

    @staticmethod
    async def incr_message_count(session_id: str) -> None:
        await SqliteConnection.write_with_lock(
            "sessions",
            "UPDATE sessions SET message_count=message_count+1 WHERE session_id=?",
            (session_id,),
        )

    @staticmethod
    async def update_activity(session_id: str, preview: str) -> None:
        """更新最近活跃时间与最后一条消息预览。"""
        await SqliteConnection.write_with_lock(
            "sessions",
            """UPDATE sessions
               SET last_active_at=datetime('now'),
                   last_message_preview=?,
                   message_count=COALESCE(message_count,0)+1
               WHERE session_id=?""",
            (preview[:200], session_id),
        )

    @staticmethod
    async def soft_delete(session_id: str, deleted_by: str | None = None) -> None:
        from .recycle_repo import recycle_repo
        row = await SqliteConnection.fetchone(
            "SELECT * FROM sessions WHERE session_id=?", (session_id,)
        )
        if row:
            await recycle_repo.snapshot("sessions", row["id"], dict(row), deleted_by)
        await SqliteConnection.write_with_lock(
            "sessions",
            "UPDATE sessions SET deleted_at=datetime('now') WHERE session_id=?",
            (session_id,),
        )


class MessageRepo:
    @staticmethod
    async def create(msg: MessageDTO) -> int:
        cur = await SqliteConnection.write_with_lock(
            "messages",
            """INSERT INTO messages
               (session_id, role, content, agent_name, intent, tool_calls,
                token_input, token_output, latency_ms, trace_id)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (msg.session_id, msg.role, msg.content, msg.agent_name, msg.intent,
             json_dumps(msg.tool_calls) if msg.tool_calls else None,
             msg.token_input, msg.token_output, msg.latency_ms, msg.trace_id),
        )
        msg_id = cur.lastrowid or 0
        # 同步刷新 session 的最近活跃 / 预览
        await SessionRepo.update_activity(msg.session_id, msg.content or "")
        return msg_id

    @staticmethod
    async def list_by_session(session_id: str, limit: int = 200) -> list[MessageDTO]:
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM messages WHERE session_id=? AND deleted_at IS NULL ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        )
        return [
            MessageDTO(
                id=r["id"], session_id=r["session_id"], role=r["role"],
                content=r["content"], agent_name=r["agent_name"], intent=r["intent"],
                tool_calls=json_loads(r["tool_calls"]),
                token_input=r["token_input"], token_output=r["token_output"],
                latency_ms=r["latency_ms"], trace_id=r["trace_id"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    @staticmethod
    async def get(message_id: int) -> MessageDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM messages WHERE id=? AND deleted_at IS NULL", (message_id,)
        )
        if not row:
            return None
        return MessageDTO(
            id=row["id"], session_id=row["session_id"], role=row["role"],
            content=row["content"], agent_name=row["agent_name"], intent=row["intent"],
            tool_calls=json_loads(row["tool_calls"]),
            token_input=row["token_input"], token_output=row["token_output"],
            latency_ms=row["latency_ms"], trace_id=row["trace_id"],
            created_at=row["created_at"],
        )


def _row_to_dto(r: dict) -> SessionDTO:
    s = SessionDTO(
        id=r["id"], session_id=r["session_id"], user_id=r["user_id"],
        customer_id=r["customer_id"], title=r["title"], status=r["status"],
        channel=r["channel"], intent_summary=r["intent_summary"],
        transferred_to_human=r["transferred_to_human"],
        message_count=r["message_count"], created_at=r["created_at"],
        closed_at=r["closed_at"],
        visitor_ip=r.get("visitor_ip"),
        visitor_region=r.get("visitor_region"),
        last_active_at=r.get("last_active_at"),
        last_message_preview=r.get("last_message_preview"),
    )
    # 访客名片（mock：从 IP 末段伪随机生成，后端未采集时填占位数据）
    _seed_mock_profile(s, r.get("id"), r.get("visitor_ip"))
    return s


def _seed_mock_profile(s: SessionDTO, row_id, ip: str | None) -> None:
    """填充访客名片字段（mock）。后续接入 UA 解析后可去掉。"""
    if not ip:
        s.device = "未知"
        s.browser = "未知"
        s.os_name = "未知"
        s.language = "zh-CN"
        s.referrer = "直接访问"
        s.visit_count = 1
        s.note = ""
        return
    # 用行号 / IP 末段做种子
    try:
        seed = (row_id or 0) + sum(int(x) for x in ip.split(".") if x.isdigit())
    except Exception:
        seed = (row_id or 0) or 1
    devices = ["iPhone 15 Pro", "iPhone 14", "MacBook Pro", "Desktop PC",
               "Xiaomi 14", "Huawei Mate 60", "Samsung S24", "iPad Air"]
    browsers = ["Chrome 124", "Edge 124", "Safari 17", "Firefox 126", "Chrome Mobile"]
    oses = ["iOS 17.4", "macOS 14.4", "Windows 11", "Android 14", "HarmonyOS 4"]
    refs = ["Google 搜索", "直接访问", "微信内分享", "微博", "百度搜索", "广告投放"]
    s.device = devices[seed % len(devices)]
    s.browser = browsers[seed % len(browsers)]
    s.os_name = oses[seed % len(oses)]
    s.language = "zh-CN" if seed % 3 != 0 else "en-US"
    s.referrer = refs[seed % len(refs)]
    s.visit_count = 1 + (seed % 9)
    s.note = ""


session_repo = SessionRepo()
message_repo = MessageRepo()
