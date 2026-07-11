"""优质 / 差评示例库：辅助 LLM few-shot 推理。"""
from __future__ import annotations

from app.logger import get_logger
from app.storage.sqlite.repositories.example_repo import example_repo

_log = get_logger("feedback.examples")


class ExampleStore:
    @staticmethod
    async def add_good(agent_name: str | None, question: str, answer: str,
                       feedback_id: int | None = None) -> int:
        return await example_repo.create(agent_name, question, answer, "good", feedback_id)

    @staticmethod
    async def add_bad(agent_name: str | None, question: str, answer: str,
                      feedback_id: int | None = None) -> int:
        return await example_repo.create(agent_name, question, answer, "bad", feedback_id)

    @staticmethod
    async def list_good(agent_name: str, limit: int = 5) -> list[dict]:
        rows = await example_repo.list_by_agent(agent_name, "good", limit)
        return [{"question": r.question, "answer": r.answer} for r in rows]

    @staticmethod
    async def list_bad(agent_name: str, limit: int = 5) -> list[dict]:
        rows = await example_repo.list_by_agent(agent_name, "bad", limit)
        return [{"question": r.question, "answer": r.answer} for r in rows]

    @staticmethod
    async def list_all(tag: str | None = None, limit: int = 100) -> list[dict]:
        rows = await example_repo.list_all(limit=limit, tag=tag)
        return [r.__dict__ for r in rows]

    @staticmethod
    async def soft_delete(example_id: int, deleted_by: str | None = None) -> None:
        await example_repo.soft_delete(example_id, deleted_by)


example_store = ExampleStore()
