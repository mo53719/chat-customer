import pytest
from types import SimpleNamespace

from app.llm.embedding import embed_texts


class TestEmbedTexts:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self):
        result = await embed_texts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_circuit_open_rejects(self, monkeypatch):
        from app.llm import circuit_breaker as cb_module
        monkeypatch.setattr(cb_module.llm_circuit, "allow", lambda: False)

        with pytest.raises(RuntimeError, match="熔断器开启"):
            await embed_texts(["hello"])

    @pytest.mark.asyncio
    async def test_unknown_backend_raises(self, monkeypatch):
        from app.llm import circuit_breaker as cb_module
        monkeypatch.setattr(cb_module.llm_circuit, "allow", lambda: True)

        # 模拟未知 backend
        import app.llm.embedding as emb_module
        monkeypatch.setattr(emb_module.settings, "EMBEDDING_BACKEND", "unknown_backend_xyz")

        # 需要 mock circuit breaker 的 record_failure
        monkeypatch.setattr(cb_module.llm_circuit, "record_failure", lambda: None)
        monkeypatch.setattr(cb_module.llm_circuit, "record_success", lambda: None)

        with pytest.raises(ValueError, match="未知 EMBEDDING_BACKEND"):
            await embed_texts(["hello"])


class TestEmbedLocal:
    @pytest.mark.asyncio
    async def test_local_embedding_flow(self, monkeypatch):
        """模拟本地 embedding 完整流程。"""
        from app.llm import circuit_breaker as cb_module
        monkeypatch.setattr(cb_module.llm_circuit, "allow", lambda: True)
        monkeypatch.setattr(cb_module.llm_circuit, "record_success", lambda: None)
        monkeypatch.setattr(cb_module.llm_circuit, "record_failure", lambda: None)

        import app.llm.embedding as emb_module
        monkeypatch.setattr(emb_module.settings, "EMBEDDING_BACKEND", "local")
        monkeypatch.setattr(emb_module.settings, "EMBEDDING_NORMALIZE", False)

        # Mock _load_local_model 返回一个假模型
        class FakeModel:
            def embed(self, texts, batch_size=8, parallel=0):
                return [[0.1, 0.2, 0.3] for _ in texts]

        def fake_load():
            return FakeModel()

        monkeypatch.setattr(emb_module, "_load_local_model", fake_load)

        result = await emb_module._embed_local(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 3


class TestEmbedOpenai:
    @pytest.mark.asyncio
    async def test_openai_embedding_batch(self, monkeypatch):
        """模拟 OpenAI embedding 批量请求。"""
        from app.llm import circuit_breaker as cb_module
        monkeypatch.setattr(cb_module.llm_circuit, "allow", lambda: True)
        monkeypatch.setattr(cb_module.llm_circuit, "record_success", lambda: None)
        monkeypatch.setattr(cb_module.llm_circuit, "record_failure", lambda: None)

        import app.llm.embedding as emb_module
        monkeypatch.setattr(emb_module.settings, "EMBEDDING_BACKEND", "openai")
        monkeypatch.setattr(emb_module.settings, "EMBEDDING_MODEL", "text-embedding-v3")
        monkeypatch.setattr(emb_module.settings, "EMBEDDING_DIM", 512)

        class FakeEmbedding:
            def __init__(self, embedding):
                self.embedding = embedding

        class FakeData:
            def __init__(self, items):
                self.data = items

        async def fake_create(model, input, **kwargs):
            return FakeData([FakeEmbedding([0.1] * 512) for _ in input])

        class FakeEmbeddings:
            embeddings = SimpleNamespace(create=fake_create)

        class FakeClient:
            def __init__(self):
                self.embeddings = FakeEmbeddings().embeddings

        monkeypatch.setattr(emb_module, "_get_openai_client", lambda: FakeClient())

        result = await emb_module._embed_openai(["text1", "text2"])
        assert len(result) == 2
        assert len(result[0]) == 512


