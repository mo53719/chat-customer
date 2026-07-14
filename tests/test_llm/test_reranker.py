import pytest

from app.llm.reranker import rerank


class TestRerank:
    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty(self):
        result = await rerank("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_disabled_returns_original(self, monkeypatch):
        import app.llm.reranker as rk_module
        monkeypatch.setattr(rk_module.settings, "RERANK_ENABLED", False)

        candidates = [
            {"text": "doc1", "score": 0.9},
            {"text": "doc2", "score": 0.8},
            {"text": "doc3", "score": 0.7},
        ]
        result = await rerank("query", candidates, top_k=2)
        assert len(result) == 2
        assert result[0]["text"] == "doc1"

    @pytest.mark.asyncio
    async def test_fewer_candidates_than_top_k(self, monkeypatch):
        import app.llm.reranker as rk_module
        monkeypatch.setattr(rk_module.settings, "RERANK_ENABLED", True)
        monkeypatch.setattr(rk_module.settings, "RERANK_FINAL_K", 5)

        candidates = [{"text": "doc1"}, {"text": "doc2"}]
        result = await rerank("query", candidates, top_k=5)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_rerank_error_falls_back(self, monkeypatch):
        """rerank 出错时降级返回原序前 top_k。"""
        import app.llm.reranker as rk_module
        monkeypatch.setattr(rk_module.settings, "RERANK_ENABLED", True)
        monkeypatch.setattr(rk_module.settings, "RERANK_FINAL_K", 3)

        def fake_load():
            raise RuntimeError("model load failed")

        monkeypatch.setattr(rk_module, "_load_model", fake_load)

        candidates = [
            {"text": "doc1"},
            {"text": "doc2"},
            {"text": "doc3"},
            {"text": "doc4"},
        ]
        result = await rerank("query", candidates, top_k=2)
        assert len(result) == 2
        assert result[0]["text"] == "doc1"

    @pytest.mark.asyncio
    async def test_rerank_success(self, monkeypatch):
        """正常 rerank 流程。"""
        import app.llm.reranker as rk_module
        monkeypatch.setattr(rk_module.settings, "RERANK_ENABLED", True)
        monkeypatch.setattr(rk_module.settings, "RERANK_FINAL_K", 3)

        class FakeModel:
            def rerank(self, query, documents):
                return [0.5, 0.9, 0.3, 0.7]

        monkeypatch.setattr(rk_module, "_load_model", lambda: FakeModel())

        candidates = [
            {"text": "doc1"},
            {"text": "doc2"},
            {"text": "doc3"},
            {"text": "doc4"},
        ]
        result = await rerank("query", candidates, top_k=2)
        assert len(result) == 2
        # doc2 得分最高 (0.9)，应该排第一
        assert result[0]["text"] == "doc2"
        assert "rerank_score" in result[0]