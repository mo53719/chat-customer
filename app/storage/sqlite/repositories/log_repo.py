"""日志仓储：run_logs / tool_call_logs / api_call_logs / token_usage / page_operation_logs。"""
from __future__ import annotations

from typing import Any

from ..connection import SqliteConnection, json_dumps


class LogRepo:
    @staticmethod
    async def insert_run_log(level: str, message: str, trace_id: str | None = None,
                             module: str | None = None,
                             extra: dict[str, Any] | None = None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "run_logs",
            "INSERT INTO run_logs (level, message, module, trace_id, extra) VALUES (?,?,?,?,?)",
            (level, message, module, trace_id, json_dumps(extra) if extra else None),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def insert_tool_call(trace_id: str | None, session_id: str | None,
                               tool_name: str, agent_name: str | None,
                               input_data: Any, output_data: Any,
                               success: bool, error: str | None,
                               latency_ms: int | None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "tool_call_logs",
            """INSERT INTO tool_call_logs
               (trace_id, session_id, tool_name, agent_name, input, output, success, error, latency_ms)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (trace_id, session_id, tool_name, agent_name,
             json_dumps(input_data) if input_data else None,
             json_dumps(output_data) if output_data else None,
             1 if success else 0, error, latency_ms),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def insert_api_call(api_key: str | None, endpoint: str, method: str,
                              status_code: int, latency_ms: int,
                              ip: str | None, trace_id: str | None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "api_call_logs",
            """INSERT INTO api_call_logs
               (api_key, endpoint, method, status_code, latency_ms, ip, trace_id)
               VALUES (?,?,?,?,?,?,?)""",
            (api_key, endpoint, method, status_code, latency_ms, ip, trace_id),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def insert_token_usage(trace_id: str | None, session_id: str | None,
                                 agent_name: str | None, model: str,
                                 prompt_tokens: int, completion_tokens: int) -> int:
        total = prompt_tokens + completion_tokens
        cur = await SqliteConnection.write_with_lock(
            "token_usage",
            """INSERT INTO token_usage
               (trace_id, session_id, agent_name, model, prompt_tokens, completion_tokens, total_tokens)
               VALUES (?,?,?,?,?,?,?)""",
            (trace_id, session_id, agent_name, model,
             prompt_tokens, completion_tokens, total),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def insert_page_op(user_id: int | None, page: str, action: str,
                             payload: Any = None, session_id: str | None = None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "page_operation_logs",
            "INSERT INTO page_operation_logs (user_id, page, action, payload, session_id) VALUES (?,?,?,?,?)",
            (user_id, page, action, json_dumps(payload) if payload else None, session_id),
        )
        return cur.lastrowid or 0

    # ------------------- 查询（运维面板用） -------------------
    @staticmethod
    async def tool_call_stats(days: int = 7) -> list[dict[str, Any]]:
        return await SqliteConnection.fetchall(
            """SELECT tool_name,
                      COUNT(*) AS total,
                      SUM(success) AS success_cnt,
                      AVG(latency_ms) AS avg_latency,
                      COUNT(CASE WHEN success=0 THEN 1 END) AS fail_cnt
               FROM tool_call_logs
               WHERE created_at >= datetime('now', ?)
               GROUP BY tool_name ORDER BY total DESC""",
            (f"-{days} days",),
        )

    @staticmethod
    async def token_usage_stats(days: int = 7) -> list[dict[str, Any]]:
        return await SqliteConnection.fetchall(
            """SELECT date(created_at) AS stat_date,
                      agent_name, model,
                      SUM(prompt_tokens) AS prompt_t,
                      SUM(completion_tokens) AS completion_t,
                      SUM(total_tokens) AS total_t
               FROM token_usage
               WHERE created_at >= datetime('now', ?)
               GROUP BY stat_date, agent_name, model
               ORDER BY stat_date DESC""",
            (f"-{days} days",),
        )

    @staticmethod
    async def top_errors(days: int = 7, limit: int = 20) -> list[dict[str, Any]]:
        return await SqliteConnection.fetchall(
            """SELECT module, level, message, COUNT(*) AS cnt
               FROM run_logs
               WHERE level IN ('ERROR','WARNING')
                 AND created_at >= datetime('now', ?)
               GROUP BY module, level, message
               ORDER BY cnt DESC LIMIT ?""",
            (f"-{days} days", limit),
        )

    @staticmethod
    async def task_latency_stats(days: int = 7) -> list[dict[str, Any]]:
        return await SqliteConnection.fetchall(
            """SELECT date(created_at) AS stat_date,
                      COUNT(*) AS task_cnt,
                      AVG(latency_ms) AS avg_latency,
                      MAX(latency_ms) AS max_latency
               FROM messages
               WHERE role='assistant' AND latency_ms IS NOT NULL
                 AND created_at >= datetime('now', ?)
               GROUP BY stat_date ORDER BY stat_date DESC""",
            (f"-{days} days",),
        )


log_repo = LogRepo()
