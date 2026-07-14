import pytest

from app.agents.router import route_by_intent
from app.agents.state import AgentState


class TestRouteByIntent:
    def test_low_confidence_goes_to_fallback(self):
        state = AgentState(intent="presales", intent_confidence=0.3)
        assert route_by_intent(state) == "fallback"

    def test_high_confidence_presales(self):
        state = AgentState(intent="presales", intent_confidence=0.9)
        assert route_by_intent(state) == "presales"

    def test_high_confidence_aftersales(self):
        state = AgentState(intent="aftersales", intent_confidence=0.8)
        assert route_by_intent(state) == "aftersales"

    def test_high_confidence_order(self):
        state = AgentState(intent="order", intent_confidence=0.7)
        assert route_by_intent(state) == "order"

    def test_high_confidence_rag(self):
        state = AgentState(intent="rag", intent_confidence=0.9)
        assert route_by_intent(state) == "rag"

    def test_safety_always_fallback(self):
        state = AgentState(intent="safety", intent_confidence=0.99)
        assert route_by_intent(state) == "fallback"

    def test_fallback_intent(self):
        state = AgentState(intent="fallback", intent_confidence=0.8)
        assert route_by_intent(state) == "fallback"

    def test_unknown_intent(self):
        state = AgentState(intent="unknown", intent_confidence=0.9)
        assert route_by_intent(state) == "fallback"

    def test_decomposition_trumps_intent(self):
        state = AgentState(intent="presales", intent_confidence=0.9, needs_decomposition=True)
        assert route_by_intent(state) == "orchestrator"

    def test_exact_boundary_confidence(self):
        state = AgentState(intent="presales", intent_confidence=0.6)
        assert route_by_intent(state) == "presales"