"""商品 / 分类 / 售后工单 路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.storage.sqlite import product_repo
from app.storage.sqlite.models import ProductDTO, ProductCategoryDTO, OrderItemDTO, AfterSalesDTO
from ..schemas.common import ApiResponse
from ..deps import get_current_user

router = APIRouter(prefix="/api/products", tags=["商品"])


# ==================== 分类 ====================
@router.get("/categories", response_model=ApiResponse)
async def list_categories(user: dict = Depends(get_current_user)):
    rows = await product_repo.list_categories()
    return ApiResponse(data=[c.__dict__ for c in rows])


@router.post("/categories", response_model=ApiResponse)
async def create_category(name: str,
                          parent_id: int | None = None,
                          sort_order: int = 0,
                          user: dict = Depends(get_current_user)):
    cid = await product_repo.create_category(name, parent_id, sort_order)
    return ApiResponse(data={"id": cid})


# ==================== 商品 ====================
@router.get("", response_model=ApiResponse)
async def search_products(
    keyword: str | None = Query(None, description="关键词（名称/品牌/型号/卖点）"),
    category_id: int | None = Query(None),
    brand: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    user: dict = Depends(get_current_user),
):
    rows = await product_repo.search_products(
        keyword=keyword, category_id=category_id, brand=brand,
        min_price=min_price, max_price=max_price,
        limit=limit, offset=offset,
    )
    return ApiResponse(data=[p.to_dict() for p in rows])


@router.get("/by-sku/{sku}", response_model=ApiResponse)
async def get_by_sku(sku: str, user: dict = Depends(get_current_user)):
    p = await product_repo.get_product_by_sku(sku)
    if not p:
        return ApiResponse(success=False, message="商品不存在")
    return ApiResponse(data=p.to_dict())


@router.get("/{product_id}", response_model=ApiResponse)
async def get_by_id(product_id: int, user: dict = Depends(get_current_user)):
    p = await product_repo.get_product_by_id(product_id)
    if not p:
        return ApiResponse(success=False, message="商品不存在")
    return ApiResponse(data=p.to_dict())


@router.post("", response_model=ApiResponse)
async def create_product(p: dict, user: dict = Depends(get_current_user)):
    """创建商品。请求体字段参考 ProductDTO。"""
    dto = ProductDTO(**p)
    pid = await product_repo.create_product(dto)
    # 同步到 Qdrant
    try:
        from app.storage.qdrant.product_indexer import index_single_product
        await index_single_product(pid)
    except Exception as e:
        pass  # 同步失败不影响创建
    return ApiResponse(data={"id": pid})


@router.put("/{product_id}", response_model=ApiResponse)
async def update_product(product_id: int, p: dict, user: dict = Depends(get_current_user)):
    """更新商品。"""
    dto = ProductDTO(**p)
    await product_repo.update_product(product_id, dto)
    # 同步到 Qdrant（重建索引）
    try:
        from app.storage.qdrant.product_indexer import index_single_product
        await index_single_product(product_id)
    except Exception as e:
        pass
    return ApiResponse(message="已更新")


@router.delete("/{product_id}", response_model=ApiResponse)
async def delete_product(product_id: int, user: dict = Depends(get_current_user)):
    """删除商品（软删除）。"""
    await product_repo.soft_delete_product(product_id)
    # 可选：同时从 Qdrant 删除（目前忽略，重建时会跳过该商品）
    return ApiResponse(message="已删除")


# ==================== 知识库重建 ====================
@router.post("/reindex-kb", response_model=ApiResponse)
async def reindex_product_kb(user: dict = Depends(get_current_user)):
    """重建商品知识库（Qdrant 全量向量化）。"""
    from app.storage.qdrant.product_indexer import reindex_all_products
    n = await reindex_all_products()
    return ApiResponse(data={"indexed": n})


# ==================== 订单明细 / 售后 ====================
@router.get("/order/{order_id}/items", response_model=ApiResponse)
async def list_order_items(order_id: int, user: dict = Depends(get_current_user)):
    items = await product_repo.list_order_items(order_id)
    return ApiResponse(data=[i.__dict__ for i in items])


@router.post("/after-sales", response_model=ApiResponse)
async def create_after_sales(t: dict, user: dict = Depends(get_current_user)):
    dto = AfterSalesDTO(**t)
    tid = await product_repo.create_after_sales(dto)
    return ApiResponse(data={"id": tid})


@router.get("/after-sales", response_model=ApiResponse)
async def list_after_sales(customer_id: int | None = None,
                           status: str | None = None,
                           limit: int = 20,
                           user: dict = Depends(get_current_user)):
    rows = await product_repo.list_after_sales(
        customer_id=customer_id, status=status, limit=limit
    )
    return ApiResponse(data=[r.__dict__ for r in rows])
