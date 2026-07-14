import pytest
from types import SimpleNamespace

from app.llm.client import LLMClient, LLMResponse, LLMError


class TestLLMResponse:
    def test_defaults(self):
        r = LLMResponse(content="hello")
        assert r.content == "hello"
        assert r.tool_calls == []
        assert r.prompt_tokens == 0
        assert r.completion_tokens == 0

    def test_with_tool_calls(self):
        tc = [{"id": "call_1", "type": "function", "function": {"name": "test", "arguments": "{}"}}]
        r = LLMResponse(content="", tool_calls=tc, prompt_tokens=10, completion_tokens=5, model="gpt-4")
        assert r.tool_calls == tc
        assert r.prompt_tokens == 10
        assert r.completion_tokens == 5
        assert r.model == "gpt-4"


class TestLLMError:
    def test_creation(self):
        e = LLMError("something went wrong")
        assert str(e) == "something went wrong"
        assert isinstance(e, Exception)


class TestLLMClientBasics:
    def test_client_creates_without_error(self):
        client = LLMClient()
        assert client._clients == {}

    def test_get_client_caches(self):
        client = LLMClient()
        c1 = client._get_client(base_url="http://test:8080/v1", api_key="sk-test")
        c2 = client._get_client(base_url="http://test:8080/v1", api_key="sk-test")
        assert c1 is c2

    def test_get_client_different_keys(self):
        client = LLMClient()
        c1 = client._get_client(base_url="http://a:8080/v1", api_key="sk-a")
        c2 = client._get_client(base_url="http://b:8080/v1", api_key="sk-b")
        assert c1 is not c2


class TestLLMClientChatCircuitOpen:
    @pytest.mark.asyncio
    async def test_rejects_when_circuit_open(self, monkeypatch):
        from app.llm import circuit_breaker as cb_module

        client = LLMClient()
        # 模拟熔断器开启
        monkeypatch.setattr(cb_module.llm_circuit, "allow", lambda: False)

        with pytest.raises(LLMError, match="熔断器开启"):
            await client.chat(
                messages=[{"role": "user", "content": "hi"}],
            )


class TestLLMClientChatSuccess:
    @pytest.mark.asyncio
    async def test_chat_returns_response(self, monkeypatch):
        from app.llm import circuit_breaker as cb_module
        from app.llm.client import llm_client

        monkeypatch.setattr(cb_module.llm_circuit, "allow", lambda: True)
        monkeypatch.setattr(cb_module.llm_circuit, "record_success", lambda: None)
        monkeypatch.setattr(cb_module.llm_circuit, "record_failure", lambda: None)

        # 模拟 _resolve_config 返回空
        async def fake_resolve(agent_name):
            return {}
        monkeypatch.setattr(llm_client, "_resolve_config", fake_resolve)

        # 模拟 OpenAI chat.completions.create
        fake_choice = SimpleNamespace(
            message=SimpleNamespace(
                content="你好，有什么可以帮助你的？",
                tool_calls=None,
            ),
        )
        fake_resp = SimpleNamespace(
            choices=[fake_choice],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
        )

        async def fake_create(**kwargs):
            return fake_resp

        monkeypatch.setattr(llm_client._get_client("", ""), "chat", SimpleNamespace(
            completions=SimpleNamespace(create=fake_create)
        ))

        # 需要注入到 _get_client 返回的 client 上
        original_get = llm_client._get_client

        class FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    async def create(**kwargs):
                        return fake_resp

        monkeypatch.setattr(llm_client, "_get_client", lambda *a, **kw: FakeClient())

        result = await llm_client.chat(
            messages=[{"role": "user", "content": "你好"}],
        )
        assert result.content == "你好，有什么可以帮助你的？"
        assert result.prompt_tokens == 5
        assert result.completion_tokens == 3

    @pytest.mark.asyncio
    async def test_chat_failure_records_circuit_failure(self, monkeypatch):
        from app.llm import circuit_breaker as cb_module
        from app.llm.client import llm_client

        monkeypatch.setattr(cb_module.llm_circuit, "allow", lambda: True)
        failure_called = []
        monkeypatch.setattr(cb_module.llm_circuit, "record_failure", lambda: failure_called.append(1))
        monkeypatch.setattr(cb_module.llm_circuit, "record_success", lambda: None)

        async def fake_resolve(agent_name):
            return {}
        monkeypatch.setattr(llm_client, "_resolve_config", fake_resolve)

        class FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    async def create(**kwargs):
                        raise Exception("API timeout")

        monkeypatch.setattr(llm_client, "_get_client", lambda *a, **kw: FakeClient())

        with pytest.raises(LLMError, match="API timeout"):
            await llm_client.chat(
                messages=[{"role": "user", "content": "hi"}],
            )
        assert len(failure_called) == 1