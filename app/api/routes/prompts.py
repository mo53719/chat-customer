"""提示词版本管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.prompts.service import prompt_service
from ..schemas.prompts import PromptSaveRequest, PromptCompareRequest, PromptActivateRequest
from ..schemas.common import ApiResponse
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/prompts", tags=["提示词"])


@router.get("/agents", response_model=ApiResponse)
async def list_agents(user: dict = Depends(get_current_user)):
    from app.prompts.service import AGENT_NAMES
    return ApiResponse(data=AGENT_NAMES)


@router.get("/{agent_name}/versions", response_model=ApiResponse)
async def list_versions(agent_name: str, user: dict = Depends(get_current_user)):
    rows = await prompt_service.list_versions(agent_name)
    return ApiResponse(data=[r.__dict__ for r in rows])


@router.get("/{agent_name}/active", response_model=ApiResponse)
async def get_active(agent_name: str, user: dict = Depends(get_current_user)):
    v = await prompt_service.get_active(agent_name)
    return ApiResponse(data=v.__dict__ if v else None)


@router.post("/save", response_model=ApiResponse)
async def save_version(req: PromptSaveRequest, user: dict = Depends(require_admin)):
    vid = await prompt_service.save_version(
        req.agent_name, req.content, req.change_note, created_by=user["username"]
    )
    return ApiResponse(data={"version_id": vid}, message="已保存新版本")


@router.post("/activate", response_model=ApiResponse)
async def activate(req: PromptActivateRequest, user: dict = Depends(require_admin)):
    await prompt_service.activate(req.version_id)
    return ApiResponse(message="已切换启用版本")


@router.post("/compare", response_model=ApiResponse)
async def compare(req: PromptCompareRequest, user: dict = Depends(get_current_user)):
    try:
        result = await prompt_service.compare(req.version_a_id, req.version_b_id,
                                              req.test_question)
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{version_id}", response_model=ApiResponse)
async def delete_version(version_id: int, user: dict = Depends(require_admin)):
    await prompt_service.soft_delete(version_id, deleted_by=user["username"])
    return ApiResponse(message="已删除（可从回收站恢复）")
