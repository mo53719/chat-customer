"""记忆管理器：短期会话记忆（持久化到 messages 表）。"""
from __future__ import annotations

from typing import Any

from config.settings import settings
from app.logger import get_logger
from app.storage.sqlite.repositories.session_repo import message_repo
from app.storage.sqlite.models import MessageDTO
from .window import trim_by_tokens, count_tokens

_log = get_logger("memory.manager")


class MemoryManager:
    """短期会话记忆：读写多轮对话历史。"""

    @staticmethod
    async def load_history(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """从 DB 加载历史消息，转为 LLM messages 格式。"""
        msgs = await message_repo.list_by_session(session_id, limit=limit)
        out: list[dict[str, Any]] = []
        for m in msgs:
            if m.role in ("user", "assistant", "system"):
                out.append({"role": m.role, "content": m.content})
        return out

    @staticmethod
    async def append_message(msg: MessageDTO) -> int:
        """持久化单条消息。"""
        return await message_repo.create(msg)

    @staticmethod
    def build_context(history: list[dict], system_prompt: str,
                      user_input: str,
                      examples: list[dict] | None = None) -> list[dict]:
        """组装最终喂给 LLM 的 messages。

        组装顺序：system(提示词) -> few-shot 示例 -> 历史(滑动窗口) -> 当前 user。
        """
        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        if examples:
            for ex in examples:
                messages.append({"role": "user", "content": ex.get("question", "")})
                messages.append({"role": "assistant", "content": ex.get("answer", "")})

        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        return trim_by_tokens(messages)

    @staticmethod
    def estimate_tokens(messages: list[dict]) -> int:
        return sum(count_tokens(m.get("content", "")) for m in messages)


memory_manager = MemoryManager()
