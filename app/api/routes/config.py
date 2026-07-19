"""配置列表路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Body

from app.storage.sqlite.repositories.config_repo import config_repo
from ..schemas.common import ApiResponse
from ..deps import require_admin

router = APIRouter(prefix="/api/config", tags=["配置列表"])


@router.get("", response_model=ApiResponse)
async def list_configs(
    config_type: str | None = Query(None, description="配置类型筛选"),
    keyword: str | None = Query(None, description="名称关键词"),
    user: dict = Depends(require_admin),
):
    rows = await config_repo.list_all(config_type=config_type, keyword=keyword)
    return ApiResponse(data=[r.to_dict() for r in rows])


@router.get("/{config_id}", response_model=ApiResponse)
async def get_config(config_id: int, user: dict = Depends(require_admin)):
    c = await config_repo.get_by_id(config_id)
    if not c:
        return ApiResponse(success=False, message="配置项不存在")
    return ApiResponse(data=c.to_dict())


@router.post("", response_model=ApiResponse)
async def create_config(
    name: str = Body(...),
    config_type: str = Body(...),
    config_value: str = Body("{}"),
    description: str = Body(""),
    user: dict = Depends(require_admin),
):
    cid = await config_repo.create(
        name=name, config_type=config_type,
        config_value=config_value, description=description,
        updated_by=user.get("username", ""),
    )
    return ApiResponse(data={"id": cid})


@router.put("/{config_id}", response_model=ApiResponse)
async def update_config(
    config_id: int,
    name: str | None = Body(None),
    config_type: str | None = Body(None),
    config_value: str | None = Body(None),
    description: str | None = Body(None),
    is_enabled: int | None = Body(None),
    user: dict = Depends(require_admin),
):
    n = await config_repo.update(
        config_id=config_id, name=name, config_type=config_type,
        config_value=config_value, description=description,
        is_enabled=is_enabled, updated_by=user.get("username", ""),
    )
    if n == 0:
        return ApiResponse(success=False, message="配置项不存在或无变更")
    return ApiResponse(message="已更新")


@router.delete("/{config_id}", response_model=ApiResponse)
async def delete_config(config_id: int, user: dict = Depends(require_admin)):
    n = await config_repo.delete(config_id)
    if n == 0:
        return ApiResponse(success=False, message="配置项不存在")
    return ApiResponse(message="已删除")


@router.get("/{config_id}/logs", response_model=ApiResponse)
async def get_change_logs(
    config_id: int,
    limit: int = Query(5, le=50),
    user: dict = Depends(require_admin),
):
    logs = await config_repo.get_change_logs(config_id, limit=limit)
    return ApiResponse(data=[l.__dict__ for l in logs])