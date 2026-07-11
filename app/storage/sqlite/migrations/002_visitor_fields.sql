-- 002_add_visitor_fields.sql
-- 给 sessions 表增加访客属性（IP / 地区 / 最近活跃时间 / 最近消息预览）
-- 幂等：所有 ALTER 都用 IF NOT EXISTS 风格（SQLite 3.35+ 支持 IF NOT EXISTS on columns）

ALTER TABLE sessions ADD COLUMN visitor_ip TEXT;
ALTER TABLE sessions ADD COLUMN visitor_region TEXT;
ALTER TABLE sessions ADD COLUMN last_active_at TEXT;
ALTER TABLE sessions ADD COLUMN last_message_preview TEXT;

-- 用于「在线访客」快速过滤（最近 5 分钟有过消息）
CREATE INDEX IF NOT EXISTS idx_sessions_last_active_at
    ON sessions (last_active_at);
