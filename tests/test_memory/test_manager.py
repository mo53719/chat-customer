import pytest

from app.memory.manager import MemoryManager


class TestBuildContext:
    def test_basic_no_examples_no_history(self):
        result = MemoryManager.build_context(
            history=[],
            system_prompt="你是客服",
            user_input="你好",
        )
        assert result[0] == {"role": "system", "content": "你是客服"}
        assert result[-1] == {"role": "user", "content": "你好"}

    def test_with_examples(self):
        examples = [
            {"question": "怎么退款", "answer": "请提供订单号"},
            {"question": "多久到账", "answer": "3-5个工作日"},
        ]
        result = MemoryManager.build_context(
            history=[],
            system_prompt="你是客服",
            user_input="我要退款",
            examples=examples,
        )
        assert result[0] == {"role": "system", "content": "你是客服"}
        assert result[1] == {"role": "user", "content": "怎么退款"}
        assert result[2] == {"role": "assistant", "content": "请提供订单号"}
        assert result[3] == {"role": "user", "content": "多久到账"}
        assert result[4] == {"role": "assistant", "content": "3-5个工作日"}
        assert result[-1] == {"role": "user", "content": "我要退款"}

    def test_with_history(self):
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮助你的？"},
        ]
        result = MemoryManager.build_context(
            history=history,
            system_prompt="你是客服",
            user_input="退款",
        )
        assert result[0] == {"role": "system", "content": "你是客服"}
        assert result[1] == {"role": "user", "content": "你好"}
        assert result[2] == {"role": "assistant", "content": "你好，有什么可以帮助你的？"}
        assert result[-1] == {"role": "user", "content": "退款"}

    def test_with_both_examples_and_history(self):
        examples = [{"question": "Q", "answer": "A"}]
        history = [{"role": "user", "content": "历史消息"}]
        result = MemoryManager.build_context(
            history=history,
            system_prompt="你是客服",
            user_input="新消息",
            examples=examples,
        )
        assert result[0] == {"role": "system", "content": "你是客服"}
        assert result[1] == {"role": "user", "content": "Q"}
        assert result[2] == {"role": "assistant", "content": "A"}
        assert result[3] == {"role": "user", "content": "历史消息"}
        assert result[-1] == {"role": "user", "content": "新消息"}

    def test_empty_examples_ignored(self):
        result = MemoryManager.build_context(
            history=[],
            system_prompt="你是客服",
            user_input="Hi",
            examples=[],
        )
        assert len(result) == 2  # system + user
        assert result[-1] == {"role": "user", "content": "Hi"}

    def test_examples_none_ignored(self):
        result = MemoryManager.build_context(
            history=[],
            system_prompt="你是客服",
            user_input="Hi",
            examples=None,
        )
        assert len(result) == 2


class TestEstimateTokens:
    def test_returns_positive_integer(self):
        msgs = [{"content": "你好世界"}, {"content": "hello world"}]
        result = MemoryManager.estimate_tokens(msgs)
        assert isinstance(result, int)
        assert result > 0

    def test_empty_messages_returns_zero(self):
        assert MemoryManager.estimate_tokens([]) == 0

    def test_empty_content_returns_zero(self):
        msgs = [{"content": ""}]
        assert MemoryManager.estimate_tokens(msgs) == 0