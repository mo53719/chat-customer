"""Agent 模型配置路由：每个 Agent 可独立设置模型、API 地址、温度等。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from config.settings import settings
from app.storage.sqlite.repositories.agent_model_repo import agent_model_repo
from app.prompts.service import AGENT_NAMES
from ..schemas.common import ApiResponse
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/agent-models", tags=["Agent 模型配置"])


@router.get("/agents", response_model=ApiResponse)
async def list_agents(user: dict = Depends(get_current_user)):
    """返回可用 Agent 列表。"""
    return ApiResponse(data=AGENT_NAMES)


@router.get("/defaults", response_model=ApiResponse)
async def get_defaults(user: dict = Depends(get_current_user)):
    """返回全局默认模型配置。"""
    return ApiResponse(data={
        "model": settings.LLM_MODEL,
        "base_url": settings.LLM_BASE_URL,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    })


@router.get("", response_model=ApiResponse)
async def list_configs(user: dict = Depends(get_current_user)):
    """返回所有 Agent 的模型配置。"""
    configs = await agent_model_repo.get_all_configs()
    # 脱敏 api_key
    for c in configs:
        if c.get("api_key"):
            c["api_key"] = c["api_key"][:4] + "****" + c["api_key"][-4:]
    return ApiResponse(data=configs)


@router.get("/{agent_name}", response_model=ApiResponse)
async def get_config(agent_name: str, user: dict = Depends(get_current_user)):
    """返回单个 Agent 的模型配置。"""
    cfg = await agent_model_repo.get_config(agent_name)
    if not cfg:
        return ApiResponse(data=None)
    if cfg.get("api_key"):
        cfg["api_key"] = cfg["api_key"][:4] + "****" + cfg["api_key"][-4:]
    return ApiResponse(data=cfg)


@router.post("/{agent_name}", response_model=ApiResponse)
async def save_config(agent_name: str, body: dict[str, Any],
                      user: dict = Depends(require_admin)):
    """保存某个 Agent 的模型配置。"""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(400, f"无效的 Agent 名称: {agent_name}")

    await agent_model_repo.save_config(
        agent_name=agent_name,
        model=body.get("model"),
        base_url=body.get("base_url"),
        api_key=body.get("api_key"),
        temperature=body.get("temperature"),
        max_tokens=body.get("max_tokens"),
    )
    return ApiResponse(message=f"Agent '{agent_name}' 模型配置已保存")


@router.delete("/{agent_name}", response_model=ApiResponse)
async def reset_config(agent_name: str, user: dict = Depends(require_admin)):
    """删除某个 Agent 的配置（恢复默认）。"""
    await agent_model_repo.delete_config(agent_name)
    return ApiResponse(message=f"Agent '{agent_name}' 已恢复为默认配置")