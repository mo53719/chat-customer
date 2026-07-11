"""商品数据访问层：商品 / 分类 / 订单明细 / 售后工单。"""
from __future__ import annotations

import json
from typing import Any

from app.logger import get_logger
from app.storage.sqlite.connection import SqliteConnection
from app.storage.sqlite.models import (
    ProductDTO, ProductCategoryDTO, OrderItemDTO, AfterSalesDTO,
)

_log = get_logger("storage.product_repo")


# ===================== 分类 =====================
async def create_category(name: str, parent_id: int | None = None, sort_order: int = 0) -> int:
    cur = await SqliteConnection.execute(
        "INSERT INTO product_categories (name, parent_id, sort_order) VALUES (?, ?, ?)",
        (name, parent_id, sort_order),
    )
    return cur.lastrowid or 0


async def list_categories() -> list[ProductCategoryDTO]:
    rows = await SqliteConnection.fetchall(
        "SELECT id, name, parent_id, sort_order FROM product_categories "
        "WHERE deleted_at IS NULL ORDER BY sort_order, id"
    )
    return [ProductCategoryDTO(**r) for r in rows]


# ===================== 商品 =====================
def _row_to_product(row: dict[str, Any]) -> ProductDTO:
    def _parse_json(v, default):
        if not v:
            return default
        try:
            return json.loads(v)
        except Exception:
            return default

    return ProductDTO(
        id=row.get("id"),
        sku=row.get("sku", ""),
        name=row.get("name", ""),
        category_id=row.get("category_id"),
        brand=row.get("brand"),
        model=row.get("model"),
        price=row.get("price", 0.0) or 0.0,
        original_price=row.get("original_price"),
        stock=row.get("stock", 0) or 0,
        sales_count=row.get("sales_count", 0) or 0,
        specs=_parse_json(row.get("specs"), {}),
        highlights=row.get("highlights"),
        description=row.get("description"),
        package_contents=row.get("package_contents"),
        warranty=row.get("warranty"),
        image_url=row.get("image_url"),
        tags=_parse_json(row.get("tags"), []),
        status=row.get("status", "on_sale"),
        category_name=row.get("category_name"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


async def create_product(p: ProductDTO) -> int:
    cur = await SqliteConnection.write_with_lock(
        "products",
        """
        INSERT INTO products (
            sku, name, category_id, brand, model,
            price, original_price, stock, sales_count,
            specs, highlights, description, package_contents, warranty,
            image_url, tags, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            p.sku, p.name, p.category_id, p.brand, p.model,
            p.price, p.original_price, p.stock, p.sales_count,
            json.dumps(p.specs or {}, ensure_ascii=False),
            p.highlights, p.description, p.package_contents, p.warranty,
            p.image_url,
            json.dumps(p.tags or [], ensure_ascii=False),
            p.status,
        ),
    )
    return cur.lastrowid or 0


async def get_product_by_sku(sku: str) -> ProductDTO | None:
    row = await SqliteConnection.fetchone(
        "SELECT * FROM products WHERE sku=? AND deleted_at IS NULL", (sku,)
    )
    return _row_to_product(row) if row else None


async def get_product_by_id(pid: int) -> ProductDTO | None:
    row = await SqliteConnection.fetchone(
        "SELECT * FROM products WHERE id=? AND deleted_at IS NULL", (pid,)
    )
    return _row_to_product(row) if row else None


async def search_products(
    keyword: str | None = None,
    category_id: int | None = None,
    brand: str | None = None,
    status: str | None = "on_sale",
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[ProductDTO]:
    """精确条件检索。售前 Agent 先用这个，匹配不到再走 RAG。"""
    sql = (
        "SELECT p.*, c.name AS category_name FROM products p "
        "LEFT JOIN product_categories c ON p.category_id = c.id "
        "WHERE p.deleted_at IS NULL"
    )
    params: list[Any] = []
    if keyword:
        sql += " AND (p.name LIKE ? OR p.brand LIKE ? OR p.model LIKE ? OR p.highlights LIKE ?)"
        kw = f"%{keyword}%"
        params += [kw, kw, kw, kw]
    if category_id is not None:
        sql += " AND p.category_id=?"
        params.append(category_id)
    if brand:
        sql += " AND p.brand=?"
        params.append(brand)
    if status:
        sql += " AND p.status=?"
        params.append(status)
    if min_price is not None:
        sql += " AND p.price>=?"
        params.append(min_price)
    if max_price is not None:
        sql += " AND p.price<=?"
        params.append(max_price)
    sql += " ORDER BY p.sales_count DESC, p.id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = await SqliteConnection.fetchall(sql, tuple(params))
    return [_row_to_product(r) for r in rows]


async def list_all_for_kb() -> list[ProductDTO]:
    """给知识库同步用的全量列表（包含 off_sale，只过滤已删除）。"""
    rows = await SqliteConnection.fetchall(
        "SELECT p.*, c.name AS category_name FROM products p "
        "LEFT JOIN product_categories c ON p.category_id = c.id "
        "WHERE p.deleted_at IS NULL"
    )
    return [_row_to_product(r) for r in rows]


async def update_product(pid: int, p: ProductDTO) -> None:
    await SqliteConnection.write_with_lock(
        "products",
        """
        UPDATE products SET
            sku=?, name=?, category_id=?, brand=?, model=?,
            price=?, original_price=?, stock=?, sales_count=?,
            specs=?, highlights=?, description=?, package_contents=?, warranty=?,
            image_url=?, tags=?, status=?
        WHERE id=?
        """,
        (
            p.sku, p.name, p.category_id, p.brand, p.model,
            p.price, p.original_price, p.stock, p.sales_count,
            json.dumps(p.specs or {}, ensure_ascii=False),
            p.highlights, p.description, p.package_contents, p.warranty,
            p.image_url,
            json.dumps(p.tags or [], ensure_ascii=False),
            p.status, pid,
        ),
    )
    _log.info(f"更新商品 pid={pid}")


async def soft_delete_product(pid: int) -> None:
    """软删除商品（标记 deleted_at）。"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    await SqliteConnection.write_with_lock(
        "products", "UPDATE products SET deleted_at=? WHERE id=?", (now, pid)
    )
    _log.info(f"软删除商品 pid={pid}")


async def update_product_stock(pid: int, delta: int) -> None:
    await SqliteConnection.write_with_lock(
        "products", "UPDATE products SET stock = stock + ? WHERE id=?", (delta, pid)
    )


# ===================== 订单明细 =====================
async def add_order_item(item: OrderItemDTO) -> int:
    cur = await SqliteConnection.write_with_lock(
        "order_items",
        """
        INSERT INTO order_items (
            order_id, product_id, product_name, product_sku,
            unit_price, quantity, subtotal
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.order_id, item.product_id, item.product_name, item.product_sku,
            item.unit_price, item.quantity, item.subtotal,
        ),
    )
    return cur.lastrowid or 0


async def list_order_items(order_id: int) -> list[OrderItemDTO]:
    rows = await SqliteConnection.fetchall(
        "SELECT * FROM order_items WHERE order_id=? AND deleted_at IS NULL",
        (order_id,),
    )
    return [OrderItemDTO(**r) for r in rows]


# ===================== 售后工单 =====================
async def create_after_sales(t: AfterSalesDTO) -> int:
    cur = await SqliteConnection.write_with_lock(
        "after_sales",
        """
        INSERT INTO after_sales (ticket_no, order_id, customer_id, type, reason, description, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (t.ticket_no, t.order_id, t.customer_id, t.type, t.reason, t.description, t.status),
    )
    return cur.lastrowid or 0


async def list_after_sales(customer_id: int | None = None, status: str | None = None,
                           limit: int = 20) -> list[AfterSalesDTO]:
    sql = "SELECT * FROM after_sales WHERE deleted_at IS NULL"
    params: list[Any] = []
    if customer_id is not None:
        sql += " AND customer_id=?"
        params.append(customer_id)
    if status:
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = await SqliteConnection.fetchall(sql, tuple(params))
    return [AfterSalesDTO(**r) for r in rows]
