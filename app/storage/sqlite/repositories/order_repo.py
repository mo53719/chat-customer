"""订单仓储。"""
from __future__ import annotations

from typing import Any

from ..connection import SqliteConnection
from ..models import OrderDTO


class OrderRepo:
    """订单仓储，提供订单的增删改查操作。"""
    @staticmethod
    async def create(order_no: str, customer_id: int | None = None,
                     product_name: str | None = None, amount: float | None = None,
                     status: str = "pending", address: str | None = None,
                     phone: str | None = None) -> int:
        """创建一条新订单。"""
        cur = await SqliteConnection.write_with_lock(
            "orders",
            """INSERT INTO orders (order_no, customer_id, product_name, amount, status, address, phone)
               VALUES (?,?,?,?,?,?,?)""",
            (order_no, customer_id, product_name, amount, status, address, phone),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def get_by_no(order_no: str) -> OrderDTO | None:
        """按订单号查询订单。"""
        row = await SqliteConnection.fetchone(
            "SELECT * FROM orders WHERE order_no=? AND deleted_at IS NULL", (order_no,)
        )
        if not row:
            return None
        return OrderDTO(**{k: row[k] for k in OrderDTO.__annotations__ if k in row})

    @staticmethod
    async def get_by_customer(customer_id: int, limit: int = 50) -> list[OrderDTO]:
        """按客户 ID 查询订单列表。"""
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM orders WHERE customer_id=? AND deleted_at IS NULL ORDER BY id DESC LIMIT ?",
            (customer_id, limit),
        )
        return [OrderDTO(**{k: r[k] for k in OrderDTO.__annotations__ if k in r}) for r in rows]

    @staticmethod
    async def update_address(order_no: str, address: str, phone: str | None = None) -> int:
        """更新订单收货地址。"""
        cur = await SqliteConnection.write_with_lock(
            "orders",
            "UPDATE orders SET address=?, phone=? WHERE order_no=?",
            (address, phone, order_no),
        )
        return cur.rowcount

    @staticmethod
    async def update_status(order_no: str, status: str) -> int:
        """更新订单状态。"""
        cur = await SqliteConnection.write_with_lock(
            "orders",
            "UPDATE orders SET status=? WHERE order_no=?",
            (status, order_no),
        )
        return cur.rowcount

    @staticmethod
    async def search(keyword: str | None = None, status: str | None = None,
                     limit: int = 50) -> list[OrderDTO]:
        """按关键字和状态搜索订单列表。"""
        sql = "SELECT * FROM orders WHERE deleted_at IS NULL"
        params: list[Any] = []
        if keyword:
            sql += " AND (order_no LIKE ? OR product_name LIKE ? OR phone LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = await SqliteConnection.fetchall(sql, tuple(params))
        return [OrderDTO(**{k: r[k] for k in OrderDTO.__annotations__ if k in r}) for r in rows]

    @staticmethod
    async def list_all(page: int = 1, page_size: int = 20,
                       keyword: str | None = None,
                       status: str | None = None,
                       after_sales_status: str | None = None) -> tuple[list[OrderDTO], int]:
        """分页列出所有订单，支持多条件筛选。返回 (列表, 总数)。"""
        where = "WHERE deleted_at IS NULL"
        params: list[Any] = []
        if keyword:
            where += " AND (order_no LIKE ? OR product_name LIKE ? OR phone LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        if status:
            where += " AND status=?"
            params.append(status)
        if after_sales_status:
            where += " AND after_sales_status=?"
            params.append(after_sales_status)

        # 总数
        count_sql = f"SELECT COUNT(*) as cnt FROM orders {where}"
        count_row = await SqliteConnection.fetchone(count_sql, tuple(params) if params else None)
        total = count_row["cnt"] if count_row else 0

        # 分页数据
        offset = (page - 1) * page_size
        data_sql = f"SELECT * FROM orders {where} ORDER BY id DESC LIMIT ? OFFSET ?"
        rows = await SqliteConnection.fetchall(
            data_sql, tuple(params + [page_size, offset])
        )
        return [OrderDTO(**{k: r[k] for k in OrderDTO.__annotations__ if k in r}) for r in rows], total

    @staticmethod
    async def soft_delete(order_id: int, deleted_by: str | None = None) -> None:
        """软删除订单，删除前快照到回收站。"""
        from .recycle_repo import recycle_repo
        row = await SqliteConnection.fetchone(
            "SELECT * FROM orders WHERE id=?", (order_id,)
        )
        if row:
            await recycle_repo.snapshot("orders", order_id, dict(row), deleted_by)
        await SqliteConnection.write_with_lock(
            "orders",
            "UPDATE orders SET deleted_at=datetime('now') WHERE id=?",
            (order_id,),
        )


order_repo = OrderRepo()
