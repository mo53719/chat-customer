"""熔断器：连续失败开熔断，定时半开探测。"""
from __future__ import annotations

import time

from config.settings import settings
from app.logger import get_logger

_log = get_logger("llm.circuit")


class CircuitBreaker:
    """简易熔断器：closed -> open -> half_open -> closed。"""

    def __init__(self, fail_threshold: int = 5, recover_sec: int = 30):
        self.fail_threshold = fail_threshold
        self.recover_sec = recover_sec
        self._fail_count = 0
        self._opened_at: float | None = None
        self._state = "closed"

    @property
    def state(self) -> str:
        if self._state == "open" and self._opened_at is not None:
            if time.time() - self._opened_at >= self.recover_sec:
                self._state = "half_open"
                _log.warning("熔断器进入半开探测状态")
        return self._state

    def allow(self) -> bool:
        return self.state in ("closed", "half_open")

    def record_success(self) -> None:
        if self._state in ("open", "half_open"):
            _log.info("熔断器恢复")
        self._fail_count = 0
        self._state = "closed"
        self._opened_at = None

    def record_failure(self) -> None:
        self._fail_count += 1
        if self._state == "half_open" or self._fail_count >= self.fail_threshold:
            self._state = "open"
            self._opened_at = time.time()
            _log.error(
                f"熔断器开启（失败 {self._fail_count} 次），{self.recover_sec}s 后半开探测"
            )


llm_circuit = CircuitBreaker(
    fail_threshold=settings.CIRCUIT_FAIL_THRESHOLD,
    recover_sec=settings.CIRCUIT_RECOVER_SEC,
)
