import asyncio

import pytest

from app.storage.qdrant.retriever import Retriever


class _FakeHit:
    def __init__(self, score: float, text: str):
        self.score = score
        self.payload = {
            "doc_id": "doc-1",
            "title": "标题",
            "chunk_idx": 0,
            "text": text,
            "source": "kb.md",
            "sheet": None,
            "row": None,
            "heading_path": "标题",
        }


class _FakeClient:
    def __init__(self):
        self.calls: list[dict] = []

    async def search(self, **kwargs):
        self.calls.append(kwargs)
        return [_FakeHit(0.31, "A"), _FakeHit(0.27, "B")]


def test_retriever_skips_vector_threshold_when_rerank_enabled(monkeypatch):
    client = _FakeClient()

    async def fake_embed_texts(texts):
        return [[0.1, 0.2]]

    async def fake_rerank(query, candidates, top_k=None):
        out = []
        for idx, item in enumerate(candidates[: top_k or len(candidates)]):
            item = dict(item)
            item["rerank_score"] = 0.9 - idx * 0.1
            out.append(item)
        return out

    monkeypatch.setattr("app.storage.qdrant.retriever.get_qdrant", lambda: client)
    monkeypatch.setattr("app.llm.embedding.embed_texts", fake_embed_texts)
    monkeypatch.setattr("app.llm.reranker.rerank", fake_rerank)

    result = asyncio.run(Retriever.search("怎么退款", top_k=1, use_rerank=True))

    assert client.calls[0]["score_threshold"] is None
    assert result[0]["vector_score"] == pytest.approx(0.31)
    assert result[0]["rerank_score"] == pytest.approx(0.9)


def test_retriever_keeps_default_threshold_without_rerank(monkeypatch):
    client = _FakeClient()

    async def fake_embed_texts(texts):
        return [[0.1, 0.2]]

    monkeypatch.setattr("app.storage.qdrant.retriever.get_qdrant", lambda: client)
    monkeypatch.setattr("app.llm.embedding.embed_texts", fake_embed_texts)

    result = asyncio.run(Retriever.search("怎么退款", top_k=1, use_rerank=False))

    assert client.calls[0]["score_threshold"] == pytest.approx(0.5)
    assert result[0]["vector_score"] == pytest.approx(0.31)
