"""反馈服务：提交反馈 -> 分析原因 -> 自动优化提示词 -> 存示例库。"""
from __future__ import annotations

import json
from typing import Any

from app.logger import get_logger
from app.llm import chat
from app.llm.formatter import repair_json
from app.storage.sqlite.repositories.feedback_repo import (
    feedback_repo, feedback_analysis_repo,
)
from app.storage.sqlite.repositories.session_repo import message_repo
from .example_store import example_store
from .optimizer import prompt_optimizer

_log = get_logger("feedback.service")

_ANALYZER_SYS = """你是客服回答质量分析专家。基于用户差评，分析回答不合格的具体原因。

输出严格 JSON：
{
  "category": "原因分类（如：信息错误/态度生硬/答非所问/遗漏关键信息/格式混乱/未解决问题/过度承诺/违反政策）",
  "reason": "具体原因说明（1-3 句话）",
  "suggestion": "改进建议（具体可执行的修改方向）"
}"""


class FeedbackService:
    @staticmethod
    async def submit(message_id: int | None, session_id: str | None,
                     user_id: int | None, rating: str,
                     comment: str | None,
                     question: str | None = None,
                     answer: str | None = None) -> dict[str, Any]:
        """提交反馈。

        rating=good：写入示例库（good）。
        rating=bad：分析原因 + 自动优化提示词 + 写入示例库（bad）。
        """
        # 从消息表补全 question / answer
        if message_id and (not question or not answer):
            msg = await message_repo.get(message_id)
            if msg:
                question = question or msg.content
                # 找该 session 中的下一条 assistant 回答
                if not answer:
                    msgs = await message_repo.list_by_session(session_id or msg.session_id, limit=200)
                    found = False
                    for m in msgs:
                        if found and m.role == "assistant":
                            answer = m.content
                            break
                        if m.id == message_id:
                            found = True

        feedback_id = await feedback_repo.create(
            message_id=message_id, session_id=session_id,
            user_id=user_id, rating=rating, comment=comment,
            question=question, answer=answer,
        )

        result: dict[str, Any] = {"feedback_id": feedback_id, "rating": rating}

        if rating == "good":
            # 优质回答入示例库
            await example_store.add_good(
                agent_name=None, question=question or "", answer=answer or "",
                feedback_id=feedback_id,
            )
            result["example_added"] = "good"
            return result

        # 差评：分析原因
        analysis = await FeedbackService._analyze(question or "", answer or "",
                                                   comment or "")
        analysis_id = await feedback_analysis_repo.create(
            feedback_id=feedback_id,
            category=analysis.get("category"),
            reason=analysis.get("reason"),
            suggestion=analysis.get("suggestion"),
        )
        result["analysis"] = analysis

        # 差评问题入示例库（bad）
        await example_store.add_bad(
            agent_name=None, question=question or "", answer=answer or "",
            feedback_id=feedback_id,
        )
        result["example_added"] = "bad"

        # 自动优化提示词（默认不自动启用）
        optimize_result = await prompt_optimizer.optimize(
            agent_name="main",  # 默认优化 main agent，可扩展
            feedback_id=feedback_id,
            analysis_category=analysis.get("category") or "",
            analysis_reason=analysis.get("reason") or "",
            analysis_suggestion=analysis.get("suggestion") or "",
            auto_activate=False,
            created_by="system",
        )
        result["optimize"] = optimize_result
        if optimize_result.get("version_id"):
            await feedback_analysis_repo.create  # noqa
            # 更新分析记录的 optimized_prompt_version_id
            from app.storage.sqlite.connection import SqliteConnection
            await SqliteConnection.write_with_lock(
                "feedback_analysis",
                "UPDATE feedback_analysis SET optimized_prompt_version_id=? WHERE id=?",
                (optimize_result["version_id"], analysis_id),
            )

        return result

    @staticmethod
    async def _analyze(question: str, answer: str, comment: str) -> dict[str, Any]:
        try:
            user_msg = f"""## 用户问题
{question}

## 客服回答
{answer}

## 用户差评反馈
{comment or "（用户未填写文字）"}

请分析回答不合格的原因。"""
            resp = await chat(
                messages=[
                    {"role": "system", "content": _ANALYZER_SYS},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                agent_name="feedback_analyzer",
            )
            parsed = repair_json(resp.content)
            if parsed:
                return json.loads(parsed)
            _log.warning(f"分析输出解析失败：{resp.content[:200]}")
            return {"category": "未知", "reason": resp.content, "suggestion": ""}
        except Exception as e:
            _log.exception(f"差评分析失败：{e}")
            return {"category": "分析失败", "reason": str(e), "suggestion": ""}

    @staticmethod
    async def list_feedback(rating: str | None = None, limit: int = 100) -> list[dict]:
        rows = await feedback_repo.list_all(limit=limit, rating=rating)
        return [r.__dict__ for r in rows]

    @staticmethod
    async def list_analysis(limit: int = 100) -> list[dict]:
        rows = await feedback_analysis_repo.list_all(limit=limit)
        return [r.__dict__ for r in rows]

    @staticmethod
    async def get_analysis(feedback_id: int) -> dict | None:
        a = await feedback_analysis_repo.get_by_feedback(feedback_id)
        return a.__dict__ if a else None

    @staticmethod
    async def soft_delete(feedback_id: int, deleted_by: str | None = None) -> None:
        await feedback_repo.soft_delete(feedback_id, deleted_by)


feedback_service = FeedbackService()
