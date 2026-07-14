import time

import pytest

from app.llm.circuit_breaker import CircuitBreaker


class TestCircuitBreakerInit:
    def test_default_values(self):
        cb = CircuitBreaker()
        assert cb.fail_threshold == 5
        assert cb.recover_sec == 30
        assert cb.state == "closed"

    def test_custom_values(self):
        cb = CircuitBreaker(fail_threshold=3, recover_sec=10)
        assert cb.fail_threshold == 3
        assert cb.recover_sec == 10

    def test_allow_when_closed(self):
        cb = CircuitBreaker()
        assert cb.allow() is True

    def test_allow_when_half_open(self):
        cb = CircuitBreaker()
        cb._state = "half_open"
        assert cb.allow() is True


class TestCircuitBreakerStateTransitions:
    def test_record_failure_opens_after_threshold(self):
        cb = CircuitBreaker(fail_threshold=3, recover_sec=60)
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"
        assert cb.allow() is False

    def test_open_stays_open_before_recovery(self):
        cb = CircuitBreaker(fail_threshold=1, recover_sec=60)
        cb.record_failure()
        assert cb.state == "open"
        assert cb.allow() is False

    def test_half_open_after_recovery_time(self, monkeypatch):
        cb = CircuitBreaker(fail_threshold=1, recover_sec=1)
        cb.record_failure()
        assert cb.state == "open"

        # 模拟时间前进 2 秒
        fake_now = time.time() + 2
        monkeypatch.setattr(time, "time", lambda: fake_now)

        assert cb.state == "half_open"
        assert cb.allow() is True

    def test_record_success_resets_to_closed(self):
        cb = CircuitBreaker(fail_threshold=1, recover_sec=60)
        cb.record_failure()
        assert cb.state == "open"
        cb.record_success()
        assert cb.state == "closed"
        assert cb.allow() is True

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(fail_threshold=1, recover_sec=1)
        cb.record_failure()
        # 模拟时间前进进入半开
        cb._opened_at = time.time() - 2
        assert cb.state == "half_open"
        cb.record_failure()
        assert cb.state == "open"

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(fail_threshold=1, recover_sec=1)
        cb.record_failure()
        cb._opened_at = time.time() - 2
        assert cb.state == "half_open"
        cb.record_success()
        assert cb.state == "closed"

    def test_multiple_failures_keep_counting(self):
        cb = CircuitBreaker(fail_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"

    def test_half_open_failure_before_threshold(self):
        """半开状态下即使未达 fail_threshold 也开熔断。"""
        cb = CircuitBreaker(fail_threshold=5, recover_sec=1)
        # 先手动设为 open 并让时间过期，进入 half_open
        cb._state = "open"
        cb._opened_at = time.time() - 2
        assert cb.state == "half_open"
        cb.record_failure()
        assert cb.state == "open"