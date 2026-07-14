-- 失败案例表：reviewer 检测到不合格回答时自动入库
CREATE TABLE IF NOT EXISTS badcases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_input TEXT NOT NULL,
    agent_answer TEXT,
    intent TEXT,
    agent_name TEXT,
    failed_rules TEXT,
    review_details TEXT,
    trace_id TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'fixed', 'ignored')),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    reviewed_at TEXT,
    reviewed_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_badcases_status ON badcases(status);
CREATE INDEX IF NOT EXISTS idx_badcases_session ON badcases(session_id);
CREATE INDEX IF NOT EXISTS idx_badcases_created ON badcases(created_at DESC);