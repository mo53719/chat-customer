"""会话管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.storage.sqlite.repositories.session_repo import session_repo, message_repo
from ..schemas.common import ApiResponse
from ..deps import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["会话"])


@router.get("", response_model=ApiResponse)
async def list_sessions(keyword: str | None = Query(None),
                        user: dict = Depends(get_current_user)):
    rows = await session_repo.list_by_user(user["user_id"], keyword=keyword)
    return ApiResponse(data=[r.__dict__ for r in rows])


@router.get("/visitors", response_model=ApiResponse)
async def list_visitors(
    keyword: str | None = Query(None),
    channel: str | None = Query(None),
    status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """访客管理页：分页列表 + 筛选 + 搜索。"""
    offset = (page - 1) * page_size
    rows, total = await session_repo.list_visitors(
        keyword=keyword, channel=channel, status=status,
        date_from=date_from, date_to=date_to,
        offset=offset, limit=page_size,
    )
    return ApiResponse(data={
        "items": [r.__dict__ for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/recent", response_model=ApiResponse)
async def list_recent(limit: int = 50, user: dict = Depends(get_current_user)):
    """对话工作台用：返回全部最近访客会话（按 last_active_at 倒序）。"""
    rows = await session_repo.list_recent(limit=limit)
    return ApiResponse(data=[r.__dict__ for r in rows])


@router.get("/{session_id}/messages", response_model=ApiResponse)
async def list_messages(session_id: str, user: dict = Depends(get_current_user)):
    msgs = await message_repo.list_by_session(session_id)
    return ApiResponse(data=[m.__dict__ for m in msgs])


@router.post("/{session_id}/close", response_model=ApiResponse)
async def close_session(session_id: str, user: dict = Depends(get_current_user)):
    await session_repo.update_status(session_id, "closed")
    return ApiResponse(message="会话已关闭")


@router.post("/{session_id}/transfer", response_model=ApiResponse)
async def transfer_human(session_id: str, user: dict = Depends(get_current_user)):
    await session_repo.update_status(session_id, "transferred", transferred=True)
    return ApiResponse(message="已转人工")
