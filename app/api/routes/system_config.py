"""系统通用设置路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body

from app.storage.sqlite.repositories.system_config_repo import system_config_repo
from ..schemas.common import ApiResponse
from ..deps import require_admin

router = APIRouter(prefix="/api/system-config", tags=["通用设置"])


@router.get("", response_model=ApiResponse)
async def get_system_config(user: dict = Depends(require_admin)):
    cfg = await system_config_repo.get()
    return ApiResponse(data=cfg.to_dict())


@router.put("", response_model=ApiResponse)
async def save_system_config(
    system_name: str | None = Body(None),
    login_timeout: int | None = Body(None),
    log_retention_days: int | None = Body(None),
    message_push_enabled: int | None = Body(None),
    data_backup_enabled: int | None = Body(None),
    data_backup_time: str | None = Body(None),
    user: dict = Depends(require_admin),
):
    await system_config_repo.save(
        system_name=system_name, login_timeout=login_timeout,
        log_retention_days=log_retention_days,
        message_push_enabled=message_push_enabled,
        data_backup_enabled=data_backup_enabled,
        data_backup_time=data_backup_time,
    )
    return ApiResponse(message="已保存")