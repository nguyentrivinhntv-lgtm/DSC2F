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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.models.base_db import (
    add_prediction_tokens, 
    create_user, 
    get_user_by_username, 
    get_user_by_email,
    save_email_otp,
    verify_email_otp,
    update_user_password,
    update_user_password_by_username
)
from app.config import get_settings
from app.services.email_service import send_otp_email
from app.security.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
import random

def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to check if current user is admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có quyền thực hiện thao tác này."
        )
    return current_user

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
    email: str = Field(
        ...,
        max_length=100,
        description="Địa chỉ email hợp lệ."
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Mật khẩu (tối thiểu 6 ký tự)."
    )
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Mã OTP gửi về email."
    )

class RequestRegisterRequest(BaseModel):
    """Schema yêu cầu gửi mã OTP để đăng ký."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)


class LoginRequest(BaseModel):
    """Schema cho request đăng nhập."""
    username: str = Field(..., description="Tên đăng nhập hoặc Email.")
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


class MeResponse(BaseModel):
    """Schema cho /auth/me."""
    id: int
    username: str
    email: Optional[str] = None
    role: str
    prediction_tokens: int
    is_active: bool


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


class AdminUpdateRoleRequest(BaseModel):
    """Schema cho request admin đổi quyền user."""
    username: str = Field(..., min_length=3, max_length=50)
    new_role: str = Field(..., description="Vai trò mới (user/admin).")



class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., max_length=100)


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., max_length=100)
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Mật khẩu cũ")
    new_password: str = Field(..., min_length=6, max_length=100, description="Mật khẩu mới")


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
    "/request-register",
    summary="Yêu cầu đăng ký tài khoản (Gửi OTP)",
    description="Kiểm tra username/email và gửi mã OTP xác nhận.",
)
def request_register(request: RequestRegisterRequest):
    # Kiểm tra username đã tồn tại chưa
    existing_user = get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' đã được sử dụng.",
        )

    # Kiểm tra email đã tồn tại chưa
    existing_email = get_user_by_email(request.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{request.email}' đã được sử dụng.",
        )

    # Tạo mã OTP 6 số
    otp_code = str(random.randint(100000, 999999))
    save_email_otp(request.email, otp_code)
    
    # Gửi email
    send_otp_email(request.email, otp_code, purpose='register')
    
    return {"message": "Mã xác thực đã được gửi đến email của bạn."}


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
    description="Xác thực OTP và tạo tài khoản mới.",
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
    existing_user = get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' đã được sử dụng.",
        )

    # Kiểm tra email đã tồn tại chưa
    existing_email = get_user_by_email(request.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{request.email}' đã được sử dụng.",
        )

    # Kiểm tra mã OTP
    is_valid = verify_email_otp(request.email, request.otp_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không hợp lệ hoặc đã hết hạn."
        )

    # Hash password và tạo user
    hashed = hash_password(request.password)
    try:
        create_user(request.username, hashed, email=request.email, prediction_tokens=5)
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


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Lấy thông tin User hiện tại",
    description="Trả về thông tin user mới nhất bao gồm số lượng prediction_tokens.",
)
def get_me(current_user: dict = Depends(get_current_user)):
    return MeResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user.get("email"),
        role=current_user["role"],
        prediction_tokens=current_user["prediction_tokens"],
        is_active=current_user.get("is_active", True),
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
    user = None
    if "@" in request.username:
        user = get_user_by_email(request.username)
    
    if not user:
        user = get_user_by_username(request.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username, Email hoặc Password không đúng.",
        )

    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username, Email hoặc Password không đúng.",
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


@router.get(
    "/admin/users",
    summary="Lấy danh sách tất cả user",
    description="Chỉ admin mới được phép xem danh sách user.",
)
def admin_get_users(current_user: dict = Depends(get_current_user)):
    from app.models.base_db import get_all_users
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có quyền xem danh sách user.",
        )
    return get_all_users()


@router.post(
    "/admin/users/role",
    summary="Thay đổi quyền user",
    description="Chỉ admin mới được thay đổi quyền. Bảo vệ tài khoản 'admin'.",
)
def admin_set_role(
    request: AdminUpdateRoleRequest,
    current_user: dict = Depends(get_current_user),
):
    from app.models.base_db import update_user_role
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có quyền phân quyền.",
        )
    
    target_username = request.username
    new_role = request.new_role
    
    if new_role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Quyền không hợp lệ.")
        
    # Logic bảo vệ tài khoản 'admin'
    if target_username == "admin" and current_user.get("username") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thay đổi chức vụ của Super Admin (admin)."
        )

    # Chống tự hạ quyền chính mình nếu là admin duy nhất, nhưng ở đây tạm cho phép tự do trừ 'admin'
    if target_username == "admin" and new_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không thể hạ quyền của tài khoản Super Admin."
        )
        
    target_user = get_user_by_username(target_username)
    if not target_user:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy user '{target_username}'.")
        
    update_user_role(target_username, new_role)
    return {"message": f"Cập nhật thành công. Tài khoản '{target_username}' hiện có quyền '{new_role}'."}


@router.post(
    "/forgot-password",
    summary="Yêu cầu khôi phục mật khẩu",
    description="Tạo và gửi mã OTP 6 số về email.",
)
def forgot_password(request: ForgotPasswordRequest):
    user = get_user_by_email(request.email)
    if not user:
        # Giả vờ thành công để chống dò email
        return {"message": "Nếu email tồn tại trong hệ thống, mã OTP sẽ được gửi đi."}
    
    # Tạo mã OTP 6 số
    otp_code = str(random.randint(100000, 999999))
    save_email_otp(request.email, otp_code)
    
    # Gửi email
    send_otp_email(request.email, otp_code)
    
    return {"message": "Mã OTP đã được gửi đến email của bạn. Có hiệu lực 5 phút."}


@router.post(
    "/reset-password",
    summary="Đặt lại mật khẩu bằng OTP",
    description="Xác thực OTP và đặt mật khẩu mới.",
)
def reset_password(request: ResetPasswordRequest):
    user = get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email không tồn tại trong hệ thống."
        )

    is_valid = verify_email_otp(request.email, request.otp_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không hợp lệ hoặc đã hết hạn."
        )
    
    new_hashed = hash_password(request.new_password)
    update_user_password(request.email, new_hashed)
    
    return {"message": "Đặt lại mật khẩu thành công! Bạn có thể đăng nhập bằng mật khẩu mới."}


@router.post(
    "/change-password",
    summary="Đổi mật khẩu",
    description="Cho phép user đang đăng nhập đổi mật khẩu của chính mình.",
)
def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    user = get_user_by_username(current_user["username"])
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại.")
        
    if not verify_password(request.old_password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không chính xác."
        )
        
    new_hashed = hash_password(request.new_password)
    update_user_password_by_username(current_user["username"], new_hashed)
    
    return {"message": "Đổi mật khẩu thành công!"}
