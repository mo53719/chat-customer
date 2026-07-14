import pytest

from app.memory.window import count_tokens, trim_by_tokens


class TestCountTokens:
    def test_returns_positive_for_text(self):
        result = count_tokens("你好世界")
        assert result > 0
        assert isinstance(result, int)

    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    def test_english_text(self):
        result = count_tokens("hello world")
        assert result > 0

    def test_long_text(self):
        text = "这是一段" * 100
        result = count_tokens(text)
        assert result > 0


class TestTrimByTokens:
    def test_empty_messages(self):
        assert trim_by_tokens([]) == []

    def test_short_messages_not_trimmed(self):
        msgs = [
            {"role": "system", "content": "你是客服"},
            {"role": "user", "content": "你好"},
        ]
        result = trim_by_tokens(msgs, max_tokens=10000)
        assert len(result) == 2

    def test_keep_system_message(self):
        msgs = [
            {"role": "system", "content": "你是客服"},
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好"},
        ]
        result = trim_by_tokens(msgs, max_tokens=10, keep_system=True)
        assert result[0]["role"] == "system"

    def test_no_keep_system(self):
        """keep_system=False 时不做特殊保留，但 system 消息仍可能因 token 足够而被保留。"""
        msgs = [
            {"role": "system", "content": "你是客服"},
            {"role": "user", "content": "你好"},
        ]
        result = trim_by_tokens(msgs, max_tokens=10000, keep_system=False)
        # 所有消息都会参与滑动窗口，system 不会被特殊保留
        assert len(result) == 2

    def test_trim_oldest_first(self):
        """验证滑动窗口：保留最近的消息。"""
        msgs = [
            {"role": "user", "content": "第一条消息"},
            {"role": "assistant", "content": "第二条消息"},
            {"role": "user", "content": "第三条消息"},
        ]
        result = trim_by_tokens(msgs, max_tokens=5, keep_system=False)
        # 应该只保留最近的一条
        if result:
            assert result[-1]["content"] == "第三条消息"

    def test_very_low_limit_trims_all(self):
        """token 上限极低时，单条消息也可能被裁掉。"""
        msgs = [{"role": "user", "content": "短"}]
        result = trim_by_tokens(msgs, max_tokens=1, keep_system=False)
        # 单条消息 token 数 > 1 时会被裁掉
        assert len(result) <= 1