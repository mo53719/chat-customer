"""表结构定义 / 数据类 DTO。

实际建表语句见 migrations/001_init.sql。
此处仅提供供上层使用的数据类，避免上层直接接触 SQL。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ProductCategoryDTO:
    id: int | None = None
    name: str = ""
    parent_id: int | None = None
    sort_order: int = 0


@dataclass
class ProductDTO:
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
        return asdict(self)


@dataclass
class OrderItemDTO:
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
    id: int | None = None
    username: str = ""
    role: str = "user"
    nickname: str | None = None
    email: str | None = None
    status: str = "active"
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrderDTO:
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
    id: int | None = None
    feedback_id: int | None = None
    category: str | None = None
    reason: str | None = None
    suggestion: str | None = None
    optimized_prompt_version_id: int | None = None
    created_at: str | None = None


@dataclass
class ExampleDTO:
    id: int | None = None
    agent_name: str | None = None
    question: str = ""
    answer: str = ""
    tag: str = "good"
    source_feedback_id: int | None = None
    created_at: str | None = None


@dataclass
class KnowledgeMetaDTO:
    id: int | None = None
    doc_id: str = ""
    title: str | None = None
    source: str | None = None
    file_type: str | None = None
    chunk_count: int = 0
    status: str = "processing"
    uploaded_by: str | None = None
    created_at: str | None = None


@dataclass
class DeletedRecordDTO:
    id: int | None = None
    table_name: str = ""
    record_id: int = 0
    snapshot: str = ""
    deleted_by: str | None = None
    deleted_at: str | None = None
    restored_at: str | None = None
