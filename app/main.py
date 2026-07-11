"""FastAPI 应用入口。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from app.logger import setup_logging, get_logger
from app.storage.sqlite.connection import SqliteConnection
from app.storage.qdrant.client import close_qdrant
from app.api.routes import (
    auth, chat, session, log, stats, order, knowledge,
    prompts, feedback, ops, recycle, product, agent_models,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    _log = get_logger("main")
    _log.info("=== 智能客服系统启动 ===")
    # 触发 SQLite 连接初始化
    _log.info("lifespan: opening SQLite...")
    await SqliteConnection.get_db()
    _log.info("lifespan: SQLite ready")
    # 初始化 Qdrant 集合
    _log.info("lifespan: ensuring Qdrant collections...")
    try:
        from app.storage.qdrant.collection import ensure_collection
        _log.info("lifespan: ensure %s", settings.QDRANT_COLLECTION)
        await ensure_collection(settings.QDRANT_COLLECTION)
        _log.info("lifespan: ensure %s", settings.QDRANT_PRODUCT_COLLECTION)
        await ensure_collection(settings.QDRANT_PRODUCT_COLLECTION)
        _log.info("lifespan: ensure %s", settings.QDRANT_LONG_TERM_COLLECTION)
        await ensure_collection(settings.QDRANT_LONG_TERM_COLLECTION)
        _log.info("lifespan: all Qdrant collections ready")
    except Exception as e:
        _log.warning(f"Qdrant 初始化失败（可能未启动）：{e}")
    _log.info("lifespan: yield (server up)")
    yield
    _log.info("=== 智能客服系统关闭 ===")
    await SqliteConnection.close()
    await close_qdrant()


app = FastAPI(
    title="智能客服系统 API",
    description="严格分层 / LangGraph 多 Agent / 双记忆 / 提示词版本管理 / 反馈自优化",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
for r in (auth, chat, session, log, stats, order, knowledge,
          prompts, feedback, ops, recycle, product, agent_models):
    app.include_router(r.router)


@app.get("/", tags=["健康"])
async def root():
    return {"status": "ok", "service": "chat_customer", "docs": "/docs"}


@app.get("/health", tags=["健康"])
async def health():
    return {"status": "healthy"}
