"""提示词版本管理模块：版本 CRUD / 启用切换 / 版本对比。"""
from .service import PromptService, prompt_service
from .loader import load_prompt

__all__ = ["PromptService", "prompt_service", "load_prompt"]
