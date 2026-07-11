"""订单/用户数据查询路由（外部系统对接）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.storage.sqlite.repositories.order_repo import order_repo
from ..schemas.common import ApiResponse
from ..deps import get_current_user, get_api_key_user

router = APIRouter(prefix="/api/orders", tags=["订单"])


@router.get("", response_model=ApiResponse)
async def search_orders(keyword: str | None = Query(None),
                        status: str | None = Query(None),
                        user: dict = Depends(get_current_user)):
    rows = await order_repo.search(keyword=keyword, status=status)
    return ApiResponse(data=[r.__dict__ for r in rows])


@router.get("/{order_no}", response_model=ApiResponse)
async def get_order(order_no: str, user: dict = Depends(get_current_user)):
    o = await order_repo.get_by_no(order_no)
    if not o:
        return ApiResponse(success=False, message="订单不存在")
    return ApiResponse(data=o.__dict__)


@router.get("/external/{order_no}", response_model=ApiResponse)
async def get_order_external(order_no: str,
                             key_user: dict = Depends(get_api_key_user)):
    """对外接口（API Key 鉴权）。"""
    o = await order_repo.get_by_no(order_no)
    if not o:
        return ApiResponse(success=False, message="订单不存在")
    return ApiResponse(data=o.__dict__)
