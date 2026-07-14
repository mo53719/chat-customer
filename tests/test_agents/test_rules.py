import pytest

from app.agents.reviewer.rules import (
    check_empty, check_harmful, check_deflection, check_on_topic, ReviewResult
)


class TestCheckEmpty:
    def test_empty_string(self):
        r = check_empty("")
        assert r.passed is False
        assert r.rule == "empty"
        assert r.severity == "fail"

    def test_whitespace_only(self):
        r = check_empty("   ")
        assert r.passed is False

    def test_too_short(self):
        r = check_empty("a")
        assert r.passed is False

    def test_valid_answer(self):
        r = check_empty("这是有效的回答")
        assert r.passed is True


class TestCheckHarmful:
    def test_clean_answer(self):
        r = check_harmful("正常回答")
        assert r.passed is True

    def test_no_blocked_words_configured(self):
        """未配置违禁词时默认通过。"""
        r = check_harmful("任何内容")
        assert r.passed is True


class TestCheckDeflection:
    def test_clean_answer(self):
        r = check_deflection("根据您的订单，我们将在3天内发货")
        assert r.passed is True

    def test_deflection_phrase_detected(self):
        r = check_deflection("请咨询人工客服处理")
        assert r.passed is False
        assert r.rule == "deflection"

    def test_cannot_answer(self):
        r = check_deflection("我无法回答这个问题")
        assert r.passed is False

    def test_contact_customer_service(self):
        r = check_deflection("请联系客服")
        assert r.passed is False

    def test_no_sales(self):
        r = check_deflection("暂时没有相关销售")
        assert r.passed is False

    def test_not_provided(self):
        r = check_deflection("我们平台暂时不提供该服务")
        assert r.passed is False


class TestCheckOnTopic:
    def test_high_overlap(self):
        r = check_on_topic("退款流程很简单，请提供订单号", "退款流程")
        assert r.passed is True

    def test_low_overlap(self):
        r = check_on_topic("这是其他内容", "退款流程怎么操作")
        assert r.passed is False
        assert r.rule == "off_topic"

    def test_no_chinese_words_in_question(self):
        """问题中没有中文词时跳过检查。"""
        r = check_on_topic("答案", "ok")
        assert r.passed is True

    def test_exact_match(self):
        r = check_on_topic("退款流程", "退款流程")
        assert r.passed is True