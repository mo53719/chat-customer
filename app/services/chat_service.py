"""对话编排服务：接收请求 -> 调 agents graph -> 持久化 -> 返回。"""
from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from app.logger import get_logger
from app.logger.tracer import TraceContext, gen_trace_id
from app.storage.sqlite.repositories.session_repo import session_repo
from app.agents.graph import run_agent, run_agent_stream

_log = get_logger("services.chat")


# 简单 IP 区域猜测（仅覆盖内网/常见段，生产请接 GeoIP）
_REGION_RULES = [
    (r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|127\.)", "内网"),
    (r"^(36\.|39\.|42\.|49\.|58\.|59\.|60\.|61\.|101\.|103\.|110\.|111\.|112\.|113\.|114\.|115\.|116\.|117\.|118\.|119\.|120\.|121\.|122\.|123\.|124\.|125\.|126\.|175\.|180\.|182\.|183\.|202\.|203\.|210\.|211\.|218\.|219\.|220\.|221\.|222\.|223\.)", "中国"),
    (r"^(8\.|12\.|24\.|32\.|40\.|56\.|64\.|72\.|96\.|104\.|172\.|192\.|198\.|199\.|204\.|205\.|206\.|207\.|208\.)", "海外"),
]


def _guess_region(ip: str | None) -> str:
    import re
    if not ip:
        return "未知"
    for pattern, name in _REGION_RULES:
        if re.match(pattern, ip):
            return name
    return "未知"


class ChatService:
    @staticmethod
    async def ensure_session(session_id: str | None, user_id: int | None,
                             channel: str = "web",
                             visitor_ip: str | None = None) -> str:
        if session_id:
            existing = await session_repo.get(session_id)
            if existing:
                return session_id
        sid = session_id or f"sess_{uuid.uuid4().hex[:16]}"
        await session_repo.create(
            session_id=sid, user_id=user_id, title="新会话",
            channel=channel, visitor_ip=visitor_ip,
            visitor_region=_guess_region(visitor_ip),
        )
        return sid

    @staticmethod
    async def chat(session_id: str, message: str, user_id: int | None = None,
                   channel: str = "web", visitor_ip: str | None = None) -> dict[str, Any]:
        """同步对话。"""
        sid = await ChatService.ensure_session(session_id, user_id, channel, visitor_ip)
        result = await run_agent(message, sid, user_id=user_id)
        return {"session_id": sid, **result}

    @staticmethod
    async def chat_stream(session_id: str, message: str, user_id: int | None = None,
                          channel: str = "web",
                          visitor_ip: str | None = None) -> AsyncIterator[str]:
        """真流式对话：边生成边输出，用户立即看到打字效果。"""
        sid = await ChatService.ensure_session(session_id, user_id, channel, visitor_ip)
        async for chunk in run_agent_stream(message, sid, user_id=user_id):
            yield chunk


chat_service = ChatService()
