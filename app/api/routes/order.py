"""订单/用户数据查询路由（外部系统对接）。"""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.storage.sqlite.repositories.order_repo import order_repo
from ..schemas.common import ApiResponse
from ..deps import get_current_user, get_api_key_user, require_admin

router = APIRouter(prefix="/api/orders", tags=["订单"])


@router.get("", response_model=ApiResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: str | None = Query(None),
    after_sales_status: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    rows, total = await order_repo.list_all(
        page=page, page_size=page_size,
        keyword=keyword, status=status,
        after_sales_status=after_sales_status,
    )
    return ApiResponse(data={
        "items": [r.__dict__ for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


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


@router.get("/export", response_class=StreamingResponse)
async def export_orders(
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    user: dict = Depends(require_admin),
):
    """导出订单为 Excel。"""
    rows, _ = await order_repo.list_all(
        page=1, page_size=10000, keyword=keyword, status=status,
    )
    try:
        import openpyxl
    except ImportError:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("openpyxl 未安装", status_code=500)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "订单列表"
    headers = ["订单号", "商品名称", "用户ID", "金额", "订单状态", "售后状态", "收货地址", "联系电话", "下单时间"]
    ws.append(headers)
    status_map = {"pending": "待付款", "paid": "已付款", "shipped": "已发货", "delivered": "已签收"}
    as_map = {"pending": "待处理", "processing": "处理中", "completed": "已完成"}
    for r in rows:
        ws.append([
            r.order_no, r.product_name, r.user_id or "-", r.amount,
            status_map.get(r.status, r.status),
            as_map.get(r.after_sales_status, r.after_sales_status or "-"),
            r.address or "-", r.phone or "-", r.created_at,
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=orders_export.xlsx"},
    )
