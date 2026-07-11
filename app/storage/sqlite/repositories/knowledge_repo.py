"""知识库元数据仓储。"""
from __future__ import annotations

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
                     file_type: str | None, uploaded_by: str | None = None) -> int:
        cur = await SqliteConnection.write_with_lock(
            "knowledge_meta",
            """INSERT INTO knowledge_meta (doc_id, title, source, file_type, status, uploaded_by)
               VALUES (?,?,?,?, 'processing', ?)""",
            (doc_id, title, source, file_type, uploaded_by),
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
    async def get(doc_id: str) -> KnowledgeMetaDTO | None:
        row = await SqliteConnection.fetchone(
            "SELECT * FROM knowledge_meta WHERE doc_id=? AND deleted_at IS NULL", (doc_id,)
        )
        if not row:
            return None
        return KnowledgeMetaDTO(
            id=row["id"], doc_id=row["doc_id"], title=row["title"],
            source=row["source"], file_type=row["file_type"],
            chunk_count=row["chunk_count"], status=row["status"],
            uploaded_by=row["uploaded_by"], created_at=row["created_at"],
        )

    @staticmethod
    async def list_all() -> list[KnowledgeMetaDTO]:
        rows = await SqliteConnection.fetchall(
            "SELECT * FROM knowledge_meta WHERE deleted_at IS NULL ORDER BY id DESC"
        )
        return [
            KnowledgeMetaDTO(
                id=r["id"], doc_id=r["doc_id"], title=r["title"], source=r["source"],
                file_type=r["file_type"], chunk_count=r["chunk_count"], status=r["status"],
                uploaded_by=r["uploaded_by"], created_at=r["created_at"],
            )
            for r in rows
        ]

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


knowledge_repo = KnowledgeRepo()
