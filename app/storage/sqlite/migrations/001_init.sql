-- =====================================================================
-- 智能客服系统 SQLite 完整建表语句 v1.0
-- 涵盖：用户/订单/会话/消息/日志/知识库/提示词版本/反馈/示例/偏好/回收站/工具调用
-- 所有表均带 created_at / updated_at / 软删字段，支持一键回溯
-- =====================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ----------------------------- 用户与鉴权 -----------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    nickname TEXT,
    email TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 外部 API 调用密钥
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_value TEXT NOT NULL UNIQUE,
    name TEXT,
    user_id INTEGER,
    rate_limit_per_minute INTEGER DEFAULT 60,
    status TEXT NOT NULL DEFAULT 'active',
    last_used_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_api_keys_value ON api_keys(key_value);

-- ----------------------------- 业务数据 -----------------------------
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_no TEXT UNIQUE,
    nickname TEXT,
    phone TEXT,
    email TEXT,
    preferences TEXT,  -- JSON：用户习惯偏好
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT
);

-- 商品分类（支持层级）
CREATE TABLE IF NOT EXISTS product_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (parent_id) REFERENCES product_categories(id)
);
CREATE INDEX IF NOT EXISTS idx_product_categories_parent ON product_categories(parent_id);

-- 商品主表（售前 Agent + 知识库共用）
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,              -- 商品编号
    name TEXT NOT NULL,                    -- 商品名称
    category_id INTEGER,                   -- 一级分类
    brand TEXT,                            -- 品牌
    model TEXT,                            -- 型号
    price REAL NOT NULL,                   -- 售价
    original_price REAL,                   -- 原价
    stock INTEGER DEFAULT 0,               -- 库存
    sales_count INTEGER DEFAULT 0,         -- 销量
    specs TEXT,                            -- JSON：参数键值对 {"颜色":"星空黑","内存":"256G"}
    highlights TEXT,                       -- 卖点（短）
    description TEXT,                      -- 详细描述（长，喂给 RAG）
    package_contents TEXT,                 -- 包装清单
    warranty TEXT,                         -- 保修政策
    image_url TEXT,                        -- 主图
    tags TEXT,                             -- 标签 JSON ["新品","爆款","限时"]
    status TEXT NOT NULL DEFAULT 'on_sale'
        CHECK (status IN ('on_sale','off_sale','pre_sale','out_of_stock')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (category_id) REFERENCES product_categories(id)
);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);

-- 订单主表（保留 product_name 兼容旧数据）
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER,
    product_name TEXT,                     -- 兼容旧数据；新订单通过 order_items 关联
    total_amount REAL DEFAULT 0,           -- 多商品时为汇总金额
    amount REAL,                           -- 兼容旧字段（同 total_amount）
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','paid','shipped','delivered','returned','refunded','cancelled')),
    address TEXT,
    phone TEXT,
    remark TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_no ON orders(order_no);

-- 订单明细（支持多商品订单）
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,            -- 冗余存商品名（即使商品下架也能显示）
    product_sku TEXT,                     -- 冗余存 SKU
    unit_price REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    subtotal REAL NOT NULL,                -- unit_price * quantity
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

-- 售后/退货申请表（售前/售后 Agent 都要用）
CREATE TABLE IF NOT EXISTS after_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_no TEXT NOT NULL UNIQUE,
    order_id INTEGER NOT NULL,
    customer_id INTEGER,
    type TEXT NOT NULL CHECK (type IN ('return','exchange','refund','repair','complaint')),
    reason TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','processing','approved','rejected','completed')),
    handler TEXT,
    resolution TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    deleted_at TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
CREATE INDEX IF NOT EXISTS idx_after_sales_order ON after_sales(order_id);
CREATE INDEX IF NOT EXISTS idx_after_sales_status ON after_sales(status);

-- ----------------------------- 会话与消息 -----------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    user_id INTEGER,
    customer_id INTEGER,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed','transferred')),
    channel TEXT DEFAULT 'web',  -- web / miniapp / wework
    intent_summary TEXT,         -- 本次会话主要意图
    transferred_to_human INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    closed_at TEXT,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
    content TEXT NOT NULL,
    agent_name TEXT,             -- 哪个 Agent 产生
    intent TEXT,
    tool_calls TEXT,             -- JSON
    token_input INTEGER DEFAULT 0,
    token_output INTEGER DEFAULT 0,
    latency_ms INTEGER,
    trace_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

-- ----------------------------- 提示词版本管理 -----------------------------
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,          -- main / presales / aftersales / order / safety / rag
    version_no INTEGER NOT NULL,       -- 同 agent 内自增
    content TEXT NOT NULL,             -- 提示词全文
    change_note TEXT,                  -- 本次修改说明
    is_active INTEGER NOT NULL DEFAULT 0,  -- 是否当前启用
    auto_generated INTEGER NOT NULL DEFAULT 0,  -- 是否自动优化生成
    source_feedback_id INTEGER,        -- 由哪条反馈触发自动优化
    created_by TEXT,                   -- 用户名 / system
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    UNIQUE (agent_name, version_no)
);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_agent ON prompt_versions(agent_name);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_active ON prompt_versions(is_active);

-- ----------------------------- 反馈与自优化 -----------------------------
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    session_id TEXT,
    user_id INTEGER,
    rating TEXT NOT NULL CHECK (rating IN ('good','bad')),
    comment TEXT,                      -- 用户填写的反馈文字
    question TEXT,                     -- 原问题
    answer TEXT,                       -- 原回答
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);

CREATE TABLE IF NOT EXISTS feedback_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER NOT NULL,
    category TEXT,                     -- 不合格分类
    reason TEXT,                       -- 详细说明
    suggestion TEXT,                   -- 改进建议
    optimized_prompt_version_id INTEGER,  -- 触发自动优化生成的版本
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (feedback_id) REFERENCES feedback(id),
    FOREIGN KEY (optimized_prompt_version_id) REFERENCES prompt_versions(id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_analysis_feedback ON feedback_analysis(feedback_id);

-- 优质 / 差评示例库（few-shot 注入）
CREATE TABLE IF NOT EXISTS examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    tag TEXT NOT NULL CHECK (tag IN ('good','bad')),  -- good=优质回答示例；bad=差评规避示例
    source_feedback_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (source_feedback_id) REFERENCES feedback(id)
);

CREATE INDEX IF NOT EXISTS idx_examples_agent ON examples(agent_name);
CREATE INDEX IF NOT EXISTS idx_examples_tag ON examples(tag);

-- ----------------------------- 知识库元数据 -----------------------------
CREATE TABLE IF NOT EXISTS knowledge_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL UNIQUE,       -- 业务文档 id
    title TEXT,
    source TEXT,                       -- 文件名 / 来源
    file_type TEXT,                    -- md / txt / pdf / url
    chunk_count INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'processing'
        CHECK (status IN ('processing','ready','failed','deleted')),
    uploaded_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_knowledge_meta_status ON knowledge_meta(status);

-- ----------------------------- 日志与运维 -----------------------------
CREATE TABLE IF NOT EXISTS run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    module TEXT,
    trace_id TEXT,
    extra TEXT,                        -- JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_run_logs_level ON run_logs(level);
CREATE INDEX IF NOT EXISTS idx_run_logs_trace ON run_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_run_logs_created ON run_logs(created_at);

CREATE TABLE IF NOT EXISTS tool_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    session_id TEXT,
    tool_name TEXT NOT NULL,
    agent_name TEXT,
    input TEXT,                        -- JSON
    output TEXT,                       -- JSON
    success INTEGER NOT NULL DEFAULT 1,
    error TEXT,
    latency_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tool_call_logs_tool ON tool_call_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_call_logs_session ON tool_call_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_call_logs_created ON tool_call_logs(created_at);

CREATE TABLE IF NOT EXISTS api_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key TEXT,
    endpoint TEXT,
    method TEXT,
    status_code INTEGER,
    latency_ms INTEGER,
    ip TEXT,
    trace_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_api_call_logs_key ON api_call_logs(api_key);
CREATE INDEX IF NOT EXISTS idx_api_call_logs_created ON api_call_logs(created_at);

CREATE TABLE IF NOT EXISTS token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    session_id TEXT,
    agent_name TEXT,
    model TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_token_usage_created ON token_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_agent ON token_usage(agent_name);

CREATE TABLE IF NOT EXISTS page_operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    page TEXT,
    action TEXT,
    payload TEXT,                      -- JSON
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_page_op_user ON page_operation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_page_op_created ON page_operation_logs(created_at);

-- ----------------------------- 软删回收站（一键回溯） -----------------------------
CREATE TABLE IF NOT EXISTS deleted_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    snapshot TEXT NOT NULL,            -- 删除前完整记录 JSON
    deleted_by TEXT,
    deleted_at TEXT NOT NULL DEFAULT (datetime('now')),
    restored_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_deleted_records_table ON deleted_records(table_name);
CREATE INDEX IF NOT EXISTS idx_deleted_records_deleted_at ON deleted_records(deleted_at);

-- ----------------------------- 每日统计（缓存加速看板） -----------------------------
CREATE TABLE IF NOT EXISTS stats_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_date TEXT NOT NULL,
    total_sessions INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    transferred_human INTEGER DEFAULT 0,
    complaints INTEGER DEFAULT 0,
    good_feedback INTEGER DEFAULT 0,
    bad_feedback INTEGER DEFAULT 0,
    avg_latency_ms REAL,
    UNIQUE (stat_date)
);

-- ----------------------------- 触发器：自动更新 updated_at -----------------------------
CREATE TRIGGER IF NOT EXISTS trg_users_updated
    AFTER UPDATE ON users FOR EACH ROW
    BEGIN
        UPDATE users SET updated_at = datetime('now') WHERE id = OLD.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_orders_updated
    AFTER UPDATE ON orders FOR EACH ROW
    BEGIN
        UPDATE orders SET updated_at = datetime('now') WHERE id = OLD.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_sessions_updated
    AFTER UPDATE ON sessions FOR EACH ROW
    BEGIN
        UPDATE sessions SET updated_at = datetime('now') WHERE id = OLD.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_knowledge_meta_updated
    AFTER UPDATE ON knowledge_meta FOR EACH ROW
    BEGIN
        UPDATE knowledge_meta SET updated_at = datetime('now') WHERE id = OLD.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_user_preferences_updated
    AFTER UPDATE ON user_preferences FOR EACH ROW
    BEGIN
        UPDATE user_preferences SET updated_at = datetime('now') WHERE id = OLD.id;
    END;
