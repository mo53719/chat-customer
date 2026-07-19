"""LangGraph 主图编排。

三层漏斗流程：
safety → rule_router → (命中→业务Agent) | (未命中→semantic_router → (命中→业务Agent) | (未命中→llm_router → 业务Agent))
Reviewer 改为异步后台执行，不阻塞响应。
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator

from langgraph.graph import StateGraph, END

from config.settings import settings
from app.logger import get_logger
from app.storage.sqlite.repositories.session_repo import session_repo, message_repo
from app.storage.sqlite.models import MessageDTO, SessionDTO
from .state import AgentState
from .safety_agent import safety_agent, is_blocked
from .rule_router import rule_router, is_rule_hit
from .semantic_router import semantic_router, is_semantic_hit
from .router import llm_router, route_by_intent
from .presales_agent import presales_agent, presales_agent_stream
from .aftersales_agent import aftersales_agent, aftersales_agent_stream
from .order_agent import order_agent
from .rag_agent import rag_agent
from .orchestrator import orchestrator
from .fallback import fallback_node, timeout_fallback
from .reviewer_agent import reviewer_agent

_log = get_logger("agents.graph")


class AgentStateGraph:
    """封装 LangGraph 的状态机。"""

    def __init__(self):
        self._graph = self._build()
        self._compiled = self._graph.compile()

    @staticmethod
    def _build() -> StateGraph:
        g = StateGraph(dict)

        # 注册所有节点
        g.add_node("safety", _wrap(safety_agent))
        g.add_node("rule_router", _wrap(rule_router))
        g.add_node("semantic_router", _wrap(semantic_router))
        g.add_node("llm_router", _wrap(llm_router))
        g.add_node("presales", _wrap(presales_agent))
        g.add_node("aftersales", _wrap(aftersales_agent))
        g.add_node("order", _wrap(order_agent))
        g.add_node("rag", _wrap(rag_agent))
        g.add_node("orchestrator", _wrap(orchestrator))
        g.add_node("fallback", _wrap(fallback_node))

        g.set_entry_point("safety")

        # safety → (被拦截→fallback) | (通过→rule_router)
        g.add_conditional_edges(
            "safety",
            lambda s: "fallback" if (s.get("error") and "安全拦截" in s["error"]) else "rule_router",
            {"fallback": "fallback", "rule_router": "rule_router"},
        )

        # rule_router → (命中→业务Agent) | (未命中→semantic_router)
        g.add_conditional_edges(
            "rule_router",
            lambda s: _route_after_rule(_to_state(s)),
            {
                "presales": "presales",
                "aftersales": "aftersales",
                "order": "order",
                "rag": "rag",
                "orchestrator": "orchestrator",
                "fallback": "fallback",
                "semantic_router": "semantic_router",
            },
        )

        # semantic_router → (命中→业务Agent) | (未命中→llm_router)
        g.add_conditional_edges(
            "semantic_router",
            lambda s: _route_after_semantic(_to_state(s)),
            {
                "presales": "presales",
                "aftersales": "aftersales",
                "order": "order",
                "rag": "rag",
                "orchestrator": "orchestrator",
                "fallback": "fallback",
                "llm_router": "llm_router",
            },
        )

        # llm_router → 业务Agent（兜底）
        g.add_conditional_edges(
            "llm_router",
            lambda s: route_by_intent(_to_state(s)),
            {
                "presales": "presales",
                "aftersales": "aftersales",
                "order": "order",
                "rag": "rag",
                "orchestrator": "orchestrator",
                "fallback": "fallback",
            },
        )

        # 业务 Agent 直接到 END，Reviewer 异步后台执行
        for n in ("presales", "aftersales", "order", "rag", "orchestrator", "fallback"):
            g.add_edge(n, END)

        return g

    async def invoke(self, state: AgentState) -> AgentState:
        return await self._compiled.ainvoke(state.to_dict())


def _wrap(fn):
    """包装节点函数，处理 dataclass <-> dict 转换。"""
    async def inner(state_dict: dict) -> dict:
        state = _to_state(state_dict)
        result = await fn(state)
        return result.__dict__ if isinstance(result, AgentState) else result
    return inner


def _to_state(d: dict) -> AgentState:
    """从 dict 重建 AgentState。"""
    valid = {k: v for k, v in d.items() if k in AgentState.__dataclass_fields__}
    return AgentState(**valid)


def _route_after_rule(state: AgentState) -> str:
    """规则层后路由：命中则分发到业务 Agent，否则进入语义层。"""
    if is_rule_hit(state):
        return route_by_intent(state)
    return "semantic_router"


def _route_after_semantic(state: AgentState) -> str:
    """语义层后路由：命中则分发到业务 Agent，否则进入 LLM 兜底层。"""
    if is_semantic_hit(state):
        return route_by_intent(state)
    return "llm_router"


def build_graph() -> AgentStateGraph:
    """构建并返回编译后的图。"""
    return AgentStateGraph()


_graph_instance: AgentStateGraph | None = None


def get_graph() -> AgentStateGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


async def run_agent(user_input: str, session_id: str,
                    user_id: int | None = None,
                    trace_id: str | None = None) -> dict[str, Any]:
    """对外暴露的主入口：完整跑一遍图，并持久化消息。

    返回 {answer, intent, agent, tool_calls, latency_ms, error, message_id}
    """
    from app.logger.tracer import TraceContext, gen_trace_id

    tid = trace_id or gen_trace_id()
    t0 = time.time()

    async with TraceContext(tid):
        # 加载历史
        history = await message_repo.list_by_session(session_id, limit=20)
        history_msgs = [{"role": m.role, "content": m.content} for m in history
                        if m.role in ("user", "assistant")]

        state = AgentState(
            session_id=session_id,
            user_id=user_id,
            trace_id=tid,
            user_input=user_input,
            history=history_msgs,
            max_tool_rounds=settings.MAX_TOOL_ROUNDS,
        )

        # 持久化用户消息
        user_msg_id = await message_repo.create(MessageDTO(
            session_id=session_id, role="user", content=user_input,
            trace_id=tid,
        ))

        # 跑图（带超时）
        graph = get_graph()
        try:
            result_state = await asyncio.wait_for(
                graph.invoke(state),
                timeout=settings.TASK_TIMEOUT_SEC,
            )
            final_state = _to_state(result_state)
        except asyncio.TimeoutError:
            final_state = await timeout_fallback(state, TimeoutError("任务超时"))
        except Exception as e:
            _log.exception(f"图执行异常：{e}")
            state.error = str(e)
            final_state = await fallback_node(state)

        latency = int((time.time() - t0) * 1000)
        final_state.latency_ms = latency

        # 持久化 assistant 回答
        assistant_msg_id = await message_repo.create(MessageDTO(
            session_id=session_id, role="assistant",
            content=final_state.final_answer,
            agent_name=final_state.current_agent,
            intent=final_state.intent,
            tool_calls=final_state.tool_results or None,
            token_input=final_state.token_input,
            token_output=final_state.token_output,
            latency_ms=latency,
            trace_id=tid,
        ))

        # 更新会话意图摘要
        if final_state.intent and final_state.intent != "fallback":
            from app.storage.sqlite.connection import SqliteConnection
            await SqliteConnection.write_with_lock(
                "sessions",
                "UPDATE sessions SET intent_summary=? WHERE session_id=?",
                (final_state.intent, session_id),
            )

        # 异步执行 Reviewer（不阻塞响应）
        _launch_reviewer_async(final_state)

        _log.info(f"会话 {session_id} 完成：intent={final_state.intent} "
                  f"agent={final_state.current_agent} latency={latency}ms")

        return {
            "answer": final_state.final_answer,
            "intent": final_state.intent,
            "agent": final_state.current_agent,
            "tool_calls": final_state.tool_results,
            "tool_calls_count": final_state.tool_calls_count,
            "rag_hits": final_state.rag_hits,
            "latency_ms": latency,
            "token_input": final_state.token_input,
            "token_output": final_state.token_output,
            "error": final_state.error,
            "trace_id": tid,
            "message_id": assistant_msg_id,
            "user_message_id": user_msg_id,
        }


def _launch_reviewer_async(state: AgentState):
    """异步启动 Reviewer，失败不影响主流程。"""
    async def _review():
        try:
            await reviewer_agent(state)
        except Exception as e:
            _log.warning(f"Reviewer 异步执行失败：{e}")
    try:
        asyncio.create_task(_review())
    except Exception as e:
        _log.warning(f"Reviewer 启动失败，跳过质检：{e}")


async def run_agent_stream(user_input: str, session_id: str,
                           user_id: int | None = None,
                           trace_id: str | None = None) -> AsyncIterator[str]:
    """流式入口：边生成边输出，用户立即看到打字效果。"""
    from app.logger.tracer import TraceContext, gen_trace_id

    tid = trace_id or gen_trace_id()
    t0 = time.time()

    async with TraceContext(tid):
        history = await message_repo.list_by_session(session_id, limit=20)
        history_msgs = [{"role": m.role, "content": m.content} for m in history
                        if m.role in ("user", "assistant")]

        state = AgentState(
            session_id=session_id,
            user_id=user_id,
            trace_id=tid,
            user_input=user_input,
            history=history_msgs,
            max_tool_rounds=settings.MAX_TOOL_ROUNDS,
        )

        # 持久化用户消息
        user_msg_id = await message_repo.create(MessageDTO(
            session_id=session_id, role="user", content=user_input,
            trace_id=tid,
        ))

        # 先跑 safety + router（同步）
        graph = get_graph()
        try:
            result_state = await asyncio.wait_for(
                graph.invoke(state),
                timeout=settings.TASK_TIMEOUT_SEC,
            )
            final_state = _to_state(result_state)
        except asyncio.TimeoutError:
            final_state = await timeout_fallback(state, TimeoutError("任务超时"))
        except Exception as e:
            _log.exception(f"图执行异常：{e}")
            state.error = str(e)
            final_state = await fallback_node(state)

        # 流式输出答案内容
        answer = final_state.final_answer
        full_answer = ""

        # 如果 agent 支持流式，使用流式输出
        if final_state.current_agent in ("presales", "aftersales"):
            stream_fn = presales_agent_stream if final_state.current_agent == "presales" else aftersales_agent_stream
            async for chunk in stream_fn(final_state):
                full_answer += chunk
                yield chunk
        else:
            # 不支持流式的 agent，按句分段输出
            import re
            parts = re.split(r"(?<=[。！？!?.\n])", answer)
            for p in parts:
                if p:
                    full_answer += p
                    yield p

        latency = int((time.time() - t0) * 1000)
        final_state.latency_ms = latency
        final_state.final_answer = full_answer

        # 持久化 assistant 回答
        assistant_msg_id = await message_repo.create(MessageDTO(
            session_id=session_id, role="assistant",
            content=full_answer,
            agent_name=final_state.current_agent,
            intent=final_state.intent,
            tool_calls=final_state.tool_results or None,
            token_input=final_state.token_input,
            token_output=final_state.token_output,
            latency_ms=latency,
            trace_id=tid,
        ))

        if final_state.intent and final_state.intent != "fallback":
            from app.storage.sqlite.connection import SqliteConnection
            await SqliteConnection.write_with_lock(
                "sessions",
                "UPDATE sessions SET intent_summary=? WHERE session_id=?",
                (final_state.intent, session_id),
            )

        # 异步 Reviewer
        _launch_reviewer_async(final_state)

        _log.info(f"会话 {session_id} 完成（流式）：intent={final_state.intent} "
                  f"agent={final_state.current_agent} latency={latency}ms")
