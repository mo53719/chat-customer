"""商家设置路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body

from app.storage.sqlite.repositories.merchant_config_repo import merchant_config_repo
from ..schemas.common import ApiResponse
from ..deps import require_admin

router = APIRouter(prefix="/api/merchant", tags=["商家设置"])


@router.get("", response_model=ApiResponse)
async def get_merchant_config(user: dict = Depends(require_admin)):
    cfg = await merchant_config_repo.get()
    return ApiResponse(data=cfg.to_dict())


@router.put("", response_model=ApiResponse)
async def save_merchant_config(
    shop_name: str | None = Body(None),
    shop_logo: str | None = Body(None),
    service_hours: str | None = Body(None),
    auto_reply: str | None = Body(None),
    auto_reply_enabled: int | None = Body(None),
    support_contact: str | None = Body(None),
    user: dict = Depends(require_admin),
):
    await merchant_config_repo.save(
        shop_name=shop_name, shop_logo=shop_logo,
        service_hours=service_hours, auto_reply=auto_reply,
        auto_reply_enabled=auto_reply_enabled,
        support_contact=support_contact,
    )
    return ApiResponse(message="已保存")