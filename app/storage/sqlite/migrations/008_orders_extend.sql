-- 008_orders_extend: 订单表扩展（售后状态 + 用户ID）
ALTER TABLE orders ADD COLUMN after_sales_status TEXT DEFAULT '';
ALTER TABLE orders ADD COLUMN user_id TEXT DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_orders_after_sales ON orders(after_sales_status);