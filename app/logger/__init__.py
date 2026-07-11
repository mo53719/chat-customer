"""日志运维层：基于 loguru 的统一日志配置。

横切所有层，仅暴露 get_logger()，禁止反向依赖业务。
"""
from .setup import get_logger, setup_logging
from .tracer import TraceContext, gen_trace_id, trace_id_var

__all__ = ["get_logger", "setup_logging", "TraceContext", "gen_trace_id", "trace_id_var"]
