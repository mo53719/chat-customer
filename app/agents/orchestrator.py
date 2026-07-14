"""子任务拆分协同：采集 -> 整理 -> 复盘 三阶段。

默认不启用，router 标记 needs_decomposition=True 时触发。
适用于复杂请求（如「查所有未发货订单并按金额排序后给出催办建议」）。
"""
from __future__ import annotations

# 核心依赖：日志、LLM 调用、提示词加载、Agent 状态
from app.logger import get_logger
from app.llm import chat
from app.prompts.loader import load_prompt
from .state import AgentState

# 模块级 logger，用于追踪子任务协同流程
_log = get_logger("agents.orchestrator")


async def orchestrator(state: AgentState) -> AgentState:
    """三阶段子任务协同。

    阶段1 采集：调 LLM 拆出需要调用的工具列表
    阶段2 整理：执行工具调用收集信息
    阶段3 复盘：基于收集的信息生成最终答案
    """
    state.current_agent = "orchestrator"
    _log.info(f"启动子任务协同：{state.user_input[:50]}")

    # 加载主 Agent 系统提示词，作为采集和复盘阶段的共用上下文
    sys_prompt = await load_prompt("main_agent")

    # ---- 阶段1：采集 ----
    # 调 LLM 拆出需要调用的工具列表
    # 使用低温度（0.2）确保工具调用的稳定性
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
    # 解析 LLM 返回的 JSON 工具计划，逐个执行
    from app.llm.formatter import repair_json
    import json
    # repair_json 修复 LLM 输出的格式问题（多余逗号、未闭合括号等）
    parsed = repair_json(resp.content)
    plan: list[dict] = []
    if parsed:
        try:
            # json.loads 解析修复后的 JSON 字符串
            plan = json.loads(parsed)
            if isinstance(plan, dict):
                plan = [plan]  # 兜底：单个工具转为列表
        except Exception:
            plan = []

    from app.tools.registry import get_tool
    collected: list[dict] = []
    # 遍历工具计划，逐个执行工具调用
    for step in plan[:5]:  # 最多执行 5 步，防止无限循环
        tool_name = step.get("tool") or step.get("name")
        args = step.get("args") or step.get("parameters") or {}
        if not tool_name:
            continue
        # 从工具注册表查找工具定义
        spec = get_tool(tool_name)
        if not spec:
            collected.append({"tool": tool_name, "error": "工具不存在"})
            continue
        try:
            # 执行工具，获取 ToolResult（含 data/error 字段）
            tr = await spec.func(state, **args)  # 执行工具
            collected.append({"tool": tool_name, "data": tr.data, "error": tr.error})
            state.tool_calls_count += 1  # 更新工具调用计数
            # 记录工具调用结果，供复盘阶段引用
            state.tool_results.append({"tool": tool_name, "args": args,
                                        "result": tr.data})
        except Exception as e:
            # 捕获工具调用异常，记录错误信息继续执行
            collected.append({"tool": tool_name, "error": str(e)})

    # ---- 阶段3：复盘 ----
    # 基于采集到的工具结果，调 LLM 生成最终答案
    review_msg = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"原始请求：{state.user_input}\n\n采集到的信息：{json.dumps(collected, ensure_ascii=False)}\n\n请基于以上信息生成最终答案。"},
    ]
    try:
        # 调 LLM 综合所有工具结果，生成最终答案
        resp2 = await chat(messages=review_msg, temperature=0.5,
                           agent_name="orchestrator_review",
                           session_id=state.session_id)
        state.final_answer = resp2.content
        state.token_input += resp2.prompt_tokens
        state.token_output += resp2.completion_tokens
    except Exception as e:
        # 复盘阶段失败，记录错误信息
        state.error = f"复盘阶段失败: {e}"

    return state
