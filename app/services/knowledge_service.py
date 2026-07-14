"""知识库管理服务：接收 ChunkDraft 列表 -> 向量化 -> 入 Qdrant + 写 meta。

入库管线职责明确：
  - 表格类（xlsx/csv）：每个 ChunkDraft 已是一行，直接 1:1 入库
  - 文本类（txt/md/json/log/pdf/docx）：ChunkDraft 是整文，交给 Ingestor 二次切分
"""
from __future__ import annotations

import uuid
from typing import Any

from config.settings import settings
from app.logger import get_logger
from app.storage.sqlite.repositories.knowledge_repo import knowledge_repo
from app.storage.qdrant.ingestor import Ingestor

_log = get_logger("services.knowledge")


class KnowledgeService:
    @staticmethod
    async def upload_drafts(doc_id: str | None, title: str, drafts: list, file_type: str = "md",
                            source: str | None = None,
                            uploaded_by: str | None = None,
                            chunk_size: int = 400, overlap: int = 80,
                            progress_callback=None,
                            file_hash: str | None = None,
                            parent_doc_id: str | None = None,
                            is_current: bool = True,
                            embedding_model: str | None = None,
                            embedding_version: str | None = None,
                            total_pages: int | None = None,
                            uploader_role: str | None = None,
                            tags: str | None = None,
                            doc_origin_url: str | None = None,
                            char_count: int = 0,
                            ) -> dict[str, Any]:
        """新版入库入口：接收解析层产出的 ChunkDraft 列表。

        drafts 元素需有 .content/.source/.sheet/.row/.heading_path/.extra 属性
        （ChunkDraft dataclass 或鸭子类型均可）。
        chunk_size/overlap 控制文本切分粒度，progress_callback 用于 WebSocket 推送进度。
        doc_id：外部传入时复用（路由层先建 meta 记录用），None 时自动生成。
        """
        if not embedding_model:
            embedding_model = settings.EMBEDDING_MODEL_NAME

        if not doc_id:
            doc_id = f"doc_{uuid.uuid4().hex[:16]}"
            await knowledge_repo.create(
                doc_id=doc_id, title=title, source=source, file_type=file_type,
                uploaded_by=uploaded_by, file_hash=file_hash,
                parent_doc_id=parent_doc_id, is_current=1 if is_current else 0,
                embedding_model=embedding_model, embedding_version=embedding_version,
                total_pages=total_pages, uploader_role=uploader_role,
                tags=tags, doc_origin_url=doc_origin_url, char_count=char_count,
            )
        try:
            cnt = await Ingestor.ingest_drafts(
                doc_id=doc_id, title=title, drafts=drafts,
                chunk_size=chunk_size, overlap=overlap,
                progress_callback=progress_callback,
                file_hash=file_hash,
                is_current=is_current,
                embedding_model=embedding_model,
                embedding_version=embedding_version,
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
            doc_id=None, title=title, drafts=[draft], file_type=file_type,
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