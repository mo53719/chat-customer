-- 009_merchant_config: 商家设置
CREATE TABLE IF NOT EXISTS merchant_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_name TEXT NOT NULL DEFAULT '',
    shop_logo TEXT DEFAULT '',
    service_hours TEXT NOT NULL DEFAULT '09:00-18:00',
    auto_reply TEXT DEFAULT '',
    auto_reply_enabled INTEGER NOT NULL DEFAULT 1,
    support_contact TEXT DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 插入默认配置
INSERT OR IGNORE INTO merchant_config (shop_name, shop_logo, service_hours, auto_reply, support_contact)
VALUES ('智能客服商城', '', '09:00-18:00',
        '您好，欢迎咨询智能客服商城！\n\n当前时间为{当前时间}，我们的客服人员将在工作时间内尽快回复您。\n\n如需查询订单，请提供您的{订单号}。',
        '400-123-4567');