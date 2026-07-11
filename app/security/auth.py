"""JWT 鉴权 + 密码哈希。"""
from __future__ import annotations

import datetime as dt
from typing import Any

import jwt
from passlib.context import CryptContext

from config.settings import settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd_ctx.verify(password, password_hash)
    except Exception:
        return False


def create_token(user_id: int, username: str, role: str,
                 expires_hours: int | None = None) -> str:
    exp = dt.datetime.now(dt.UTC) + dt.timedelta(hours=expires_hours or settings.JWT_EXPIRE_HOURS)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": exp,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        return None
