"""限流：基于内存令牌桶，按 API Key / 用户维度限流。"""
from __future__ import annotations

import time
from collections import defaultdict

from config.settings import settings


class RateLimiter:
    """简单滑动窗口限流（按分钟）。"""

    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._default_limit = settings.RATE_LIMIT_PER_MINUTE

    def allow(self, key: str, limit: int | None = None) -> bool:
        lim = limit or self._default_limit
        now = time.time()
        window = 60.0
        bucket = self._buckets[key]
        # 清理过期
        self._buckets[key] = [t for t in bucket if now - t < window]
        if len(self._buckets[key]) >= lim:
            return False
        self._buckets[key].append(now)
        return True


rate_limiter = RateLimiter()
