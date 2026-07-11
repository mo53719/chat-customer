"""测试状态机与意图路由。"""
import pytest

from app.agents.state import AgentState, Intent
from app.agents.router import route_by_intent


def test_state_tool_rounds_limit():
    s = AgentState(max_tool_rounds=2)
    assert s.can_call_tool()
    s.tool_calls_count = 2
    assert not s.can_call_tool()


def test_route_by_intent():
    s = AgentState(intent="presales", intent_confidence=0.9)
    assert route_by_intent(s) == "presales"


def test_route_low_confidence_fallback():
    s = AgentState(intent="presales", intent_confidence=0.3)
    assert route_by_intent(s) == "fallback"


def test_route_decomposition():
    s = AgentState(intent="rag", intent_confidence=0.9, needs_decomposition=True)
    assert route_by_intent(s) == "orchestrator"
