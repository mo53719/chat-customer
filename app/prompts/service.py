"""提示词版本管理服务：CRUD / 启用切换 / 版本对比。"""
from __future__ import annotations

import asyncio
from typing import Any

from app.logger import get_logger
from app.storage.sqlite.repositories.prompt_repo import prompt_repo
from app.storage.sqlite.models import PromptVersionDTO
from app.llm import chat
from app.memory.manager import memory_manager
from .loader import load_prompt, invalidate_cache

_log = get_logger("prompts.service")

AGENT_NAMES = [
    "main_agent", "presales_agent", "aftersales_agent",
    "order_agent", "safety_agent", "rag_agent",
]


class PromptService:
    @staticmethod
    async def save_version(agent_name: str, content: str, change_note: str | None = None,
                           created_by: str | None = None) -> int:
        """保存新版本（自动设为启用，旧版本 inactive）。"""
        vid = await prompt_repo.create_version(
            agent_name=agent_name, content=content,
            change_note=change_note, created_by=created_by,
        )
        invalidate_cache(agent_name)
        _log.info(f"保存提示词 {agent_name} 新版本 id={vid}")
        return vid

    @staticmethod
    async def activate(version_id: int) -> None:
        await prompt_repo.activate(version_id)
        v = await prompt_repo.get_by_id(version_id)
        if v:
            invalidate_cache(v.agent_name)
        _log.info(f"启用提示词版本 id={version_id}")

    @staticmethod
    async def list_versions(agent_name: str) -> list[PromptVersionDTO]:
        return await prompt_repo.list_versions(agent_name)

    @staticmethod
    async def get_active(agent_name: str) -> PromptVersionDTO | None:
        return await prompt_repo.get_active(agent_name)

    @staticmethod
    async def get_by_id(version_id: int) -> PromptVersionDTO | None:
        return await prompt_repo.get_by_id(version_id)

    @staticmethod
    async def soft_delete(version_id: int, deleted_by: str | None = None) -> None:
        await prompt_repo.soft_delete(version_id, deleted_by)
        v = await prompt_repo.get_by_id(version_id)
        invalidate_cache(v.agent_name if v else None)

    @staticmethod
    async def compare(version_a_id: int, version_b_id: int,
                      test_question: str) -> dict[str, Any]:
        """版本对比：用两个版本提示词分别跑同一个问题，返回两个答案。"""
        va = await prompt_repo.get_by_id(version_a_id)
        vb = await prompt_repo.get_by_id(version_b_id)
        if not va or not vb:
            raise ValueError("版本不存在")

        async def _run(version: PromptVersionDTO) -> dict[str, Any]:
            messages = [
                {"role": "system", "content": version.content},
                {"role": "user", "content": test_question},
            ]
            try:
                resp = await chat(
                    messages=messages,
                    agent_name=f"compare_v{version.version_no}",
                )
                return {
                    "version_id": version.id,
                    "version_no": version.version_no,
                    "answer": resp.content,
                    "tokens": resp.prompt_tokens + resp.completion_tokens,
                }
            except Exception as e:
                return {
                    "version_id": version.id,
                    "version_no": version.version_no,
                    "answer": f"[生成失败] {e}",
                    "tokens": 0,
                }

        # 并行跑两个版本
        result_a, result_b = await asyncio.gather(_run(va), _run(vb))
        return {
            "test_question": test_question,
            "version_a": result_a,
            "version_b": result_b,
        }


prompt_service = PromptService()
