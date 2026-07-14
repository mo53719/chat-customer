import pytest

from app.tools.safety_tools import safety_check, SENSITIVE_WORDS


class TestSafetyCheck:
    @pytest.mark.asyncio
    async def test_clean_text_passes(self):
        result = await safety_check(None, text="你好，我想咨询一下产品")
        assert result.success is True
        assert result.data["safe"] is True

    @pytest.mark.asyncio
    async def test_sensitive_word_detected(self):
        result = await safety_check(None, text="购买毒品")
        assert result.success is False
        assert result.data["safe"] is False
        assert "毒品" in result.data["hit"]

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        result = await safety_check(None, text="FUCK")
        assert result.success is False
        assert result.data["safe"] is False

    @pytest.mark.asyncio
    async def test_multiple_sensitive_words(self):
        result = await safety_check(None, text="色情赌博")
        assert result.success is False
        assert len(result.data["hit"]) >= 2

    @pytest.mark.asyncio
    async def test_empty_text(self):
        result = await safety_check(None, text="")
        assert result.success is True
        assert result.data["safe"] is True

    @pytest.mark.asyncio
    async def test_sensitive_words_list_contains_expected(self):
        """验证内置敏感词列表包含预期词汇。"""
        assert "色情" in SENSITIVE_WORDS
        assert "赌博" in SENSITIVE_WORDS
        assert "毒品" in SENSITIVE_WORDS

    @pytest.mark.asyncio
    async def test_partial_match_in_context(self):
        """敏感词嵌在正常文本中也能检测到。"""
        result = await safety_check(None, text="你好我想买一把枪支")
        assert result.success is False
        assert "枪支" in result.data["hit"]