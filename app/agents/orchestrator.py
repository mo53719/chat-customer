"""子任务拆分协同：采集 -> 整理 -> 复盘 三阶段。

默认不启用，router 标记 needs_decomposition=True 时触发。
适用于复杂请求（如「查所有未发货订单并按金额排序后给出催办建议」）。
"""
from __future__ import annotations

from app.logger import get_logger
from app.llm import chat
from app.prompts.loader import load_prompt
from .state import AgentState

_log = get_logger("agents.orchestrator")


async def orchestrator(state: AgentState) -> AgentState:
    """三阶段子任务协同。

    阶段1 采集：调 LLM 拆出需要调用的工具列表
    阶段2 整理：执行工具调用收集信息
    阶段3 复盘：基于收集的信息生成最终答案
    """
    state.current_agent = "orchestrator"
    _log.info(f"启动子任务协同：{state.user_input[:50]}")

    sys_prompt = await load_prompt("main_agent")

    # ---- 阶段1：采集 ----
    collect_msg = [
        {"role": "system", "content": sys_prompt + "\n\n你现在需要拆解任务。"},
        {"role": "user", "content": f"复杂请求：{state.user_input}\n\n请列出需要调用的工具及参数（JSON 数组）。"},
    ]
    try:
        resp = await chat(messages=collect_msg, temperature=0.2,
                          agent_name="orchestrator_collect",
                          session_id=state.session_id)
    except Exception as e:
        state.error = f"采集阶段失败: {e}"
        return state

    # ---- 阶段2：整理（执行工具） ----
    from app.llm.formatter import repair_json
    import json
    parsed = repair_json(resp.content)
    plan: list[dict] = []
    if parsed:
        try:
            plan = json.loads(parsed)
            if isinstance(plan, dict):
                plan = [plan]
        except Exception:
            plan = []

    from app.tools.registry import get_tool
    collected: list[dict] = []
    for step in plan[:5]:  # 最多 5 步
        tool_name = step.get("tool") or step.get("name")
        args = step.get("args") or step.get("parameters") or {}
        if not tool_name:
            continue
        spec = get_tool(tool_name)
        if not spec:
            collected.append({"tool": tool_name, "error": "工具不存在"})
            continue
        try:
            tr = await spec.func(state, **args)
            collected.append({"tool": tool_name, "data": tr.data, "error": tr.error})
            state.tool_calls_count += 1
            state.tool_results.append({"tool": tool_name, "args": args,
                                        "result": tr.data})
        except Exception as e:
            collected.append({"tool": tool_name, "error": str(e)})

    # ---- 阶段3：复盘 ----
    review_msg = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"原始请求：{state.user_input}\n\n采集到的信息：{json.dumps(collected, ensure_ascii=False)}\n\n请基于以上信息生成最终答案。"},
    ]
    try:
        resp2 = await chat(messages=review_msg, temperature=0.5,
                           agent_name="orchestrator_review",
                           session_id=state.session_id)
        state.final_answer = resp2.content
        state.token_input += resp2.prompt_tokens
        state.token_output += resp2.completion_tokens
    except Exception as e:
        state.error = f"复盘阶段失败: {e}"

    return state
