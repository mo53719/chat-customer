-- 010_system_config: 通用设置
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system_name TEXT NOT NULL DEFAULT '智能客服系统',
    login_timeout INTEGER NOT NULL DEFAULT 30,
    log_retention_days INTEGER NOT NULL DEFAULT 90,
    message_push_enabled INTEGER NOT NULL DEFAULT 1,
    data_backup_enabled INTEGER NOT NULL DEFAULT 0,
    data_backup_time TEXT DEFAULT '03:00',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 插入默认配置
INSERT OR IGNORE INTO system_config (system_name, login_timeout, log_retention_days, message_push_enabled, data_backup_enabled)
VALUES ('智能客服系统', 30, 90, 1, 0);