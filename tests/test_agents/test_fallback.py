import pytest

from app.agents.fallback import fallback_node, timeout_fallback
from app.agents.state import AgentState


class TestFallbackNode:
    @pytest.mark.asyncio
    async def test_sets_fallback_answer(self, monkeypatch):
        import app.agents.fallback as fb_module
        monkeypatch.setattr(fb_module.settings, "FALLBACK_TEXT", "抱歉，我无法处理您的请求。")

        state = AgentState(
            session_id="test-session",
            user_input="测试",
            error="LLM调用失败",
        )
        result = await fallback_node(state)
        assert result.final_answer == "抱歉，我无法处理您的请求。"
        assert result.current_agent == "fallback"

    @pytest.mark.asyncio
    async def test_no_error_defaults_to_unknown(self, monkeypatch):
        import app.agents.fallback as fb_module
        monkeypatch.setattr(fb_module.settings, "FALLBACK_TEXT", "兜底回复")

        state = AgentState(session_id="test-session")
        result = await fallback_node(state)
        assert result.final_answer == "兜底回复"
        assert result.current_agent == "fallback"


class TestTimeoutFallback:
    @pytest.mark.asyncio
    async def test_records_timeout_error(self, monkeypatch):
        import app.agents.fallback as fb_module
        monkeypatch.setattr(fb_module.settings, "FALLBACK_TEXT", "请求超时，请稍后重试。")

        state = AgentState(session_id="test-session")
        exc = TimeoutError("任务执行超时")
        result = await timeout_fallback(state, exc)
        assert "任务超时" in result.error
        assert result.final_answer == "请求超时，请稍后重试。"
        assert result.current_agent == "fallback"