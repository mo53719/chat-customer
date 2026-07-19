"""日志上报与查询路由。"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from config.settings import settings
from app.storage.sqlite.repositories.log_repo import log_repo
from ..schemas.common import ApiResponse
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/logs", tags=["日志"])

# 日志行格式：时间 | 级别 | trace_id | 模块:函数:行号 - 消息
LOG_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| "
    r"(\w+)\s+\| "
    r"(\S+) \| "
    r"(.+?) - "
    r"(.+)$"
)


def _parse_log_line(line: str) -> dict | None:
    m = LOG_PATTERN.match(line.strip())
    if not m:
        return None
    return {
        "time": m.group(1),
        "level": m.group(2).strip(),
        "trace_id": m.group(3),
        "location": m.group(4),
        "message": m.group(5),
    }


async def _read_log_files(
    level: str | None = None,
    module: str | None = None,
    keyword: str | None = None,
    trace_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    log_dir = Path(settings.log_abs_dir)
    if not log_dir.exists():
        return []

    results: list[dict] = []
    log_files = sorted(log_dir.glob("app_*.log"), reverse=True)

    for log_file in log_files:
        if len(results) >= limit:
            break
        try:
            content = await asyncio.to_thread(log_file.read_text, encoding="utf-8")
            for line in reversed(content.strip().split("\n")):
                if len(results) >= limit:
                    break
                parsed = _parse_log_line(line)
                if not parsed:
                    continue
                if level and parsed["level"].upper() != level.upper():
                    continue
                if module and module not in parsed["location"]:
                    continue
                if keyword and keyword not in parsed["message"]:
                    continue
                if trace_id and parsed["trace_id"] != trace_id:
                    continue
                results.append(parsed)
        except Exception:
            continue

    return results


class PageOpRequest(BaseModel):
    page: str
    action: str
    payload: dict | None = None
    session_id: str | None = None


@router.post("/page-op", response_model=ApiResponse)
async def page_op(req: PageOpRequest, user: dict = Depends(get_current_user)):
    await log_repo.insert_page_op(user["user_id"], req.page, req.action,
                                   req.payload, req.session_id)
    return ApiResponse(message="已记录")


@router.get("/run-logs", response_model=ApiResponse)
async def list_run_logs(level: str | None = None, limit: int = 100,
                        user: dict = Depends(get_current_user)):
    from app.storage.sqlite.connection import SqliteConnection
    sql = "SELECT * FROM run_logs WHERE 1=1"
    params: list = []
    if level:
        sql += " AND level=?"
        params.append(level)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = await SqliteConnection.fetchall(sql, tuple(params))
    return ApiResponse(data=rows)


@router.get("/search")
async def search_log_files(
    level: str | None = Query(None, description="日志级别: INFO/WARNING/ERROR/DEBUG"),
    module: str | None = Query(None, description="模块名，如 agents.presales"),
    keyword: str | None = Query(None, description="消息内容模糊匹配"),
    trace_id: str | None = Query(None, description="关联某次请求的 trace_id"),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    results = await _read_log_files(
        level=level, module=module, keyword=keyword,
        trace_id=trace_id, limit=limit,
    )
    return {"data": results, "total": len(results)}


@router.get("/page-ops", response_model=ApiResponse)
async def list_page_ops(
    page: str | None = Query(None),
    action: str | None = Query(None),
    user_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    user: dict = Depends(require_admin),
):
    """查询页面操作日志。"""
    from app.storage.sqlite.connection import SqliteConnection
    sql = "SELECT * FROM page_operation_logs WHERE 1=1"
    params: list = []
    if page:
        sql += " AND page LIKE ?"
        params.append(f"%{page}%")
    if action:
        sql += " AND action=?"
        params.append(action)
    if user_id:
        sql += " AND user_id=?"
        params.append(user_id)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = await SqliteConnection.fetchall(sql, tuple(params))
    return ApiResponse(data=rows)
