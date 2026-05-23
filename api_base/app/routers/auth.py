"""
=============================================================================
Auth Router - Đăng ký & Đăng nhập
=============================================================================
API endpoints cho authentication:
  - POST /auth/register : Tạo tài khoản mới
  - POST /auth/login    : Đăng nhập, trả về JWT token
"""

import hashlib
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.models.base_db import add_prediction_tokens, create_user, get_user_by_username
from app.config import get_settings
from app.security.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Schema cho request đăng ký."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Tên đăng nhập (3-50 ký tự)."
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Mật khẩu (tối thiểu 6 ký tự)."
    )


class LoginRequest(BaseModel):
    """Schema cho request đăng nhập."""
    username: str = Field(..., description="Tên đăng nhập.")
    password: str = Field(..., description="Mật khẩu.")


class TokenResponse(BaseModel):
    """Schema cho response chứa JWT token."""
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field(default="bearer", description="Loại token.")
    username: str = Field(..., description="Username đã đăng nhập.")
    role: str = Field(default="user", description="Vai trò (user/admin).")
    prediction_tokens: int = Field(default=0, description="Số token prediction còn lại.")


class RegisterResponse(BaseModel):
    """Schema cho response đăng ký thành công."""
    message: str
    username: str
    prediction_tokens: int


class GoogleConfigResponse(BaseModel):
    """Schema trả về config Google Sign-In cho frontend."""
    enabled: bool
    client_id: str = ""


class GoogleLoginRequest(BaseModel):
    """Schema cho request Google login từ frontend (GIS credential)."""
    credential: str = Field(..., min_length=10, description="Google ID token credential.")


class AdminTopUpTokensRequest(BaseModel):
    """Schema cho request admin nạp token cho user."""
    username: str = Field(..., min_length=3, max_length=50)
    amount: int = Field(..., gt=0, le=100000)


class AdminTopUpTokensResponse(BaseModel):
    """Schema response khi admin nạp token thành công."""
    message: str
    username: str
    added_tokens: int
    prediction_tokens: int


def _build_google_username(email: str) -> str:
    """
    Tạo username ổn định từ email Google, đảm bảo <= 50 ký tự.
    """
    email = email.strip().lower()
    if len(email) <= 50:
        return email

    local = email.split("@")[0][:36]
    suffix = hashlib.sha1(email.encode("utf-8")).hexdigest()[:8]
    return f"{local}_{suffix}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
    description="Tạo tài khoản mới với username và password.",
)
def register(request: RegisterRequest):
    """
    Đăng ký tài khoản mới.

    Args:
        request: Username và password.

    Returns:
        RegisterResponse: Thông báo thành công.

    Raises:
        HTTPException 400: Nếu username đã tồn tại.
    """
    # Kiểm tra username đã tồn tại chưa
    existing = get_user_by_username(request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' đã được sử dụng.",
        )

    # Hash password và tạo user
    hashed = hash_password(request.password)
    try:
        create_user(request.username, hashed, prediction_tokens=5)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return RegisterResponse(
        message="Đăng ký thành công!",
        username=request.username,
        prediction_tokens=5,
    )


@router.get(
    "/google/config",
    response_model=GoogleConfigResponse,
    summary="Google Sign-In config",
    description="Trả về trạng thái bật/tắt đăng nhập Google và client ID cho frontend.",
)
def google_config():
    settings = get_settings()
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    return GoogleConfigResponse(
        enabled=bool(client_id),
        client_id=client_id,
    )


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Đăng nhập bằng Google",
    description="Xác thực Google credential, tự động tạo user nếu chưa tồn tại và trả JWT token.",
)
def login_google(request: GoogleLoginRequest):
    settings = get_settings()
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In chưa được cấu hình trên server.",
        )

    try:
        id_info = id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            client_id,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token không hợp lệ hoặc đã hết hạn.",
        )

    email = (id_info.get("email") or "").strip().lower()
    email_verified = bool(id_info.get("email_verified", False))

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account không trả về email.",
        )

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email Google chưa được xác thực.",
        )

    username = _build_google_username(email)
    user = get_user_by_username(username)

    if not user:
        auto_password = hash_password(f"google::{uuid4().hex}{uuid4().hex}")
        user = create_user(
            username=username,
            hashed_password=auto_password,
            role="user",
            prediction_tokens=5,
        )

    token = create_access_token(data={"sub": str(user["id"])})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user["username"],
        role=user.get("role", "user"),
        prediction_tokens=int(user.get("prediction_tokens", 0)),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập",
    description="Đăng nhập bằng username/password, nhận JWT token.",
)
def login(request: LoginRequest):
    """
    Đăng nhập và nhận JWT token.

    Args:
        request: Username và password.

    Returns:
        TokenResponse: JWT access token.

    Raises:
        HTTPException 401: Nếu username/password sai.
    """
    user = get_user_by_username(request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username hoặc password không đúng.",
        )

    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username hoặc password không đúng.",
        )

    # Tạo JWT token
    token = create_access_token(data={"sub": str(user["id"])})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user["username"],
        role=user.get("role", "user"),
        prediction_tokens=int(user.get("prediction_tokens", 0)),
    )


@router.post(
    "/admin/tokens/topup",
    response_model=AdminTopUpTokensResponse,
    summary="Admin nạp token cho user",
    description="Chỉ admin mới được phép nạp thêm prediction token cho user.",
)
def admin_topup_tokens(
    request: AdminTopUpTokensRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có quyền nạp token.",
        )

    try:
        updated_user = add_prediction_tokens(request.username, request.amount)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy user '{request.username}'.",
        )

    return AdminTopUpTokensResponse(
        message="Nạp token thành công.",
        username=updated_user["username"],
        added_tokens=request.amount,
        prediction_tokens=int(updated_user.get("prediction_tokens", 0)),
    )
