"""知识库管理服务：接收 ChunkDraft 列表 -> 向量化 -> 入 Qdrant + 写 meta。

入库管线职责明确：
  - 表格类（xlsx/csv）：每个 ChunkDraft 已是一行，直接 1:1 入库
  - 文本类（txt/md/json/log）：ChunkDraft 是整文，交给 Ingestor 二次切分
"""
from __future__ import annotations

import uuid
from typing import Any

from app.logger import get_logger
from app.storage.sqlite.repositories.knowledge_repo import knowledge_repo
from app.storage.qdrant.ingestor import Ingestor

_log = get_logger("services.knowledge")


class KnowledgeService:
    @staticmethod
    async def upload_drafts(title: str, drafts: list, file_type: str = "md",
                            source: str | None = None,
                            uploaded_by: str | None = None,
                            chunk_size: int = 400, overlap: int = 80,
                            progress_callback=None) -> dict[str, Any]:
        """新版入库入口：接收解析层产出的 ChunkDraft 列表。

        drafts 元素需有 .content/.source/.sheet/.row/.heading_path/.extra 属性
        （ChunkDraft dataclass 或鸭子类型均可）。
        chunk_size/overlap 控制文本切分粒度，progress_callback 用于 WebSocket 推送进度。
        """
        doc_id = f"doc_{uuid.uuid4().hex[:16]}"
        await knowledge_repo.create(doc_id, title, source, file_type, uploaded_by)
        try:
            cnt = await Ingestor.ingest_drafts(
                doc_id=doc_id, title=title, drafts=drafts,
                chunk_size=chunk_size, overlap=overlap,
                progress_callback=progress_callback,
            )
            await knowledge_repo.update_status(doc_id, "ready", chunk_count=cnt)
            if progress_callback:
                await progress_callback("done", cnt, cnt, "向量化完成")
            return {"doc_id": doc_id, "chunks": cnt, "status": "ready"}
        except Exception as e:
            _log.exception(f"文档 {doc_id} 入库失败：{e}")
            await knowledge_repo.update_status(doc_id, "failed")
            if progress_callback:
                await progress_callback("error", 0, 0, str(e))
            return {"doc_id": doc_id, "chunks": 0, "status": "failed", "error": str(e)}

    @staticmethod
    async def upload(title: str, content: str, file_type: str = "md",
                     source: str | None = None,
                     uploaded_by: str | None = None) -> dict[str, Any]:
        """旧入口保留：整文 -> 单个 ChunkDraft -> 由 Ingestor 二次切分。"""
        from app.api.routes.knowledge import ChunkDraft
        draft = ChunkDraft(content=content, source=source or "", heading_path=source or "")
        return await KnowledgeService.upload_drafts(
            title=title, drafts=[draft], file_type=file_type,
            source=source, uploaded_by=uploaded_by,
        )

    @staticmethod
    async def list_docs() -> list[dict[str, Any]]:
        rows = await knowledge_repo.list_all()
        return [r.__dict__ for r in rows]

    @staticmethod
    async def delete(doc_id: str, deleted_by: str | None = None) -> None:
        try:
            await Ingestor.delete_doc(doc_id)
        except Exception as e:
            _log.warning(f"删除 Qdrant 向量失败 {doc_id}：{e}")
        await knowledge_repo.soft_delete(doc_id, deleted_by)


knowledge_service = KnowledgeService()
