import asyncio
from types import SimpleNamespace

from app.prompts import loader


def test_load_prompt_supports_agent_alias_from_db(monkeypatch):
    loader.invalidate_cache()
    calls: list[str] = []

    async def fake_get_active(agent_name: str):
        calls.append(agent_name)
        if agent_name == "rag_agent":
            return SimpleNamespace(version_no=2, content="db prompt")
        return None

    monkeypatch.setattr(loader.prompt_repo, "get_active", fake_get_active)

    content = asyncio.run(loader.load_prompt("rag"))

    assert content == "db prompt"
    assert calls == ["rag", "rag_agent"]


def test_load_prompt_supports_agent_alias_from_seed(monkeypatch, tmp_path):
    loader.invalidate_cache()
    (tmp_path / "presales_agent.md").write_text("seed prompt", encoding="utf-8")

    async def fake_get_active(agent_name: str):
        return None

    monkeypatch.setattr(loader, "PROMPTS_SEED_DIR", tmp_path)
    monkeypatch.setattr(loader.prompt_repo, "get_active", fake_get_active)

    content = asyncio.run(loader.load_prompt("presales"))

    assert content == "seed prompt"
