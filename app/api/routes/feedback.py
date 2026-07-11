"""反馈路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.feedback.service import feedback_service
from ..schemas.feedback import FeedbackRequest
from ..schemas.common import ApiResponse
from ..deps import get_current_user

router = APIRouter(prefix="/api/feedback", tags=["反馈"])


@router.post("", response_model=ApiResponse)
async def submit_feedback(req: FeedbackRequest, user: dict = Depends(get_current_user)):
    result = await feedback_service.submit(
        message_id=req.message_id, session_id=req.session_id,
        user_id=user["user_id"], rating=req.rating, comment=req.comment,
        question=req.question, answer=req.answer,
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse)
async def list_feedback(rating: str | None = None, limit: int = 100,
                        user: dict = Depends(get_current_user)):
    return ApiResponse(data=await feedback_service.list_feedback(rating, limit))


@router.get("/analysis", response_model=ApiResponse)
async def list_analysis(limit: int = 100, user: dict = Depends(get_current_user)):
    return ApiResponse(data=await feedback_service.list_analysis(limit))


@router.get("/{feedback_id}/analysis", response_model=ApiResponse)
async def get_analysis(feedback_id: int, user: dict = Depends(get_current_user)):
    return ApiResponse(data=await feedback_service.get_analysis(feedback_id))


@router.delete("/{feedback_id}", response_model=ApiResponse)
async def delete_feedback(feedback_id: int, user: dict = Depends(get_current_user)):
    await feedback_service.soft_delete(feedback_id, deleted_by=user["username"])
    return ApiResponse(message="已删除（可从回收站恢复）")
