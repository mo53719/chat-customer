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
    async def dashboard(days: int = 7) -> dict[str, Any]:
        """首页仪表盘聚合数据：今日指标 + 昨日对比 + 趋势 + 意图分布 + 最近会话。"""

        async def _today_val(query: str, key: str = "cnt") -> int:
            row = await SqliteConnection.fetchone(query)
            return row[key] if row else 0

        # ── 今日指标 ──
        today_sessions = await _today_val(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE date(created_at)=date('now')"
        )
        today_msgs = await _today_val(
            "SELECT COUNT(*) AS cnt FROM messages WHERE date(created_at)=date('now')"
        )
        avg_latency_row = await SqliteConnection.fetchone(
            "SELECT AVG(latency_ms) AS avg_ms FROM messages WHERE date(created_at)=date('now') AND role='assistant' AND latency_ms IS NOT NULL"
        )
        today_avg_latency = round(avg_latency_row["avg_ms"]) if avg_latency_row and avg_latency_row["avg_ms"] else 0

        fb_row = await SqliteConnection.fetchone(
            "SELECT COUNT(CASE WHEN rating='good' THEN 1 END) AS good, COUNT(*) AS total FROM feedback WHERE date(created_at)=date('now')"
        )
        today_satisfaction = round((fb_row["good"] / fb_row["total"] * 100), 1) if fb_row and fb_row["total"] else 0

        today_transfer = await _today_val(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE transferred_to_human=1 AND date(created_at)=date('now')"
        )
        today_bad = await _today_val(
            "SELECT COUNT(*) AS cnt FROM feedback WHERE rating='bad' AND date(created_at)=date('now')"
        )
        online_agents = await _today_val(
            "SELECT COUNT(*) AS cnt FROM users WHERE status='active' AND deleted_at IS NULL"
        )
        today_new_visitors = await _today_val(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE date(created_at)=date('now')"
        )
        active_chats = await _today_val(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE status='active' AND deleted_at IS NULL"
        )

        today = {
            "sessions": today_sessions,
            "messages": today_msgs,
            "avg_latency_ms": today_avg_latency,
            "satisfaction": today_satisfaction,
            "transfer_human": today_transfer,
            "bad_feedback": today_bad,
            "online_agents": online_agents,
            "new_visitors": today_new_visitors,
            "active_chats": active_chats,
        }

        # ── 昨日对比 ──
        yesterday_sessions = await _today_val(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE date(created_at)=date('now','-1 day')"
        )
        yesterday_msgs = await _today_val(
            "SELECT COUNT(*) AS cnt FROM messages WHERE date(created_at)=date('now','-1 day')"
        )
        yesterday_avg_latency_row = await SqliteConnection.fetchone(
            "SELECT AVG(latency_ms) AS avg_ms FROM messages WHERE date(created_at)=date('now','-1 day') AND role='assistant' AND latency_ms IS NOT NULL"
        )
        yesterday_avg_latency = round(yesterday_avg_latency_row["avg_ms"]) if yesterday_avg_latency_row and yesterday_avg_latency_row["avg_ms"] else 0

        yesterday_fb = await SqliteConnection.fetchone(
            "SELECT COUNT(CASE WHEN rating='good' THEN 1 END) AS good, COUNT(*) AS total FROM feedback WHERE date(created_at)=date('now','-1 day')"
        )
        yesterday_satisfaction = round((yesterday_fb["good"] / yesterday_fb["total"] * 100), 1) if yesterday_fb and yesterday_fb["total"] else 0

        yesterday_transfer = await _today_val(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE transferred_to_human=1 AND date(created_at)=date('now','-1 day')"
        )
        yesterday_bad = await _today_val(
            "SELECT COUNT(*) AS cnt FROM feedback WHERE rating='bad' AND date(created_at)=date('now','-1 day')"
        )
        yesterday_new_visitors = await _today_val(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE date(created_at)=date('now','-1 day')"
        )
        yesterday_active = await _today_val(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE status='active' AND date(created_at)=date('now','-1 day') AND deleted_at IS NULL"
        )

        yesterday = {
            "sessions": yesterday_sessions,
            "messages": yesterday_msgs,
            "avg_latency_ms": yesterday_avg_latency,
            "satisfaction": yesterday_satisfaction,
            "transfer_human": yesterday_transfer,
            "bad_feedback": yesterday_bad,
            "new_visitors": yesterday_new_visitors,
            "active_chats": yesterday_active,
        }

        # ── 每日趋势 ──
        daily_rows = await SqliteConnection.fetchall(
            """SELECT date(created_at) AS d,
                      COUNT(DISTINCT session_id) AS sessions,
                      COUNT(*) AS msgs
               FROM messages
               WHERE created_at >= datetime('now', ?)
               GROUP BY d ORDER BY d""",
            (f"-{days} days",),
        )

        # ── 意图分布（饼图） ──
        intents = await SqliteConnection.fetchall(
            """SELECT intent_summary AS name, COUNT(*) AS value
               FROM sessions
               WHERE intent_summary IS NOT NULL
                 AND created_at >= datetime('now', ?)
               GROUP BY intent_summary ORDER BY value DESC LIMIT 10""",
            (f"-{days} days",),
        )

        # ── 最近会话 ──
        recent_sessions = await SqliteConnection.fetchall(
            """SELECT s.session_id, s.title, s.channel, s.status, s.created_at,
                      s.visitor_region, s.last_message_preview, s.last_active_at
               FROM sessions s
               WHERE s.deleted_at IS NULL
               ORDER BY s.created_at DESC LIMIT 10"""
        )

        return {
            "today": today,
            "yesterday": yesterday,
            "daily": daily_rows,
            "intents": intents,
            "recent_sessions": recent_sessions,
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

    @staticmethod
    async def service_stats(days: int = 30) -> dict[str, Any]:
        """服务统计页：渠道分布、响应时间、客服工作量、满意度趋势。"""
        since = f"-{days} days"

        # 渠道来源分布
        channel_rows = await SqliteConnection.fetchall(
            """SELECT channel, COUNT(*) AS cnt
               FROM sessions
               WHERE created_at >= datetime('now', ?) AND deleted_at IS NULL
               GROUP BY channel ORDER BY cnt DESC""",
            (since,),
        )

        # 每日会话 + 消息趋势
        daily_rows = await SqliteConnection.fetchall(
            """SELECT date(created_at) AS d,
                      COUNT(DISTINCT session_id) AS sessions,
                      COUNT(*) AS msgs
               FROM messages
               WHERE created_at >= datetime('now', ?)
               GROUP BY d ORDER BY d""",
            (since,),
        )

        # 响应时间分布（按秒分桶）
        latency_rows = await SqliteConnection.fetchall(
            """SELECT
                 CASE
                   WHEN latency_ms < 1000 THEN '<1s'
                   WHEN latency_ms < 3000 THEN '1-3s'
                   WHEN latency_ms < 5000 THEN '3-5s'
                   WHEN latency_ms < 10000 THEN '5-10s'
                   ELSE '>10s'
                 END AS bucket,
                 COUNT(*) AS cnt
               FROM messages
               WHERE role='assistant' AND latency_ms IS NOT NULL
                 AND created_at >= datetime('now', ?)
               GROUP BY bucket ORDER BY MIN(latency_ms)""",
            (since,),
        )

        # 意图分布
        intent_rows = await SqliteConnection.fetchall(
            """SELECT intent_summary AS name, COUNT(*) AS value
               FROM sessions
               WHERE intent_summary IS NOT NULL
                 AND created_at >= datetime('now', ?)
               GROUP BY intent_summary ORDER BY value DESC LIMIT 10""",
            (since,),
        )

        # 客服工作量排行
        agent_rows = await SqliteConnection.fetchall(
            """SELECT COALESCE(u.username, m.agent_name, '系统') AS agent,
                      COUNT(DISTINCT m.session_id) AS sessions,
                      COUNT(*) AS msgs,
                      ROUND(AVG(m.latency_ms)) AS avg_latency_ms
               FROM messages m
               LEFT JOIN users u ON u.id = (SELECT user_id FROM sessions WHERE session_id=m.session_id LIMIT 1)
               WHERE m.role='assistant' AND m.created_at >= datetime('now', ?)
               GROUP BY agent ORDER BY msgs DESC LIMIT 10""",
            (since,),
        )

        return {
            "channels": [{"name": r["channel"], "value": r["cnt"]} for r in channel_rows],
            "daily": daily_rows,
            "latency_dist": [{"bucket": r["bucket"], "count": r["cnt"]} for r in latency_rows],
            "intents": intent_rows,
            "agents": agent_rows,
        }


stats_service = StatsService()
