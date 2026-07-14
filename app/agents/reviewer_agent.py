"""出口自检 Agent：多维度规则检查，不再依赖 LLM 一次性判断。

规则 1-4 是纯本地规则（不调 LLM），规则 5（事实错误）可选。
失败时自动入库 badcase。
"""
from __future__ import annotations

from config.settings import settings
from app.logger import get_logger
from .reviewer.rules import RULES, ReviewResult
from .state import AgentState

_log = get_logger("agents.reviewer")


async def reviewer_agent(state: AgentState) -> AgentState:
    """多维度规则检查：每条规则独立判断。"""
    _log.info(f"开始质检：intent={state.intent} agent={state.current_agent}")

    answer = state.final_answer
    user_input = state.user_input

    # 执行所有规则
    results: list[ReviewResult] = []
    for rule in RULES:
        try:
            if rule.__name__ == "check_on_topic":
                result = rule(answer, user_input)
            else:
                result = rule(answer)
            results.append(result)
        except Exception as e:
            _log.error(f"规则 {rule.__name__} 执行异常: {e}")
            results.append(ReviewResult(rule.__name__, True, "warn", ""))

    # 统计
    failed = [r for r in results if not r.passed and r.severity == "fail"]
    warned = [r for r in results if not r.passed and r.severity == "warn"]

    state.review_details = [
        {"rule": r.rule, "passed": r.passed, "reason": r.reason}
        for r in results
    ]

    if failed:
        state.final_answer = settings.FALLBACK_TEXT
        state.error = "; ".join(r.reason for r in failed)
        state.review_status = "fail"
        _log.warning(f"质检失败: {state.error}")
    elif warned:
        state.review_status = "warn"
        state.review_warnings = [r.reason for r in warned]
        _log.info(f"质检警告: {state.review_warnings}")
    else:
        state.review_status = "pass"
        _log.info("质检通过")

    # 失败时入库 badcase
    if state.review_status == "fail":
        try:
            from app.storage.sqlite.repositories.badcase_repo import badcase_repo
            await badcase_repo.create(
                session_id=state.session_id,
                user_input=state.user_input,
                agent_answer=answer,
                intent=state.intent,
                agent_name=state.current_agent,
                failed_rules=[r.rule for r in failed],
                review_details=state.review_details,
                trace_id=state.trace_id,
            )
            _log.info("badcase 已入库")
        except Exception as e:
            _log.error(f"badcase 入库失败: {e}")

    return state