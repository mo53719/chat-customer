-- 渠道配置表
CREATE TABLE IF NOT EXISTS channel_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_key TEXT NOT NULL UNIQUE,
    channel_name TEXT NOT NULL,
    icon TEXT DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    api_key TEXT DEFAULT '',
    api_secret TEXT DEFAULT '',
    webhook_url TEXT DEFAULT '',
    auto_reply TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    config_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT
);

-- 预置默认渠道
INSERT OR IGNORE INTO channel_configs (channel_key, channel_name, icon, enabled) VALUES
    ('web', '官网在线客服', '🌐', 1),
    ('miniapp', '微信小程序', '💬', 1),
    ('wework', '企业微信', '📱', 1),
    ('douyin', '抖音企业号', '🎵', 0),
    ('app', '移动 App', '📲', 0);