"""运维观测路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.services.ops_service import ops_service
from ..schemas.common import ApiResponse
from ..deps import require_admin

router = APIRouter(prefix="/api/ops", tags=["运维"])


@router.get("/tool-stats", response_model=ApiResponse)
async def tool_stats(days: int = Query(7, ge=1, le=90),
                     user: dict = Depends(require_admin)):
    return ApiResponse(data=await ops_service.tool_stats(days))


@router.get("/token-stats", response_model=ApiResponse)
async def token_stats(days: int = Query(7, ge=1, le=90),
                      user: dict = Depends(require_admin)):
    return ApiResponse(data=await ops_service.token_stats(days))


@router.get("/top-errors", response_model=ApiResponse)
async def top_errors(days: int = Query(7, ge=1, le=90),
                     user: dict = Depends(require_admin)):
    return ApiResponse(data=await ops_service.top_errors(days))


@router.get("/task-latency", response_model=ApiResponse)
async def task_latency(days: int = Query(7, ge=1, le=90),
                       user: dict = Depends(require_admin)):
    return ApiResponse(data=await ops_service.task_latency(days))
