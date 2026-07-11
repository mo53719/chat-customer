"""认证路由：登录 / 注册。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.security.auth import create_token, hash_password, verify_password
from app.storage.sqlite.repositories.user_repo import user_repo
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse[TokenResponse])
async def register(req: RegisterRequest):
    existing = await user_repo.get_by_username(req.username)
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "用户名已存在")
    uid = await user_repo.create(req.username, hash_password(req.password),
                                  role=req.role, nickname=req.nickname)
    token = create_token(uid, req.username, req.role)
    return ApiResponse(data=TokenResponse(access_token=token, username=req.username,
                                          role=req.role, user_id=uid))


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(req: LoginRequest):
    user = await user_repo.get_by_username(req.username)
    if not user or not verify_password(req.password, user.password_hash if hasattr(user, "password_hash") else ""):
        # 注意：UserDTO 未带 password_hash，直接查原行
        from app.storage.sqlite.connection import SqliteConnection
        row = await SqliteConnection.fetchone(
            "SELECT password_hash FROM users WHERE username=? AND deleted_at IS NULL",
            (req.username,),
        )
        if not row or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    token = create_token(user.id, user.username, user.role)
    return ApiResponse(data=TokenResponse(access_token=token, username=user.username,
                                          role=user.role, user_id=user.id))
