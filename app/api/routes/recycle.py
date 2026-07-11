"""回收站路由：一键回溯。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.storage.sqlite.repositories.recycle_repo import recycle_repo
from ..schemas.common import ApiResponse
from ..deps import require_admin

router = APIRouter(prefix="/api/recycle", tags=["回收站"])


@router.get("", response_model=ApiResponse)
async def list_deleted(table_name: str | None = Query(None),
                       limit: int = Query(100, ge=1, le=500),
                       user: dict = Depends(require_admin)):
    rows = await recycle_repo.list_deleted(table_name, limit)
    return ApiResponse(data=rows)


@router.get("/{deleted_id}", response_model=ApiResponse)
async def get_snapshot(deleted_id: int, user: dict = Depends(require_admin)):
    row = await recycle_repo.get_snapshot(deleted_id)
    if not row:
        raise HTTPException(404, "记录不存在")
    return ApiResponse(data=row)


@router.post("/{deleted_id}/restore", response_model=ApiResponse)
async def restore(deleted_id: int, user: dict = Depends(require_admin)):
    try:
        result = await recycle_repo.restore(deleted_id)
        return ApiResponse(data=result, message="已恢复")
    except ValueError as e:
        raise HTTPException(400, str(e))
