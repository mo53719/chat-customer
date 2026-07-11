"""订单工具：查询 / 修改地址 / 催发货 / 催退款。"""
from __future__ import annotations

from .registry import register_tool, ToolResult
from app.storage.sqlite.repositories.order_repo import order_repo


@register_tool(
    name="query_order",
    description="根据订单号或手机号查询订单详情",
    parameters={
        "type": "object",
        "properties": {
            "order_no": {"type": "string", "description": "订单号"},
            "phone": {"type": "string", "description": "收货手机号"},
        },
    },
)
async def query_order(state, order_no: str | None = None,
                      phone: str | None = None) -> ToolResult:
    if order_no:
        o = await order_repo.get_by_no(order_no)
        if not o:
            return ToolResult(success=False, error="订单不存在")
        return ToolResult(data=o.__dict__)
    if phone:
        rows = await order_repo.search(keyword=phone, limit=10)
        return ToolResult(data=[r.__dict__ for r in rows])
    return ToolResult(success=False, error="需提供 order_no 或 phone")


@register_tool(
    name="update_order_address",
    description="修改订单收货地址（需用户二次确认）",
    parameters={
        "type": "object",
        "properties": {
            "order_no": {"type": "string"},
            "address": {"type": "string"},
            "phone": {"type": "string"},
        },
        "required": ["order_no", "address"],
    },
)
async def update_order_address(state, order_no: str, address: str,
                               phone: str | None = None) -> ToolResult:
    n = await order_repo.update_address(order_no, address, phone)
    return ToolResult(success=n > 0, data={"updated": n})


@register_tool(
    name="urge_shipment",
    description="催发货，标记订单为催办状态",
    parameters={"type": "object", "properties": {"order_no": {"type": "string"}}, "required": ["order_no"]},
)
async def urge_shipment(state, order_no: str) -> ToolResult:
    n = await order_repo.update_status(order_no, "pending")
    return ToolResult(success=n > 0, data={"urged": n, "eta": "24小时内发货"})


@register_tool(
    name="urge_refund",
    description="催退款，标记订单为退款处理中",
    parameters={"type": "object", "properties": {"order_no": {"type": "string"}}, "required": ["order_no"]},
)
async def urge_refund(state, order_no: str) -> ToolResult:
    n = await order_repo.update_status(order_no, "refunded")
    return ToolResult(success=n > 0, data={"urged": n, "eta": "1-3个工作日到账"})
