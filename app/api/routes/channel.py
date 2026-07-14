"""渠道管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.storage.sqlite.repositories.channel_repo import channel_repo
from ..schemas.common import ApiResponse
from ..deps import get_current_user

router = APIRouter(prefix="/api/channels", tags=["渠道"])


class ChannelUpdate(BaseModel):
    channel_name: str | None = None
    icon: str | None = None
    enabled: int | None = None
    api_key: str | None = None
    api_secret: str | None = None
    webhook_url: str | None = None
    auto_reply: str | None = None
    remark: str | None = None
    config_json: str | None = None


@router.get("", response_model=ApiResponse)
async def list_channels(user: dict = Depends(get_current_user)):
    rows = await channel_repo.list_all()
    return ApiResponse(data=rows)


@router.put("/{channel_key}", response_model=ApiResponse)
async def update_channel(channel_key: str, body: ChannelUpdate,
                         user: dict = Depends(get_current_user)):
    data = body.model_dump(exclude_none=True)
    if not data:
        return ApiResponse(message="无更新内容")
    await channel_repo.update(channel_key, **data)
    return ApiResponse(message="更新成功")


@router.post("/{channel_key}/toggle", response_model=ApiResponse)
async def toggle_channel(channel_key: str, user: dict = Depends(get_current_user)):
    row = await channel_repo.get_by_key(channel_key)
    if not row:
        return ApiResponse(success=False, message="渠道不存在")
    new_enabled = 0 if row["enabled"] else 1
    await channel_repo.update(channel_key, enabled=new_enabled)
    return ApiResponse(data={"enabled": new_enabled}, message="状态已切换")