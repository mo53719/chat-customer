import asyncio
from copy import deepcopy
from types import SimpleNamespace

from app.agents.base import run_business_agent
from app.agents.state import AgentState


class _FakeResp:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.prompt_tokens = 1
        self.completion_tokens = 1


def test_run_business_agent_appends_tool_call_id(monkeypatch):
    calls: list[dict] = []

    async def fake_load_prompt(agent_name):
        return "system prompt"

    async def fake_chat(messages, **kwargs):
        calls.append({"messages": deepcopy(messages), "kwargs": kwargs})
        if len(calls) == 1:
            return _FakeResp(
                content="",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "rag_search", "arguments": '{"query":"退款规则"}'},
                }],
            )
        return _FakeResp(content="最终回答")

    async def fake_list_good(agent_name, limit=3):
        return []

    async def fake_tool(state, **kwargs):
        return SimpleNamespace(success=True, data=[{"text": "命中文档"}], error=None)

    monkeypatch.setattr("app.agents.base.load_prompt", fake_load_prompt)
    monkeypatch.setattr("app.agents.base.chat", fake_chat)
    monkeypatch.setattr("app.agents.base.get_tool", lambda name: SimpleNamespace(func=fake_tool))
    monkeypatch.setattr("app.agents.base.to_openai_tools", lambda: [{"function": {"name": "rag_search"}}])
    monkeypatch.setattr("app.agents.base.example_store.list_good", fake_list_good)
    monkeypatch.setattr(
        "app.agents.base.memory_manager.build_context",
        lambda **kwargs: [{"role": "system", "content": "system prompt"}, {"role": "user", "content": "你好"}],
    )

    state = AgentState(user_input="你好")
    result = asyncio.run(run_business_agent(state, "rag", ["rag_search"]))

    assert result.final_answer == "最终回答"
    tool_message = calls[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call_1"
    assert tool_message["name"] == "rag_search"
