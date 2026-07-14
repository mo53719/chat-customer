import asyncio

import pytest

from app.llm.retry import _is_retryable, with_retry


class TestIsRetryable:
    def test_timeout(self):
        assert _is_retryable(Exception("request timed out")) is True

    def test_rate_limit(self):
        assert _is_retryable(Exception("rate limit exceeded")) is True

    def test_http_429(self):
        assert _is_retryable(Exception("HTTP 429")) is True

    def test_http_500(self):
        assert _is_retryable(Exception("server error 500")) is True

    def test_http_502(self):
        assert _is_retryable(Exception("bad gateway 502")) is True

    def test_http_503(self):
        assert _is_retryable(Exception("service unavailable 503")) is True

    def test_http_504(self):
        assert _is_retryable(Exception("gateway timeout 504")) is True

    def test_connection_error(self):
        assert _is_retryable(Exception("connection refused")) is True

    def test_overloaded(self):
        assert _is_retryable(Exception("server overloaded")) is True

    def test_temporary_error(self):
        assert _is_retryable(Exception("temporary failure")) is True

    def test_non_retryable(self):
        assert _is_retryable(Exception("invalid api key")) is False

    def test_validation_error(self):
        assert _is_retryable(ValueError("bad input")) is False

    def test_empty_message(self):
        assert _is_retryable(Exception("")) is False


class TestWithRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        call_count = 0

        async def ok():
            nonlocal call_count
            call_count += 1
            return "done"

        result = await with_retry(ok, max_retries=3, backoff=0.01)
        assert result == "done"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("timeout error")
            return "ok"

        result = await with_retry(flaky, max_retries=3, backoff=0.01)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_error(self):
        call_count = 0

        async def bad():
            nonlocal call_count
            call_count += 1
            raise ValueError("invalid input")

        with pytest.raises(ValueError, match="invalid input"):
            await with_retry(bad, max_retries=3, backoff=0.01)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("timeout")

        with pytest.raises(Exception, match="timeout"):
            await with_retry(always_fail, max_retries=2, backoff=0.01)
        assert call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_uses_exponential_backoff(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("timeout")
            return "ok"

        result = await with_retry(flaky, max_retries=2, backoff=0.01)
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_zero_retries(self):
        call_count = 0

        async def fail():
            nonlocal call_count
            call_count += 1
            raise Exception("timeout")

        with pytest.raises(Exception, match="timeout"):
            await with_retry(fail, max_retries=0, backoff=0.01)
        assert call_count == 1