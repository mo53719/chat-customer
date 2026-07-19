"""客服管理路由。"""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, Query, Body
from fastapi.responses import StreamingResponse

from app.storage.sqlite.repositories.agent_repo import agent_repo
from ..schemas.common import ApiResponse
from ..deps import require_admin

router = APIRouter(prefix="/api/agents", tags=["客服管理"])


@router.get("", response_model=ApiResponse)
async def list_agents(
    department: str | None = Query(None),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    user: dict = Depends(require_admin),
):
    rows = await agent_repo.list_all(
        department=department, status=status, keyword=keyword,
    )
    return ApiResponse(data=[r.to_dict() for r in rows])


@router.get("/{agent_id}", response_model=ApiResponse)
async def get_agent(agent_id: int, user: dict = Depends(require_admin)):
    a = await agent_repo.get_by_id(agent_id)
    if not a:
        return ApiResponse(success=False, message="客服不存在")
    return ApiResponse(data=a.to_dict())


@router.post("", response_model=ApiResponse)
async def create_agent(
    name: str = Body(...),
    account: str = Body(...),
    department: str = Body(""),
    status: str = Body("offline"),
    max_sessions: int = Body(5),
    channel: str = Body(""),
    role: str = Body("agent"),
    user: dict = Depends(require_admin),
):
    aid = await agent_repo.create(
        name=name, account=account, department=department,
        status=status, max_sessions=max_sessions,
        channel=channel, role=role,
    )
    return ApiResponse(data={"id": aid})


@router.put("/{agent_id}", response_model=ApiResponse)
async def update_agent(
    agent_id: int,
    name: str | None = Body(None),
    department: str | None = Body(None),
    status: str | None = Body(None),
    max_sessions: int | None = Body(None),
    channel: str | None = Body(None),
    role: str | None = Body(None),
    user: dict = Depends(require_admin),
):
    n = await agent_repo.update(
        agent_id=agent_id, name=name, department=department,
        status=status, max_sessions=max_sessions,
        channel=channel, role=role,
    )
    if n == 0:
        return ApiResponse(success=False, message="客服不存在或无变更")
    return ApiResponse(message="已更新")


@router.put("/{agent_id}/status", response_model=ApiResponse)
async def toggle_status(
    agent_id: int,
    status: str = Body(..., embed=True),
    user: dict = Depends(require_admin),
):
    n = await agent_repo.update_status(agent_id, status)
    if n == 0:
        return ApiResponse(success=False, message="客服不存在")
    return ApiResponse(message=f"状态已切换为 {status}")


@router.delete("/{agent_id}", response_model=ApiResponse)
async def delete_agent(agent_id: int, user: dict = Depends(require_admin)):
    n = await agent_repo.delete(agent_id)
    if n == 0:
        return ApiResponse(success=False, message="客服不存在")
    return ApiResponse(message="已删除")


@router.get("/export", response_class=StreamingResponse)
async def export_agents(
    department: str | None = Query(None),
    status: str | None = Query(None),
    user: dict = Depends(require_admin),
):
    """导出客服列表为 Excel。"""
    rows = await agent_repo.list_all(department=department, status=status)
    try:
        import openpyxl
    except ImportError:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("openpyxl 未安装", status_code=500)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "客服列表"
    ws.append(["姓名", "账号", "部门", "角色", "在线状态", "当前接待数", "最大接待数", "绑定渠道"])
    role_map = {"admin": "管理员", "supervisor": "客服主管", "agent": "普通客服"}
    status_map = {"online": "在线", "offline": "离线", "busy": "忙碌"}
    for r in rows:
        ws.append([
            r.name, r.account, r.department,
            role_map.get(r.role, r.role),
            status_map.get(r.status, r.status),
            r.current_sessions, r.max_sessions, r.channel,
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=agents_export.xlsx"},
    )