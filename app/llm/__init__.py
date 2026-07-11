"""LLM 推理层：统一封装 LLM 调用入口，供所有 Agent 使用。

特性：
- OpenAI 兼容协议（GLM / Qwen / DeepSeek / OpenAI 等）
- 熔断器 + 自动重试
- 输出格式自修复
- Token 用量记录入库
"""
from .client import LLMClient, llm_client, chat, chat_stream
from .embedding import embed_texts
from .circuit_breaker import llm_circuit
from .retry import with_retry
from .formatter import repair_json, repair_output

__all__ = [
    "LLMClient", "llm_client", "chat", "chat_stream",
    "embed_texts", "llm_circuit", "with_retry",
    "repair_json", "repair_output",
]
