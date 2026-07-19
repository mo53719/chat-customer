"""全局 Agent 状态定义：所有节点通过此数据类通信。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class Intent(str, Enum):
    PRESALES = "presales"
    AFTERSALES = "aftersales"
    ORDER = "order"
    RAG = "rag"
    SAFETY = "safety"
    FALLBACK = "fallback"


@dataclass
class AgentState:
    """LangGraph 节点间流转的标准化状态。"""
    # 会话标识
    session_id: str = ""
    user_id: int | None = None
    trace_id: str = ""

    # 输入
    user_input: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    # 意图
    intent: str = ""
    intent_confidence: float = 0.0
    needs_decomposition: bool = False

    # 当前 Agent
    current_agent: str = ""

    # 三层漏斗路由信息
    router_layer: str = ""  # "rule" | "semantic" | "llm"

    # 工具循环控制
    tool_calls_count: int = 0
    max_tool_rounds: int = 6
    tool_results: list[dict[str, Any]] = field(default_factory=list)

    # 业务 Agent 产出
    agent_messages: list[dict[str, Any]] = field(default_factory=list)

    # 最终输出
    final_answer: str = ""
    error: str | None = None

    # 是否需要 RAG 搜索（greeting/闲聊不需要）
    need_rag: bool = True

    # 预取 RAG 上下文（agent 层在调 LLM 前强制注入知识库内容）
    rag_context: str = ""

    # RAG 检索命中（用于前端溯源引用）
    rag_hits: list[dict[str, Any]] = field(default_factory=list)

    # few-shot 示例
    examples: list[dict[str, Any]] = field(default_factory=list)

    # reviewer 评分
    review_status: str = ""
    review_warnings: list[str] = field(default_factory=list)
    review_details: list[dict] = field(default_factory=list)

    # 元数据
    latency_ms: int | None = None
    token_input: int = 0
    token_output: int = 0

    def can_call_tool(self) -> bool:
        return self.tool_calls_count < self.max_tool_rounds

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "trace_id": self.trace_id,
            "intent": self.intent,
            "current_agent": self.current_agent,
            "tool_calls_count": self.tool_calls_count,
            "error": self.error,
        }

    def to_dict(self) -> dict[str, Any]:
        """全字段转 dict，供 LangGraph 在节点间传递。
        LangGraph 默认要求 state 是 TypedDict 或支持 dict 转换的 dataclass。"""
        from dataclasses import asdict
        return asdict(self)
