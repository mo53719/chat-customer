"""仓储包：每个 repo 只暴露 DTO，不泄露 SQL。"""
from . import user_repo, order_repo, session_repo, log_repo, knowledge_repo
from . import prompt_repo, feedback_repo, example_repo, recycle_repo
from . import product_repo

__all__ = [
    "user_repo", "order_repo", "session_repo", "log_repo", "knowledge_repo",
    "prompt_repo", "feedback_repo", "example_repo", "recycle_repo",
    "product_repo",
]
