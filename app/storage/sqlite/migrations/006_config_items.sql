-- 006_config_items: 配置列表 + 变更记录
CREATE TABLE IF NOT EXISTS config_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    config_type TEXT NOT NULL,
    config_value TEXT NOT NULL DEFAULT '{}',
    description TEXT DEFAULT '',
    is_enabled INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS config_change_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER NOT NULL,
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (config_id) REFERENCES config_items(id)
);

CREATE INDEX IF NOT EXISTS idx_config_type ON config_items(config_type);
CREATE INDEX IF NOT EXISTS idx_config_log_config ON config_change_logs(config_id);

-- 插入默认配置项
INSERT OR IGNORE INTO config_items (name, config_type, config_value, description, updated_by)
VALUES
    ('意图识别置信度阈值', 'intent_threshold', '{"threshold": 0.5}', 'LLM 意图识别的最低置信度', 'system'),
    ('转人工规则', 'transfer_rule', '{"max_retries": 3, "negative_keywords": ["投诉", "人工", "转人工"]}', '触发转人工的条件配置', 'system'),
    ('超时回复设置', 'timeout_reply', '{"timeout_seconds": 30, "reply_text": "抱歉，我正在处理您的问题，请稍候..."}', '超时后的自动回复内容', 'system');