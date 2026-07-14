"""表结构定义 / 数据类 DTO。

实际建表语句见 migrations/001_init.sql。
此处仅提供供上层使用的数据类，避免上层直接接触 SQL。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ProductCategoryDTO:
    """商品分类数据传输对象。"""
    id: int | None = None
    name: str = ""
    parent_id: int | None = None
    sort_order: int = 0


@dataclass
class ProductDTO:
    """商品主表数据传输对象，含 SKU、价格、库存、规格等字段。"""
    id: int | None = None
    sku: str = ""
    name: str = ""
    category_id: int | None = None
    brand: str | None = None
    model: str | None = None
    price: float = 0.0
    original_price: float | None = None
    stock: int = 0
    sales_count: int = 0
    specs: dict[str, Any] | None = None
    highlights: str | None = None
    description: str | None = None
    package_contents: str | None = None
    warranty: str | None = None
    image_url: str | None = None
    tags: list[str] | None = None
    status: str = "on_sale"
    category_name: str | None = None  # 联表查询时的冗余字段
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """将 DTO 转为字典。"""
        return asdict(self)


@dataclass
class OrderItemDTO:
    """订单明细数据传输对象。"""
    id: int | None = None
    order_id: int = 0
    product_id: int = 0
    product_name: str = ""
    product_sku: str | None = None
    unit_price: float = 0.0
    quantity: int = 1
    subtotal: float = 0.0


@dataclass
class AfterSalesDTO:
    """售后工单数据传输对象。"""
    id: int | None = None
    ticket_no: str = ""
    order_id: int = 0
    customer_id: int | None = None
    type: str = "return"
    reason: str | None = None
    description: str | None = None
    status: str = "pending"
    handler: str | None = None
    resolution: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


@dataclass
class UserDTO:
    """用户数据传输对象。"""
    id: int | None = None
    username: str = ""
    role: str = "user"
    nickname: str | None = None
    email: str | None = None
    status: str = "active"
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """将 DTO 转为字典。"""
        return asdict(self)


@dataclass
class OrderDTO:
    """订单主表数据传输对象。"""
    id: int | None = None
    order_no: str = ""
    customer_id: int | None = None
    product_name: str | None = None
    amount: float | None = None
    status: str = "pending"
    address: str | None = None
    phone: str | None = None
    created_at: str | None = None


@dataclass
class SessionDTO:
    """会话数据传输对象，含访客名片字段。"""
    id: int | None = None
    session_id: str = ""
    user_id: int | None = None
    customer_id: int | None = None
    title: str | None = None
    status: str = "active"
    channel: str = "web"
    intent_summary: str | None = None
    transferred_to_human: int = 0
    message_count: int = 0
    created_at: str | None = None
    closed_at: str | None = None
    # 访客相关（migration 002）
    visitor_ip: str | None = None
    visitor_region: str | None = None
    last_active_at: str | None = None
    last_message_preview: str | None = None
    # 访客名片（mock，后端未采集）
    device: str | None = None
    browser: str | None = None
    os_name: str | None = None
    language: str | None = None
    referrer: str | None = None
    visit_count: int = 1
    note: str | None = None


@dataclass
class MessageDTO:
    """消息数据传输对象，含 Token 和耗时统计。"""
    id: int | None = None
    session_id: str = ""
    role: str = "user"
    content: str = ""
    agent_name: str | None = None
    intent: str | None = None
    tool_calls: list[dict] | None = None
    token_input: int = 0
    token_output: int = 0
    latency_ms: int | None = None
    trace_id: str | None = None
    created_at: str | None = None


@dataclass
class PromptVersionDTO:
    """提示词版本数据传输对象。"""
    id: int | None = None
    agent_name: str = ""
    version_no: int = 0
    content: str = ""
    change_note: str | None = None
    is_active: int = 0
    auto_generated: int = 0
    source_feedback_id: int | None = None
    created_by: str | None = None
    created_at: str | None = None


@dataclass
class FeedbackDTO:
    """用户反馈数据传输对象。"""
    id: int | None = None
    message_id: int | None = None
    session_id: str | None = None
    user_id: int | None = None
    rating: str = ""
    comment: str | None = None
    question: str | None = None
    answer: str | None = None
    created_at: str | None = None


@dataclass
class FeedbackAnalysisDTO:
    """反馈分析结果数据传输对象。"""
    id: int | None = None
    feedback_id: int | None = None
    category: str | None = None
    reason: str | None = None
    suggestion: str | None = None
    optimized_prompt_version_id: int | None = None
    created_at: str | None = None


@dataclass
class ExampleDTO:
    """优质/差评示例数据传输对象。"""
    id: int | None = None
    agent_name: str | None = None
    question: str = ""
    answer: str = ""
    tag: str = "good"
    source_feedback_id: int | None = None
    created_at: str | None = None


@dataclass
class KnowledgeMetaDTO:
    """知识库文档元数据传输对象。"""
    id: int | None = None
    doc_id: str = ""
    title: str | None = None
    source: str | None = None
    file_type: str | None = None
    chunk_count: int = 0
    status: str = "processing"
    uploaded_by: str | None = None
    created_at: str | None = None
    # 可溯源字段
    file_hash: str | None = None
    parent_doc_id: str | None = None
    is_current: int = 1
    embedding_model: str | None = None
    embedding_version: str | None = None
    total_pages: int | None = None
    uploader_role: str | None = None
    tags: str | None = None
    doc_origin_url: str | None = None
    language: str | None = "zh"
    char_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DeletedRecordDTO:
    """回收站记录数据传输对象。"""
    id: int | None = None
    table_name: str = ""
    record_id: int = 0
    snapshot: str = ""
    deleted_by: str | None = None
    deleted_at: str | None = None
    restored_at: str | None = None


@dataclass
class BadcaseDTO:
    """失败案例数据传输对象，记录 review 不通过的回答。"""
    id: int | None = None
    session_id: str | None = None
    user_input: str = ""
    agent_answer: str | None = None
    intent: str | None = None
    agent_name: str | None = None
    failed_rules: list[str] | None = None
    review_details: list[dict] | None = None
    trace_id: str | None = None
    status: str = "new"
    note: str | None = None
    created_at: str | None = None
    reviewed_at: str | None = None
    reviewed_by: str | None = None
