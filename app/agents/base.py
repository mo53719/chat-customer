"""业务 Agent 通用基类：加载 prompt -> 组装 messages -> 调 LLM -> 工具循环。

各业务 Agent 复用此逻辑，只差异化 agent_name。
"""
from __future__ import annotations

import json
from typing import Any

from app.logger import get_logger
from app.llm import chat
from app.llm.formatter import repair_json
from app.memory.manager import memory_manager
from app.prompts.loader import load_prompt
from app.tools.registry import get_tool, to_openai_tools
from app.tools import rag_tools, order_tools, product_tools, user_tools  # 触发工具注册
from app.feedback.example_store import example_store
from .state import AgentState

_log = get_logger("agents.base")


async def run_business_agent(state: AgentState, agent_name: str,
                             allowed_tools: list[str] | None = None) -> AgentState:
    """通用业务 Agent 执行流程。"""
    state.current_agent = agent_name

    # 加载提示词
    sys_prompt = await load_prompt(agent_name)
    if not sys_prompt:
        sys_prompt = f"你是 {agent_name} Agent，请回应用户请求。"

    # 加载优质示例（few-shot）
    examples = await example_store.list_good(agent_name, limit=3)
    state.examples = examples

    # 组装上下文
    messages = memory_manager.build_context(
        history=state.history,
        system_prompt=sys_prompt,
        user_input=state.user_input,
        examples=examples,
    )

    # 工具集
    tools = None
    if allowed_tools:
        tool_specs = [t for t in to_openai_tools() if t["function"]["name"] in allowed_tools]
        tools = tool_specs if tool_specs else None

    # 主循环：LLM -> 工具调用 -> LLM ...
    max_rounds = state.max_tool_rounds
    for _ in range(max_rounds + 1):
        try:
            resp = await chat(
                messages=messages, tools=tools,
                agent_name=agent_name, session_id=state.session_id,
            )
        except Exception as e:
            state.error = f"{agent_name} LLM 调用失败: {e}"
            return state

        state.token_input += resp.prompt_tokens
        state.token_output += resp.completion_tokens

        # 无工具调用 -> 直接返回
        if not resp.tool_calls or not state.can_call_tool():
            state.final_answer = resp.content
            return state

        # 有工具调用 -> 执行工具 -> 把结果 append 到 messages -> 继续
        messages.append({"role": "assistant", "content": resp.content,
                         "tool_calls": resp.tool_calls})

        for tc in resp.tool_calls:
            state.tool_calls_count += 1
            if not state.can_call_tool():
                state.error = f"超过最大工具调用轮次 {max_rounds}"
                return state

            # 兼容 OpenAI 协议完整结构
            func = tc.get("function", {}) if isinstance(tc.get("function"), dict) else {}
            tool_name = func.get("name") or tc.get("name", "")
            args_raw = func.get("arguments", "{}")
            if not args_raw:
                args_raw = "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                args = {}

            spec = get_tool(tool_name)
            if not spec:
                tool_result_data = {"error": f"工具 {tool_name} 不存在"}
            else:
                try:
                    tr = await spec.func(state, **args)
                    tool_result_data = {"success": tr.success, "data": tr.data, "error": tr.error}
                except Exception as e:
                    _log.warning(f"工具 {tool_name} 执行失败：{e}")
                    tool_result_data = {"success": False, "data": None, "error": str(e)}

            state.tool_results.append({"tool": tool_name, "args": args,
                                        "result": tool_result_data})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id"),
                "name": tool_name,
                "content": json.dumps(tool_result_data, ensure_ascii=False),
            })

    state.error = f"{agent_name} 工具循环超出最大轮次"
    return state
