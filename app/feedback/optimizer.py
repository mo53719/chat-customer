"""提示词自动优化：基于差评分析生成新版本提示词。"""
from __future__ import annotations

import json
from typing import Any

from app.logger import get_logger
from app.llm import chat
from app.llm.formatter import repair_json
from app.prompts.loader import load_prompt
from app.prompts.service import prompt_service
from app.storage.sqlite.repositories.feedback_repo import feedback_analysis_repo

_log = get_logger("feedback.optimizer")

_OPTIMIZER_SYS = """你是提示词优化专家。基于「当前提示词 + 差评原因分析」，生成优化后的新提示词。

输出严格 JSON：
{
  "optimized_prompt": "优化后的完整提示词",
  "change_note": "本次优化的简要说明（一句话）"
}

要求：
- 保留原提示词的核心职责与角色定位
- 针对差评原因做有针对性的补强
- 不要删除原有的工具说明与输出格式要求
- 优化后的提示词应可直接替换原提示词使用"""


class PromptOptimizer:
    @staticmethod
    async def optimize(agent_name: str, feedback_id: int,
                       analysis_category: str, analysis_reason: str,
                       analysis_suggestion: str,
                       auto_activate: bool = False,
                       created_by: str = "system") -> dict[str, Any]:
        """根据差评分析自动生成优化版提示词。

        默认不自动启用（auto_activate=False），需人工在版本管理页确认。
        """
        current_prompt = await load_prompt(agent_name)

        user_msg = f"""## 当前提示词（{agent_name}）
{current_prompt}

## 差评原因分析
- 分类：{analysis_category}
- 原因：{analysis_reason}
- 改进建议：{analysis_suggestion}

请生成优化后的提示词。"""

        try:
            resp = await chat(
                messages=[
                    {"role": "system", "content": _OPTIMIZER_SYS},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                agent_name="prompt_optimizer",
            )
            parsed = repair_json(resp.content)
            if not parsed:
                _log.error(f"优化器输出解析失败：{resp.content[:200]}")
                return {"success": False, "error": "优化输出解析失败"}
            data = json.loads(parsed)
            new_prompt = data.get("optimized_prompt", "")
            change_note = data.get("change_note", "差评自动优化")
            if not new_prompt:
                return {"success": False, "error": "优化输出为空"}

            # 写入新版本（auto_generated=1），不自动启用
            vid = await prompt_repo_create_version_safe(
                agent_name=agent_name,
                content=new_prompt,
                change_note=change_note,
                created_by=created_by,
                auto_generated=1,
                source_feedback_id=feedback_id,
                auto_activate=auto_activate,
            )
            # 回填分析表的 optimized_prompt_version_id
            await feedback_analysis_repo.create  # noqa: PLC0414 (typo guard)

            _log.info(f"自动优化提示词 {agent_name} 新版本 id={vid}")
            return {
                "success": True,
                "version_id": vid,
                "change_note": change_note,
                "auto_activated": auto_activate,
            }
        except Exception as e:
            _log.exception(f"提示词优化失败：{e}")
            return {"success": False, "error": str(e)}


async def prompt_repo_create_version_safe(
    agent_name: str, content: str, change_note: str,
    created_by: str, auto_generated: int,
    source_feedback_id: int, auto_activate: bool,
) -> int:
    """安全包装：调用 prompt_service，可控制是否自动启用。"""
    from app.storage.sqlite.repositories.prompt_repo import prompt_repo
    vid = await prompt_repo.create_version(
        agent_name=agent_name, content=content,
        change_note=change_note, created_by=created_by,
        auto_generated=auto_generated, source_feedback_id=source_feedback_id,
    )
    if not auto_activate:
        # create_version 默认 is_active=1，需切回旧版本
        # 找到上一个非自动生成的版本并启用
        versions = await prompt_repo.list_versions(agent_name)
        # versions[0] 是刚创建的新版本，找下一个人工版本
        for v in versions[1:]:
            if v.auto_generated == 0:
                await prompt_repo.activate(v.id)
                break
    from app.prompts.loader import invalidate_cache
    invalidate_cache(agent_name)
    return vid


prompt_optimizer = PromptOptimizer()
