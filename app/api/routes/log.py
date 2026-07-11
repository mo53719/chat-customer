"""日志上报路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.storage.sqlite.repositories.log_repo import log_repo
from ..schemas.common import ApiResponse
from ..deps import get_current_user

router = APIRouter(prefix="/api/logs", tags=["日志"])


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
