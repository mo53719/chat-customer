"""知识库元数据仓储。"""
from __future__ import annotations

import json
from typing import Any

from ..connection import SqliteConnection
from ..models import KnowledgeMetaDTO
from app.logger import get_logger

_log = get_logger("storage.knowledge_repo")


class KnowledgeRepo:
    # ── 配置管理 ────────────────────────────────────────────
    @staticmethod
    async def _ensure_config_table() -> None:
        db = await SqliteConnection.get_db()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.commit()

    @staticmethod
    async def get_config() -> dict[str, Any]:
        await KnowledgeRepo._ensure_config_table()
        rows = await SqliteConnection.fetchall("SELECT key, value FROM knowledge_config")
        result = {r["key"]: r["value"] for r in rows}
        return {
            "chunk_size": int(result.get("chunk_size", "400")),
            "overlap": int(result.get("overlap", "80")),
        }

    @staticmethod
    async def save_config(chunk_size: int, overlap: int) -> None:
        await KnowledgeRepo._ensure_config_table()
        await SqliteConnection.write_with_lock(
            "knowledge_config",
            "INSERT OR REPLACE INTO knowledge_config (key, value) VALUES (?, ?)",
            ("chunk_size", str(chunk_size)),
        )
        await SqliteConnection.write_with_lock(
            "knowledge_config",
            "INSERT OR REPLACE INTO knowledge_config (key, value) VALUES (?, ?)",
            ("overlap", str(overlap)),
        )
        _log.info(f"保存知识库配置 chunk_size={chunk_size} overlap={overlap}")

    # ── 文档 CRUD ────────────────────────────────────────────
    @staticmethod
    async def create(doc_id: str, title: str | None, source: str | None,
                     file_type: str | None, uploaded_by: str | None = None,
                     file_hash: str | None = None,
                     parent_doc_id: str | None = None,
                     is_current: int = 1,
                     embedding_model: str | None = None,
                     embedding_version: str | None = None,
                     total_pages: int | None = None,
                     uploader_role: str | None = None,
                     tags: str | None = None,
                     doc_origin_url: str | None = None,
                     char_count: int = 0,
                     ) -> int:
        cur = await SqliteConnection.write_with_lock(
            "knowledge_meta",
            """INSERT INTO knowledge_meta
               (doc_id, title, source, file_type, status, uploaded_by,
                file_hash, parent_doc_id, is_current, embedding_model,
                embedding_version, total_pages, uploader_role, tags,
                doc_origin_url, char_count)
               VALUES (?,?,?,?, 'processing', ?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, title, source, file_type, uploaded_by,
             file_hash, parent_doc_id, is_current, embedding_model,
             embedding_version, total_pages, uploader_role, tags,
             doc_origin_url, char_count),
        )
        return cur.lastrowid or 0

    @staticmethod
    async def update_status(doc_id: str, status: str, chunk_count: int | None = None) -> None:
        if chunk_count is not None:
            await SqliteConnection.write_with_lock(
                "knowledge_meta",
                "UPDATE knowledge_meta SET status=?, chunk_count=? WHERE doc_id=?",
                (status, chunk_count, doc_id),
            )
        else:
            await SqliteConnection.write_with_lock(
                "knowledge_meta",
                "UPDATE knowledge_meta SET status=? WHERE doc_id=?",
                (status, doc_id),
            )

    @staticmethod
    def _row_to_dto(row: dict[str, Any]) -> KnowledgeMetaDTO:
        return KnowledgeMetaDTO(
            id=row["id"], doc_id=row["doc_id"], title=row["title"],
            source=row["source"], file_type=row["file_type"],
            chunk_count=row["chunk_count"], status=row["status"],
            uploaded_by=row["uploaded_by"], created_at=row["created_at"],
            file_hash=row.get("file_hash"),
            parent_doc_id=row.get("parent_doc_id"),
            is_current=row.get("is_current", 1),
            embedding_model=row.get("embedding_model"),
            embedding_version=row.get("embedding_version"),
            total_pages=row.get("total_pages"),
            uploader_role=row.get("uploader_role"),
            tags=row.get("tags"),
            doc_origin_url=row.get("doc_origin_url"),
            language=row.get("language", "zh"),
            char_count=row.get("char_count", 0),
        )

    @staticmethod
    async def get(doc_id: str) -> KnowledgeMetaDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM knowledge_meta WHERE doc_id=? AND deleted_at IS NULL", (doc_id,)
        )
        if not row:
            return None
        return KnowledgeRepo._row_to_dto(row)

    @staticmethod
    async def list_all() -> list[KnowledgeMetaDTO]:
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM knowledge_meta WHERE deleted_at IS NULL ORDER BY id DESC"
        )
        return [KnowledgeRepo._row_to_dto(r) for r in rows]

    @staticmethod
    async def soft_delete(doc_id: str, deleted_by: str | None = None) -> None:
        from .recycle_repo import recycle_repo
        row = await SqliteConnection.fetchone(
            "SELECT * FROM knowledge_meta WHERE doc_id=?", (doc_id,)
        )
        if row:
            await recycle_repo.snapshot("knowledge_meta", row["id"], dict(row), deleted_by)
        await SqliteConnection.write_with_lock(
            "knowledge_meta",
            "UPDATE knowledge_meta SET deleted_at=datetime('now'), status='deleted' WHERE doc_id=?",
            (doc_id,),
        )

    # ── 去重 / 版本控制 ──────────────────────────────────────
    @staticmethod
    async def find_by_hash(file_hash: str) -> KnowledgeMetaDTO | None:
        """按文件指纹查找已存在的文档（仅查当前生效的）。"""
        row = await SqliteConnection.fetchone(
            "SELECT * FROM knowledge_meta WHERE file_hash=? AND deleted_at IS NULL AND is_current=1",
            (file_hash,),
        )
        if not row:
            return None
        return KnowledgeRepo._row_to_dto(row)

    @staticmethod
    async def find_any_by_hash(file_hash: str) -> list[KnowledgeMetaDTO]:
        """按文件指纹查找所有版本（含历史版本）。"""
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM knowledge_meta WHERE file_hash=? AND deleted_at IS NULL",
            (file_hash,),
        )
        return [KnowledgeRepo._row_to_dto(r) for r in rows]

    @staticmethod
    async def mark_not_current(doc_id: str) -> None:
        """将文档标记为非当前生效版本。"""
        await SqliteConnection.write_with_lock(
            "knowledge_meta",
            "UPDATE knowledge_meta SET is_current=0 WHERE doc_id=?",
            (doc_id,),
        )

    @staticmethod
    async def set_current(doc_id: str) -> None:
        """将文档标记为当前生效版本。"""
        await SqliteConnection.write_with_lock(
            "knowledge_meta",
            "UPDATE knowledge_meta SET is_current=1 WHERE doc_id=?",
            (doc_id,),
        )

    # ── 版本历史 ─────────────────────────────────────────────
    @staticmethod
    async def create_version_row(doc_id: str, parent_doc_id: str | None,
                                 version_no: int, file_hash: str | None,
                                 chunk_count: int = 0, note: str | None = None) -> None:
        await SqliteConnection.write_with_lock(
            "knowledge_doc_versions",
            """INSERT INTO knowledge_doc_versions
               (doc_id, parent_doc_id, version_no, file_hash, chunk_count, note)
               VALUES (?,?,?,?,?,?)""",
            (doc_id, parent_doc_id, version_no, file_hash, chunk_count, note),
        )

    @staticmethod
    async def get_next_version_no(parent_doc_id: str) -> int:
        """获取同文档链的下一个版本号。"""
        row = await SqliteConnection.fetchone(
            "SELECT MAX(version_no) as max_v FROM knowledge_doc_versions WHERE parent_doc_id=?",
            (parent_doc_id,),
        )
        return (row["max_v"] or 0) + 1

    @staticmethod
    async def list_versions(parent_doc_id: str) -> list[dict[str, Any]]:
        """列出某文档链的所有历史版本。"""
        rows = await SqliteConnection.fetchall(
            """SELECT v.*, m.title, m.source, m.is_current
               FROM knowledge_doc_versions v
               LEFT JOIN knowledge_meta m ON v.doc_id = m.doc_id
               WHERE v.parent_doc_id = ?
               UNION ALL
               SELECT v.*, m.title, m.source, m.is_current
               FROM knowledge_doc_versions v
               LEFT JOIN knowledge_meta m ON v.doc_id = m.doc_id
               WHERE v.doc_id = ?
               ORDER BY v.version_no DESC""",
            (parent_doc_id, parent_doc_id),
        )
        return [dict(r) for r in rows]

    # ── 更新元数据 ───────────────────────────────────────────
    @staticmethod
    async def update_meta(doc_id: str, **kwargs) -> None:
        """按 key=value 更新 knowledge_meta 字段。"""
        if not kwargs:
            return
        sets = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [doc_id]
        await SqliteConnection.write_with_lock(
            "knowledge_meta",
            f"UPDATE knowledge_meta SET {sets} WHERE doc_id=?",
            tuple(values),
        )


knowledge_repo = KnowledgeRepo()