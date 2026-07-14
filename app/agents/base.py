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

    # 强制注入 RAG 上下文（agent 层预取，确保 LLM 不会漏查知识库）
    if state.rag_context:
        sys_prompt += "\n\n## 知识库检索结果（已预取，优先参考）\n"
        sys_prompt += "以下是从知识库中检索到的与用户问题最相关的内容，请优先基于这些内容回答：\n\n"
        sys_prompt += state.rag_context
        sys_prompt += "\n\n注意：如果上述知识库内容能回答用户问题，直接使用，不要编造信息。"

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

            # 捕获 RAG 检索命中，供前端溯源引用
            if tool_name == "rag_search" and tool_result_data.get("success"):
                hits = tool_result_data.get("data", [])
                if isinstance(hits, list):
                    for h in hits:
                        if isinstance(h, dict):
                            state.rag_hits.append({
                                "chunk_id": h.get("chunk_id"),
                                "doc_id": h.get("doc_id"),
                                "title": h.get("title"),
                                "text": h.get("text", "")[:200],
                                "source": h.get("source"),
                                "page_no": h.get("page_no"),
                                "sheet": h.get("sheet"),
                                "row": h.get("row"),
                                "heading_path": h.get("heading_path"),
                                "score": h.get("score"),
                            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id"),
                "name": tool_name,
                "content": json.dumps(tool_result_data, ensure_ascii=False),
            })

    state.error = f"{agent_name} 工具循环超出最大轮次"

    # 兜底：轮次用尽且没答案，再调一次 LLM（不带工具）强制输出文本
    if not state.final_answer:
        _log.warning(f"{agent_name} 工具轮次用尽且无答案，兜底调 LLM（无工具）")
        try:
            resp = await chat(
                messages=messages, tools=None,
                agent_name=agent_name, session_id=state.session_id,
            )
            state.token_input += resp.prompt_tokens
            state.token_output += resp.completion_tokens
            state.final_answer = resp.content or "抱歉，我暂时无法回答这个问题，请换个方式描述。"
            state.error = None
        except Exception as e:
            state.error = f"{agent_name} 兜底调用失败: {e}"
            state.final_answer = "抱歉，系统暂时无法处理您的请求，请稍后再试。"

    return state
