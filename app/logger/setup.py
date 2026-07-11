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

    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[trace_id]}</cyan> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.configure(extra={"trace_id": "-"})

    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=False,
    )

    log_dir = settings.log_abs_dir
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

    _configured = True


def get_logger(name: Optional[str] = None):
    """获取带 name 标签的 logger 实例。"""
    if not _configured:
        setup_logging()
    if name:
        return logger.bind(module=name)
    return logger
