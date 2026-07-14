"""loguru 配置：控制台 + 文件轮转 + trace_id 注入。"""
from __future__ import annotations

import sys
from typing import Optional

from loguru import logger

from config.settings import settings

_configured = False


def setup_logging() -> None:
    """初始化日志系统，进程内只配置一次。"""
    global _configured
    if _configured:
        return

    # 移除 loguru 默认 handler，避免日志重复输出
    logger.remove()

    # 日志格式：时间 | 级别 | trace_id | 模块:函数:行号 - 消息
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[trace_id]}</cyan> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # 设置默认 trace_id，未传入时显示 "-"
    logger.configure(extra={"trace_id": "-"})

    # 控制台输出（开发调试）
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=False,
    )

    log_dir = settings.log_abs_dir  # 日志文件存放目录
    # 全量日志文件（按天轮转）
    logger.add(
        str(log_dir / "app_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    # 错误日志文件（仅 ERROR 级别，含完整诊断信息）
    logger.add(
        str(log_dir / "error_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    _configured = True  # 防止重复初始化


def get_logger(name: Optional[str] = None):
    """获取带 name 标签的 logger 实例。"""
    if not _configured:
        setup_logging()  # 懒初始化：首次调用时自动配置
    if name:
        return logger.bind(module=name)
    return logger
