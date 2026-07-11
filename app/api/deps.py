"""API 依赖注入：当前用户 / API Key 鉴权。"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Header, HTTPException, status

from config.settings import settings
from app.security.auth import decode_token
from app.security.api_key import validate_api_key
from app.security.rate_limit import rate_limiter
from app.storage.sqlite.repositories.user_repo import user_repo
from app.storage.sqlite.repositories.log_repo import log_repo


async def get_current_user(authorization: str | None = Header(None)) -> dict[str, Any]:
    """JWT 鉴权依赖。返回 {user_id, username, role}。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "缺少认证信息")
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "认证无效或已过期")
    user = await user_repo.get_by_id(int(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不可用")
    return {"user_id": user.id, "username": user.username, "role": user.role}


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user


async def get_api_key_user(x_api_key: str | None = Header(None, alias=settings.API_KEY_HEADER)) -> dict[str, Any]:
    """对外开放 API 的 Key 鉴权 + 限流。"""
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "缺少 API Key")
    rec = await validate_api_key(x_api_key)
    if not rec:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API Key 无效")
    if not rate_limiter.allow(x_api_key, rec.get("rate_limit_per_minute")):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "请求过于频繁")
    return {"api_key": x_api_key, "key_id": rec["id"], "user_id": rec.get("user_id")}


async def log_api_call(request_info: dict, user_info: dict, status_code: int,
                       latency_ms: int) -> None:
    await log_repo.insert_api_call(
        api_key=user_info.get("api_key"),
        endpoint=request_info.get("endpoint"),
        method=request_info.get("method"),
        status_code=status_code, latency_ms=latency_ms,
        ip=request_info.get("ip"),
        trace_id=request_info.get("trace_id"),
    )
