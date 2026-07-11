"""文档切片 + 向量化入库。

两种入口：
  - ingest_drafts(drafts): 接收解析层产出的 ChunkDraft 列表
      * 表格类（含 sheet/row 字段）直接 1:1 入库
      * 文本类（仅 source/heading_path）走 split_text 二次切分
  - ingest(text): 旧入口，整文切分入库（向后兼容）
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from config.settings import settings
from app.logger import get_logger

from .client import get_qdrant
from .collection import ensure_collection

_log = get_logger("storage.qdrant.ingestor")


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

    sentences: list[str] = []
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
        if len(buf) + len(s) <= chunk_size:
            buf += s
        else:
            if buf:
                chunks.append(buf)
                buf = buf[-overlap:] + s if overlap < len(buf) else s
            else:
                buf = s
    if buf:
        chunks.append(buf)
    return chunks


class Ingestor:
    @staticmethod
    async def ingest_drafts(doc_id: str, title: str, drafts: list,
                             collection: str | None = None,
                             chunk_size: int = 400, overlap: int = 80,
                             progress_callback=None) -> int:
        """新版入库：接收 ChunkDraft 列表。

        - 表格类 chunk（含 sheet/row）：直接 1:1 入库
        - 文本类 chunk（仅整文）：二次切分后入库
        每个 chunk payload 完整携带：doc_id/title/chunk_idx/source/sheet/row/
        heading_path/created_at/text。

        progress_callback(phase, current, total, message) 用于 WebSocket 推送进度。
        """
        from app.llm.embedding import embed_texts

        coll = collection or settings.QDRANT_COLLECTION
        await ensure_collection(coll)

        # 把 drafts 展平成 (text, meta) 列表
        flat: list[tuple[str, dict[str, Any]]] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for d in drafts:
            content = getattr(d, "content", "") or ""
            meta = {
                "source": getattr(d, "source", "") or "",
                "sheet": getattr(d, "sheet", None),
                "row": getattr(d, "row", None),
                "heading_path": getattr(d, "heading_path", None),
                "extra": getattr(d, "extra", {}) or {},
            }
            # 表格类（带 row 或 sheet）直接整段入库
            if meta["sheet"] is not None or meta["row"] is not None:
                flat.append((content, meta))
            else:
                # 文本类：二次切分
                for piece in split_text(content, chunk_size=chunk_size, overlap=overlap):
                    flat.append((piece, meta))

        if not flat:
            _log.warning(f"文档 {doc_id} 切片为空")
            return 0

        total = len(flat)
        _log.info(f"文档 {doc_id} 待向量化 {total} 段 (chunk_size={chunk_size}, overlap={overlap})")

        if progress_callback:
            await progress_callback("splitting", total, total, f"文本切分完成，共 {total} 段")

        # 分批 embed（dashscope 上限 10，本地 fastembed 32）
        batch = settings.EMBEDDING_BATCH_SIZE or 32
        all_vecs: list[list[float]] = []
        for i in range(0, total, batch):
            texts = [t for t, _ in flat[i:i + batch]]
            all_vecs.extend(await embed_texts(texts))
            done = min(i + batch, total)
            if progress_callback:
                await progress_callback("embedding", done, total, f"向量化 {done}/{total} 段")

        if progress_callback:
            await progress_callback("embedding", total, total, f"向量化完成，共 {total} 段")

        points = []
        for i, ((text, meta), vec) in enumerate(zip(flat, all_vecs)):
            points.append({
                "id": str(uuid.uuid4()),
                "vector": vec,
                "payload": {
                    "doc_id": doc_id,
                    "title": title,
                    "chunk_idx": i,
                    "text": text,
                    "source": meta["source"],
                    "sheet": meta["sheet"],
                    "row": meta["row"],
                    "heading_path": meta["heading_path"],
                    "created_at": now_iso,
                },
            })

        client = get_qdrant()
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
