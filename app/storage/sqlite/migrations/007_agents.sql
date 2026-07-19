-- 007_agents: 客服管理
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    account TEXT NOT NULL UNIQUE,
    department TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'offline',
    current_sessions INTEGER NOT NULL DEFAULT 0,
    max_sessions INTEGER NOT NULL DEFAULT 5,
    channel TEXT DEFAULT '',
    role TEXT NOT NULL DEFAULT 'agent',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_dept ON agents(department);

-- 插入默认客服
INSERT OR IGNORE INTO agents (name, account, department, status, role, channel)
VALUES
    ('张客服', 'zhang', '售前部', 'online', 'agent', 'web'),
    ('李客服', 'li', '售后部', 'offline', 'agent', 'web'),
    ('王主管', 'wang', '售前部', 'online', 'supervisor', 'web,wechat'),
    ('赵客服', 'zhao', '售后部', 'busy', 'agent', 'douyin');