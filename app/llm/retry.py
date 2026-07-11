"""自动重试：指数退避，区分可重试错误。"""
from __future__ import annotations

import asyncio
import functools
from typing import Awaitable, Callable, TypeVar

from config.settings import settings
from app.logger import get_logger

_log = get_logger("llm.retry")

T = TypeVar("T")

_RETRYABLE_MSG_KEYS = (
    "timeout", "timed out", "connection", "rate limit", "rate_limit",
    "429", "500", "502", "503", "504", "overloaded", "temporary",
)


def _is_retryable(err: Exception) -> bool:
    msg = str(err).lower()
    return any(k in msg for k in _RETRYABLE_MSG_KEYS)


async def with_retry(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int | None = None,
    backoff: float | None = None,
    **kwargs,
) -> T:
    """带指数退避的异步重试。"""
    retries = max_retries if max_retries is not None else settings.LLM_RETRY_MAX
    bk = backoff if backoff is not None else settings.LLM_RETRY_BACKOFF

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_err = e
            if not _is_retryable(e) or attempt == retries:
                raise
            wait = bk * (2 ** attempt)
            _log.warning(f"第 {attempt + 1} 次重试，{wait:.1f}s 后重试：{e}")
            await asyncio.sleep(wait)
    if last_err:
        raise last_err
    raise RuntimeError("with_retry: 未知错误")


def retryable(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """装饰器形式。"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        return await with_retry(func, *args, **kwargs)
    return wrapper
