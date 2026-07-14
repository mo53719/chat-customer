"""文档切片 + 向量化入库。

两种入口：
  - ingest_drafts(drafts): 接收解析层产出的 ChunkDraft 列表
      * 表格类（含 sheet/row 字段）直接 1:1 入库
      * 文本类（仅 source/heading_path）走 split_text 二次切分
  - ingest(text): 旧入口，整文切分入库（向后兼容）
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

# 核心依赖：配置、日志、Qdrant 客户端、集合管理
from config.settings import settings
from app.logger import get_logger

from .client import get_qdrant
from .collection import ensure_collection

# 模块级 logger，用于追踪文档入库流程
_log = get_logger("storage.qdrant.ingestor")

# 稳定 chunk_id 的命名空间 UUID
_NAMESPACE_DNS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _stable_chunk_id(doc_id: str, chunk_idx: int, text: str) -> str:
    """生成稳定的 chunk_id，同一内容再入库 id 不变。"""
    seed = f"{doc_id}|{chunk_idx}|{text[:200]}"
    return str(uuid.uuid5(_NAMESPACE_DNS, seed))


def split_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """递归式切片：按 \\n\\n -> \\n -> 句末标点 -> 长度兜底。

    改进点：先按段落分，再按句子累加到 chunk_size，overlap 取末尾片段。
    """
    if not text:
        return []

    # 第一步：按段落（双换行）粗切
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if not paragraphs:
        return []

    # 第二步：按句子累加到 chunk_size，overlap 取末尾片段
    sentences: list[str] = []
    # 按句末标点切分每个段落为独立句子
    sent_split = re.compile(r"(?<=[。！？!?.\n])\s*")
    for p in paragraphs:
        parts = [s for s in sent_split.split(p) if s.strip()]
        sentences.extend(parts or [p])

    chunks: list[str] = []
    buf = ""
    for s in sentences:
        if not s:
            continue
        # 单句超长，硬切
        if len(s) > chunk_size:
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(s), chunk_size - overlap):
                chunks.append(s[i:i + chunk_size])
            continue
        # 累加句子到缓冲区，达到 chunk_size 时输出
        if len(buf) + len(s) <= chunk_size:
            buf += s
        else:
            if buf:
                chunks.append(buf)
                # overlap 取末尾片段，保持上下文连续性
                buf = buf[-overlap:] + s if overlap < len(buf) else s
            else:
                buf = s
    if buf:
        chunks.append(buf)
    return chunks


class Ingestor:
    """文档切片 + 向量化入库。

    提供三种入口：ingest_drafts（新版，接收 ChunkDraft 列表）、
    ingest（旧版兼容）、delete_doc（按 doc_id 删除向量）。
    """
    @staticmethod
    async def ingest_drafts(doc_id: str, title: str, drafts: list,
                             collection: str | None = None,
                             chunk_size: int = 400, overlap: int = 80,
                             progress_callback=None,
                             file_hash: str | None = None,
                             is_current: bool = True,
                             embedding_model: str | None = None,
                             embedding_version: str | None = None,
                             language: str = "zh",
                             ) -> int:
        """新版入库：接收 ChunkDraft 列表。

        - 表格类 chunk（含 sheet/row）：直接 1:1 入库
        - 文本类 chunk（仅整文）：二次切分后入库
        每个 chunk payload 完整携带：chunk_id/doc_id/title/chunk_idx/source/sheet/row/
        heading_path/page_no/created_at/text/file_hash/is_current 等。

        progress_callback(phase, current, total, message) 用于 WebSocket 推送进度。
        """
        from app.llm.embedding import embed_texts

        coll = collection or settings.QDRANT_COLLECTION
        await ensure_collection(coll)

        # 把 drafts 展平成 (text, meta) 列表
        flat: list[tuple[str, dict[str, Any]]] = []
        # 统一时间戳，所有 chunk 共用同一个 created_at
        now_iso = datetime.now(timezone.utc).isoformat()
        for d in drafts:
            content = getattr(d, "content", "") or ""
            # 构建 chunk 元数据：来源、表格位置、标题路径、页码等
            meta = {
                "source": getattr(d, "source", "") or "",
                "sheet": getattr(d, "sheet", None),
                "row": getattr(d, "row", None),
                "heading_path": getattr(d, "heading_path", None),
                "extra": getattr(d, "extra", {}) or {},
                "page_no": getattr(d, "page_no", None),
                "section": getattr(d, "section", None),
                "char_start": getattr(d, "char_start", None),
                "char_end": getattr(d, "char_end", None),
                "char_count": getattr(d, "char_count", None),
            }
            # 表格类（带 row 或 sheet）直接整段入库，不再二次切分
            if meta["sheet"] is not None or meta["row"] is not None:
                flat.append((content, meta))
            else:
                # 文本类：二次切分
                pieces = split_text(content, chunk_size=chunk_size, overlap=overlap)
                # 计算每个 piece 在原文中的 char_start/char_end
                pos = 0
                for piece in pieces:
                    piece_meta = dict(meta)
                    piece_meta["char_start"] = pos
                    piece_meta["char_end"] = pos + len(piece)
                    piece_meta["char_count"] = len(piece)
                    flat.append((piece, piece_meta))
                    pos += len(piece)

        if not flat:
            _log.warning(f"文档 {doc_id} 切片为空")
            return 0

        total = len(flat)
        _log.info(f"文档 {doc_id} 待向量化 {total} 段 (chunk_size={chunk_size}, overlap={overlap})")

        if progress_callback:
            await progress_callback("splitting", total, total, f"文本切分完成，共 {total} 段")

        # 分批 embed：dashscope 上限 10，本地 fastembed 默认 32
        batch = settings.EMBEDDING_BATCH_SIZE or 32
        # 存储所有向量结果，按批次顺序拼接
        all_vecs: list[list[float]] = []
        for i in range(0, total, batch):
            # 提取当前批次的文本列表
            texts = [t for t, _ in flat[i:i + batch]]
            all_vecs.extend(await embed_texts(texts))
            done = min(i + batch, total)
            if progress_callback:
                await progress_callback("embedding", done, total, f"向量化 {done}/{total} 段")

        if progress_callback:
            await progress_callback("embedding", total, total, f"向量化完成，共 {total} 段")

        # 构造 Qdrant points：每个 point 含稳定 chunk_id、向量和完整 payload
        points = []
        for i, ((text, meta), vec) in enumerate(zip(flat, all_vecs)):
            points.append({
                "id": _stable_chunk_id(doc_id, i, text),
                "vector": vec,
                "payload": {
                    "chunk_id": _stable_chunk_id(doc_id, i, text),
                    "doc_id": doc_id,
                    "title": title,
                    "chunk_idx": i,
                    "text": text,
                    "source": meta["source"],
                    "sheet": meta["sheet"],
                    "row": meta["row"],
                    "heading_path": meta["heading_path"],
                    "page_no": meta["page_no"],
                    "section": meta["section"],
                    "file_hash": file_hash,
                    "is_current": is_current,
                    "embedding_model": embedding_model,
                    "embedding_version": embedding_version,
                    "language": language,
                    "char_start": meta["char_start"],
                    "char_end": meta["char_end"],
                    "char_count": meta["char_count"],
                    "created_at": now_iso,
                },
            })

        client = get_qdrant()
        # Qdrant 单次请求上限 32MB，每批 256 条避免超限
        UPLOAD_BATCH = 256
        for i in range(0, len(points), UPLOAD_BATCH):
            batch_points = points[i:i + UPLOAD_BATCH]
            await client.upsert(collection_name=coll, points=batch_points)
            done = min(i + UPLOAD_BATCH, total)
            if progress_callback:
                await progress_callback("upserting", done, total, f"入库 {done}/{total} 段")

        _log.info(f"文档 {doc_id} 入库 {len(points)} 条向量 (分 {(len(points) + UPLOAD_BATCH - 1) // UPLOAD_BATCH} 批)")
        return len(points)

    @staticmethod
    async def ingest(doc_id: str, title: str, text: str,
                     collection: str | None = None,
                     metadata: dict[str, Any] | None = None) -> int:
        """旧入口（向后兼容）：整文 + 单一 metadata 切分入库。"""
        from app.api.routes.knowledge import ChunkDraft
        source = (metadata or {}).get("source", "")
        draft = ChunkDraft(content=text, source=source, heading_path=source or None)
        return await Ingestor.ingest_drafts(
            doc_id=doc_id, title=title, drafts=[draft], collection=collection,
        )

    @staticmethod
    async def delete_doc(doc_id: str, collection: str | None = None) -> None:
        """按 doc_id 删除 Qdrant 中所有向量（按 payload.doc_id 过滤）。"""
        coll = collection or settings.QDRANT_COLLECTION
        client = get_qdrant()
        from qdrant_client.http import models as qmodels
        selector = qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[qmodels.FieldCondition(
                    key="doc_id",
                    match=qmodels.MatchValue(value=doc_id),
                )]
            )
        )
        await client.delete(collection_name=coll, points_selector=selector)
        _log.info(f"删除文档 {doc_id} 全部向量")

    @staticmethod
    async def scroll_chunks(doc_id: str, limit: int = 100,
                            collection: str | None = None) -> list[dict[str, Any]]:
        """按 doc_id 滚动获取所有 chunk（用于前端查看切片）。"""
        coll = collection or settings.QDRANT_COLLECTION
        client = get_qdrant()
        from qdrant_client.http import models as qmodels
        points, _ = await client.scroll(
            collection_name=coll,
            scroll_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(
                    key="doc_id",
                    match=qmodels.MatchValue(value=doc_id),
                )]
            ),
            limit=limit,
            with_payload=True,
        )
        results = []
        for p in points:
            payload = p.payload or {}
            results.append({
                "chunk_id": payload.get("chunk_id"),
                "chunk_idx": payload.get("chunk_idx"),
                "text": payload.get("text", ""),
                "source": payload.get("source"),
                "sheet": payload.get("sheet"),
                "row": payload.get("row"),
                "heading_path": payload.get("heading_path"),
                "page_no": payload.get("page_no"),
                "section": payload.get("section"),
                "file_hash": payload.get("file_hash"),
                "is_current": payload.get("is_current"),
                "char_start": payload.get("char_start"),
                "char_end": payload.get("char_end"),
                "char_count": payload.get("char_count"),
                "created_at": payload.get("created_at"),
            })
        return results