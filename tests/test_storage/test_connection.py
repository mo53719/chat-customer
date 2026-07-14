import pytest

from app.storage.sqlite.connection import json_dumps, json_loads


class TestJsonDumps:
    def test_simple_dict(self):
        result = json_dumps({"a": 1, "b": "你好"})
        assert '"a"' in result
        assert '"b"' in result
        assert "你好" in result

    def test_list(self):
        result = json_dumps([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_none_value(self):
        result = json_dumps({"x": None})
        assert "null" in result


class TestJsonLoads:
    def test_valid_json(self):
        result = json_loads('{"a": 1}')
        assert result == {"a": 1}

    def test_none_input(self):
        assert json_loads(None) is None

    def test_empty_string(self):
        assert json_loads("") is None

    def test_invalid_json(self):
        result = json_loads("not json")
        assert result is None