"""一键重建 Qdrant 集合 + 重新导入演示数据。

用法：
    python -m app.scripts.rebuild_qdrant

适用场景：
    1. embedding 模型切换 / 维度变更
    2. Qdrant 集合结构升级
    3. 演示数据重新生成
"""
from __future__ import annotations

import asyncio

from config.settings import settings
from app.logger import get_logger
from app.storage.qdrant.collection import delete_collection, ensure_collection
from app.storage.qdrant.product_indexer import reindex_all_products
from app.llm.embedding import warmup

_log = get_logger("scripts.rebuild_qdrant")


async def rebuild_all() -> None:
    """删除所有 Qdrant 集合 + 用新维度重建 + 重导商品数据。"""
    print(f"=== Qdrant 重建开始 ===")
    print(f"EMBEDDING_BACKEND = {settings.EMBEDDING_BACKEND}")
    print(f"EMBEDDING_DIM     = {settings.EMBEDDING_DIM}")

    # 0) 预热 + 验证模型
    print("\n[1/4] 预热 embedding 模型...")
    info = await warmup()
    print(f"  → {info}")
    if not info.get("ok"):
        _log.error(f"embedding 模型异常：{info}")
        if not info.get("dim"):
            print("\n  ⚠️  本地模型加载失败，请检查：")
            print(f"     路径：{settings.embedding_local_abs_path}")
            print(f"     fastembed model_name：{getattr(settings, 'EMBEDDING_MODEL_NAME', 'BAAI/bge-small-zh-v1.5')}")
            print(f"     pip 是否已安装：fastembed==0.7.2")
            return

    collections = [
        ("QDRANT_COLLECTION", settings.QDRANT_COLLECTION),
        ("QDRANT_PRODUCT_COLLECTION", settings.QDRANT_PRODUCT_COLLECTION),
        ("QDRANT_LONG_TERM_COLLECTION", settings.QDRANT_LONG_TERM_COLLECTION),
    ]

    # 1) 删除旧集合
    print("\n[2/4] 删除旧集合...")
    for label, name in collections:
        try:
            await delete_collection(name)
            print(f"  - {label} = {name} 已删除")
        except Exception as e:
            print(f"  ! {label} = {name} 删除失败（可能不存在）：{e}")

    # 2) 用新维度重建
    print(f"\n[3/4] 重建 {len(collections)} 个集合（维度 {settings.EMBEDDING_DIM}）...")
    for label, name in collections:
        try:
            await ensure_collection(name)
            print(f"  + {label} = {name} 创建成功")
        except Exception as e:
            print(f"  ✗ {label} = {name} 创建失败：{e}")

    # 3) 重导商品数据
    print("\n[4/4] 重建商品索引...")
    try:
        cnt = await reindex_all_products()
        print(f"  ✓ 商品索引完成：{cnt} 条")
    except Exception as e:
        print(f"  ✗ 商品索引失败：{e}")
        _log.exception(e)

    print(f"\n=== Qdrant 重建完成 ===")
    print(f"⚠️  业务侧知识库（chat_customer_kb）需要重新上传文档，"
          f"旧向量已不可用。")


if __name__ == "__main__":
    asyncio.run(rebuild_all())
