"""API Key 鉴权（对外开放接口）。"""
from __future__ import annotations

from app.storage.sqlite.repositories.user_repo import api_key_repo


async def validate_api_key(key_value: str) -> dict | None:
    """校验 API Key，返回 key 记录或 None。"""
    if not key_value:
        return None
    rec = await api_key_repo.get_by_key(key_value)
    if rec:
        await api_key_repo.touch_last_used(key_value)
    return rec
