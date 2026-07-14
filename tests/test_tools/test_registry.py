import pytest

from app.tools.registry import ToolResult, ToolSpec, get_tool, list_tools, to_openai_tools, _REGISTRY


class TestToolResult:
    def test_default_success(self):
        r = ToolResult()
        assert r.success is True
        assert r.data is None
        assert r.error is None
        assert r.meta == {}

    def test_failure(self):
        r = ToolResult(success=False, error="出错了")
        assert r.success is False
        assert r.error == "出错了"

    def test_with_data(self):
        r = ToolResult(data={"name": "test"}, meta={"count": 1})
        assert r.data == {"name": "test"}
        assert r.meta["count"] == 1


class TestGetTool:
    def test_existing_tool(self):
        spec = _REGISTRY.get("rag_search")
        if spec:
            result = get_tool("rag_search")
            assert result is not None
            assert result.name == "rag_search"

    def test_missing_tool(self):
        assert get_tool("nonexistent_tool") is None


class TestListTools:
    def test_returns_list(self):
        tools = list_tools()
        assert isinstance(tools, list)
        for t in tools:
            assert isinstance(t, ToolSpec)


class TestToOpenaiTools:
    def test_returns_correct_format(self):
        result = to_openai_tools()
        assert isinstance(result, list)
        for item in result:
            assert item["type"] == "function"
            assert "function" in item
            assert "name" in item["function"]
            assert "description" in item["function"]
            assert "parameters" in item["function"]