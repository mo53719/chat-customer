"""统计数据路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.services.stats_service import stats_service
from ..schemas.common import ApiResponse
from ..deps import get_current_user

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/overview", response_model=ApiResponse)
async def overview(days: int = Query(7, ge=1, le=90),
                   user: dict = Depends(get_current_user)):
    return ApiResponse(data=await stats_service.overview(days))


@router.get("/top-intents", response_model=ApiResponse)
async def top_intents(days: int = Query(7, ge=1, le=90),
                      user: dict = Depends(get_current_user)):
    return ApiResponse(data=await stats_service.top_intents(days))


@router.get("/daily-sessions", response_model=ApiResponse)
async def daily_sessions(days: int = Query(30, ge=1, le=365),
                         user: dict = Depends(get_current_user)):
    return ApiResponse(data=await stats_service.daily_sessions(days))
