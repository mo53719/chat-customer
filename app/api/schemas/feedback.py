"""反馈相关 schema。"""
from __future__ import annotations

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    message_id: int | None = None
    session_id: str | None = None
    rating: str  # good / bad
    comment: str | None = None
    question: str | None = None
    answer: str | None = None


class FeedbackResponse(BaseModel):
    feedback_id: int
    rating: str
    analysis: dict | None = None
    optimize: dict | None = None
    example_added: str | None = None
