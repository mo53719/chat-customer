"""Pydantic 请求/响应模型。"""
from .chat import ChatRequest, ChatResponse
from .auth import LoginRequest, RegisterRequest, TokenResponse
from .feedback import FeedbackRequest, FeedbackResponse
from .prompts import PromptSaveRequest, PromptCompareRequest
from .common import ApiResponse

__all__ = [
    "ChatRequest", "ChatResponse",
    "LoginRequest", "RegisterRequest", "TokenResponse",
    "FeedbackRequest", "FeedbackResponse",
    "PromptSaveRequest", "PromptCompareRequest",
    "ApiResponse",
]
