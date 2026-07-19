"""配置层：基于 pydantic-settings 加载 .env，全局只读单例。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_SEED_DIR = Path(__file__).resolve().parent / "prompts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "glm-4-plus"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048
    LLM_TIMEOUT: int = 60

    # Embedding（可插拔后端）
    EMBEDDING_BACKEND: str = "local"             # "local" | "openai"
    EMBEDDING_BASE_URL: str = ""                  # openai 后端使用
    EMBEDDING_API_KEY: str = ""                   # openai 后端使用
    EMBEDDING_MODEL: str = "bge-small-zh-v1.5"    # 通用标识
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-zh-v1.5"  # fastembed 用
    EMBEDDING_DIM: int = 512
    # 本地后端（fastembed + Qdrant ONNX 优化版）
    EMBEDDING_LOCAL_PATH: str = "models/qdrant-bge-small-zh-v1.5"
    EMBEDDING_LOCAL_DEVICE: str = "cpu"           # "cpu" | "cuda"
    EMBEDDING_BATCH_SIZE: int = 32                # 本地无 10 条限制
    EMBEDDING_NORMALIZE: bool = True              # bge + cosine 推荐 L2 归一化

    # Rerank（fastembed CrossEncoder）
    RERANK_ENABLED: bool = True
    RERANK_MODEL: str = "BAAI/bge-reranker-base"   # fastembed 支持的中文 reranker
    RERANK_TOP_N: int = 20                           # 初筛数量（向量 TopK * N）
    RERANK_FINAL_K: int = 5                          # rerank 后最终返回

    # Qdrant
    QDRANT_MODE: str = "local"          # "local"（本地服务） | "embed"（嵌入式）
    QDRANT_PATH: str = "data/qdrant"    # 嵌入式模式数据目录
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "chat_customer_kb"
    QDRANT_PRODUCT_COLLECTION: str = "product_kb"
    QDRANT_LONG_TERM_COLLECTION: str = "user_long_term_memory"

    # SQLite
    SQLITE_PATH: str = "data/chat_customer.db"
    SQLITE_WAL: bool = True

    # 安全
    JWT_SECRET: str = "change_me_to_a_random_long_string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    API_KEY_HEADER: str = "X-API-Key"
    RATE_LIMIT_PER_MINUTE: int = 60

    # 熔断 / 限流 / 超时
    MAX_TOOL_ROUNDS: int = 6
    TASK_TIMEOUT_SEC: int = 120
    CIRCUIT_FAIL_THRESHOLD: int = 5
    CIRCUIT_RECOVER_SEC: int = 30
    LLM_RETRY_MAX: int = 3
    LLM_RETRY_BACKOFF: float = 1.5

    # 上下文记忆
    CONTEXT_MAX_TOKENS: int = 4000
    SHORT_TERM_WINDOW: int = 20

    # 兜底
    FALLBACK_TEXT: str = "抱歉，我暂时无法处理您的请求，已为您转接人工客服。"

    # 意图缓存
    INTENT_CACHE_SIZE: int = 100

    # 三层漏斗路由
    RULE_ROUTER_ENABLED: bool = True              # 是否启用规则层（Layer 1）
    SEMANTIC_ROUTER_ENABLED: bool = True          # 是否启用语义层（Layer 2）
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.7    # 语义层相似度阈值
    SEMANTIC_HISTORY_BOOST: float = 0.1           # 对话历史一致性加成

    # RAG 超时
    RAG_TIMEOUT: float = 3.0

    # 服务
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "30 days"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def sqlite_abs_path(self) -> Path:
        p = Path(self.SQLITE_PATH)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def log_abs_dir(self) -> Path:
        p = Path(self.LOG_DIR)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def embedding_local_abs_path(self) -> Path:
        p = Path(self.EMBEDDING_LOCAL_PATH)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p

    @property
    def qdrant_abs_path(self) -> Path:
        p = Path(self.QDRANT_PATH)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
