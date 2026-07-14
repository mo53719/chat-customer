-- 005_rag_traceability: RAG 知识库可溯源增强
-- 添加文档指纹、版本控制、页码、embedding 模型等字段

-- 扩展 knowledge_meta 表
ALTER TABLE knowledge_meta ADD COLUMN file_hash TEXT;
ALTER TABLE knowledge_meta ADD COLUMN parent_doc_id TEXT;
ALTER TABLE knowledge_meta ADD COLUMN is_current INTEGER NOT NULL DEFAULT 1;
ALTER TABLE knowledge_meta ADD COLUMN embedding_model TEXT;
ALTER TABLE knowledge_meta ADD COLUMN embedding_version TEXT;
ALTER TABLE knowledge_meta ADD COLUMN total_pages INTEGER;
ALTER TABLE knowledge_meta ADD COLUMN uploader_role TEXT;
ALTER TABLE knowledge_meta ADD COLUMN tags TEXT;
ALTER TABLE knowledge_meta ADD COLUMN doc_origin_url TEXT;
ALTER TABLE knowledge_meta ADD COLUMN language TEXT DEFAULT 'zh';
ALTER TABLE knowledge_meta ADD COLUMN char_count INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_knowledge_meta_hash ON knowledge_meta(file_hash);
CREATE INDEX IF NOT EXISTS idx_knowledge_meta_parent ON knowledge_meta(parent_doc_id);

-- 版本历史表：每次 replace/version 写一行
CREATE TABLE IF NOT EXISTS knowledge_doc_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    parent_doc_id TEXT,
    version_no INTEGER NOT NULL DEFAULT 1,
    file_hash TEXT,
    chunk_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    note TEXT,
    FOREIGN KEY (doc_id) REFERENCES knowledge_meta(doc_id)
);
CREATE INDEX IF NOT EXISTS idx_versions_doc ON knowledge_doc_versions(doc_id);