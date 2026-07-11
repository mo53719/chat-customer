"""提示词管理 schema。"""
from __future__ import annotations

from pydantic import BaseModel


class PromptSaveRequest(BaseModel):
    agent_name: str
    content: str
    change_note: str | None = None


class PromptCompareRequest(BaseModel):
    version_a_id: int
    version_b_id: int
    test_question: str


class PromptActivateRequest(BaseModel):
    version_id: int
