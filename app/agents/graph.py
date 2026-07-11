"""LangGraph 主图编排。

流程：START -> safety -> router -> [presales/aftersales/order/rag/orchestrator/fallback] -> END
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from langgraph.graph import StateGraph, END

from config.settings import settings
from app.logger import get_logger
from app.storage.sqlite.repositories.session_repo import session_repo, message_repo
from app.storage.sqlite.models import MessageDTO, SessionDTO
from .state import AgentState
from .safety_agent import safety_agent, is_blocked
from .router import intent_router, route_by_intent
from .presales_agent import presales_agent
from .aftersales_agent import aftersales_agent
from .order_agent import order_agent
from .rag_agent import rag_agent
from .orchestrator import orchestrator
from .fallback import fallback_node, timeout_fallback

_log = get_logger("agents.graph")


class AgentStateGraph:
    """封装 LangGraph 的状态机。"""

    def __init__(self):
        self._graph = self._build()
        self._compiled = self._graph.compile()

    @staticmethod
    def _build() -> StateGraph:
        # 使用 dict state（LangGraph 默认支持 TypedDict / dataclass 转换）
        g = StateGraph(dict)

        g.add_node("safety", _wrap(safety_agent))
        g.add_node("router", _wrap(intent_router))
        g.add_node("presales", _wrap(presales_agent))
        g.add_node("aftersales", _wrap(aftersales_agent))
        g.add_node("order", _wrap(order_agent))
        g.add_node("rag", _wrap(rag_agent))
        g.add_node("orchestrator", _wrap(orchestrator))
        g.add_node("fallback", _wrap(fallback_node))

        g.set_entry_point("safety")

        g.add_conditional_edges(
            "safety",
            lambda s: "fallback" if (s.get("error") and "安全拦截" in s["error"]) else "router",
            {"fallback": "fallback", "router": "router"},
        )
        g.add_conditional_edges(
            "router",
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

        _log.info(f"会话 {session_id} 完成：intent={final_state.intent} "
                  f"agent={final_state.current_agent} latency={latency}ms")

        return {
            "answer": final_state.final_answer,
            "intent": final_state.intent,
            "agent": final_state.current_agent,
            "tool_calls": final_state.tool_results,
            "tool_calls_count": final_state.tool_calls_count,
            "latency_ms": latency,
            "token_input": final_state.token_input,
            "token_output": final_state.token_output,
            "error": final_state.error,
            "trace_id": tid,
            "message_id": assistant_msg_id,
            "user_message_id": user_msg_id,
        }
