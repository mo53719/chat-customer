"""对话路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.services.chat_service import chat_service
from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.common import ApiResponse
from ..deps import get_current_user, get_api_key_user

router = APIRouter(prefix="/api/chat", tags=["对话"])


def _client_ip(request: Request) -> str:
    # 优先 X-Forwarded-For（反代场景），否则直接取 socket
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else ""


@router.post("", response_model=ApiResponse[ChatResponse])
async def chat(req: ChatRequest, request: Request,
               user: dict = Depends(get_current_user)):
    """内部用户对话（JWT 鉴权）。"""
    result = await chat_service.chat(
        session_id=req.session_id or "", message=req.message,
        user_id=user["user_id"], channel=req.channel,
        visitor_ip=_client_ip(request),
    )
    return ApiResponse(data=ChatResponse(**result))


@router.post("/stream")
async def chat_stream(req: ChatRequest, request: Request,
                      user: dict = Depends(get_current_user)):
    """流式对话（SSE）。"""
    async def gen():
        async for chunk in chat_service.chat_stream(
            session_id=req.session_id or "", message=req.message,
            user_id=user["user_id"], channel=req.channel,
            visitor_ip=_client_ip(request),
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/external", response_model=ApiResponse[ChatResponse])
async def chat_external(req: ChatRequest, request: Request,
                        key_user: dict = Depends(get_api_key_user)):
    """对外开放对话接口（API Key 鉴权 + 限流）。"""
    result = await chat_service.chat(
        session_id=req.session_id or "", message=req.message,
        user_id=key_user.get("user_id"), channel="api",
        visitor_ip=_client_ip(request),
    )
    return ApiResponse(data=ChatResponse(**result))
