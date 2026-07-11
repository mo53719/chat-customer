"""商品搜索 / 查询工具。售前 Agent 用。"""
from __future__ import annotations

from .registry import register_tool, ToolResult
from app.storage.sqlite import product_repo


@register_tool(
    name="product_search",
    description="根据关键词 / 分类 / 品牌 / 价格区间查询商品。返回最匹配的 N 条，包含价格、库存、参数、卖点、描述等。",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "关键词（商品名称/品牌/型号/卖点）"},
            "category_id": {"type": "integer", "description": "分类 ID，可选"},
            "brand": {"type": "string", "description": "品牌，可选"},
            "min_price": {"type": "number", "description": "最低价"},
            "max_price": {"type": "number", "description": "最高价"},
            "limit": {"type": "integer", "default": 5, "description": "返回数量"},
        },
        "required": [],
    },
)
async def product_search(state, keyword: str | None = None,
                         category_id: int | None = None,
                         brand: str | None = None,
                         min_price: float | None = None,
                         max_price: float | None = None,
                         limit: int = 5) -> ToolResult:
    """精确条件检索商品。"""
    items = await product_repo.search_products(
        keyword=keyword, category_id=category_id, brand=brand,
        min_price=min_price, max_price=max_price, limit=limit,
    )
    return ToolResult(
        data=[p.to_dict() if hasattr(p, "to_dict") else p.__dict__ for p in items],
        meta={"count": len(items)},
    )


@register_tool(
    name="product_search_semantic",
    description="基于语义相似度搜索商品（兜底用：精确搜索无结果时使用）。适合「适合送礼的、性价比高的、适合送女朋友的」这类模糊需求。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "自然语言查询"},
            "top_k": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
)
async def product_search_semantic(state, query: str, top_k: int = 5) -> ToolResult:
    """语义相似度商品检索。"""
    from app.storage.qdrant.product_indexer import search_products_semantic
    hits = await search_products_semantic(query=query, top_k=top_k)
    return ToolResult(data=hits, meta={"count": len(hits)})


@register_tool(
    name="product_get_detail",
    description="按 SKU 或商品 ID 查询商品详细信息（参数、描述、保修、包装清单等）。",
    parameters={
        "type": "object",
        "properties": {
            "sku": {"type": "string", "description": "商品编号"},
            "product_id": {"type": "integer", "description": "商品 ID"},
        },
    },
)
async def product_get_detail(state, sku: str | None = None,
                             product_id: int | None = None) -> ToolResult:
    if sku:
        p = await product_repo.get_product_by_sku(sku)
    elif product_id is not None:
        p = await product_repo.get_product_by_id(product_id)
    else:
        return ToolResult(success=False, error="必须传 sku 或 product_id")
    if not p:
        return ToolResult(success=False, error="商品不存在")
    return ToolResult(data=p.to_dict() if hasattr(p, "to_dict") else p.__dict__)


@register_tool(
    name="product_list_categories",
    description="获取商品分类列表（一级 / 二级分类），用于回答「有哪些品类」。",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def product_list_categories(state) -> ToolResult:
    cats = await product_repo.list_categories()
    return ToolResult(
        data=[{"id": c.id, "name": c.name, "parent_id": c.parent_id} for c in cats],
        meta={"count": len(cats)},
    )
