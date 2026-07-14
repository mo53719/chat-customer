"""失败案例 API：查询、标记状态。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.storage.sqlite.repositories.badcase_repo import badcase_repo

router = APIRouter(prefix="/api/badcase", tags=["Badcase"])


@router.get("/list")
async def list_badcases(
    status: str = Query("new"),
    keyword: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    data = await badcase_repo.search(keyword=keyword, status=status, limit=limit, offset=offset)
    return {
        "data": [
            {
                "id": d.id,
                "session_id": d.session_id,
                "user_input": d.user_input,
                "agent_answer": d.agent_answer,
                "intent": d.intent,
                "agent_name": d.agent_name,
                "failed_rules": d.failed_rules,
                "review_details": d.review_details,
                "trace_id": d.trace_id,
                "status": d.status,
                "note": d.note,
                "created_at": d.created_at,
                "reviewed_at": d.reviewed_at,
                "reviewed_by": d.reviewed_by,
            }
            for d in data
        ]
    }


@router.put("/{badcase_id}/mark")
async def mark_badcase(
    badcase_id: int,
    status: str = Query(...),
    note: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    await badcase_repo.mark(badcase_id, status, note, str(user.get("user_id", "")))
    return {"ok": True}