"""测试 LLM 客户端格式自修复与 token 估算。"""
import pytest

from app.llm.formatter import repair_json, repair_output
from app.memory.window import count_tokens


def test_repair_json_clean():
    assert repair_json('{"a": 1}') == '{"a": 1}'


def test_repair_json_codeblock():
    text = '```json\n{"a": 1}\n```'
    assert repair_json(text) == '{"a": 1}'


def test_repair_json_with_commas():
    text = '{"a": 1, "b": 2,}'
    r = repair_json(text)
    assert r is not None
    import json
    assert json.loads(r)["a"] == 1


def test_repair_json_invalid():
    assert repair_json("not json at all") is None


def test_repair_output_removes_control_chars():
    assert repair_output("hello\x00world") == "helloworld"


def test_repair_output_collapses_blank_lines():
    assert repair_output("a\n\n\n\nb") == "a\n\nb"


def test_count_tokens_basic():
    assert count_tokens("hello") > 0
    assert count_tokens("") == 0
