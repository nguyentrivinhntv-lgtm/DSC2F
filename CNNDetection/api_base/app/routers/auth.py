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

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, Field, field_validator
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
    update_user_password_by_username,
    get_site_config
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
import re
from app.limiter import limiter


def _validate_password_strength(password: str) -> str:
    """Kiểm tra mật khẩu phải có chữ, số và ký tự đặc biệt."""
    if not re.search(r'[A-Za-z]', password):
        raise ValueError('Mật khẩu phải chứa ít nhất 1 chữ cái (a-z, A-Z)')
    if not re.search(r'[0-9]', password):
        raise ValueError('Mật khẩu phải chứa ít nhất 1 chữ số (0-9)')
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]', password):
        raise ValueError('Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt (!@#$%^&*...)')
    return password

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
        description="Mật khẩu (tối thiểu 6 ký tự, phải có chữ + số + ký tự đặc biệt)."
    )
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Mã OTP gửi về email."
    )

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        return _validate_password_strength(v)

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

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Mật khẩu cũ")
    new_password: str = Field(..., min_length=6, max_length=100, description="Mật khẩu mới")

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        return _validate_password_strength(v)


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
@limiter.limit("5/minute")
def register(request: Request, body: RegisterRequest, response: Response):
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
    existing_user = get_user_by_username(body.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{body.username}' đã được sử dụng.",
        )

    # Kiểm tra email đã tồn tại chưa
    existing_email = get_user_by_email(body.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{body.email}' đã được sử dụng.",
        )

    # Kiểm tra mã OTP
    is_valid = verify_email_otp(body.email, body.otp_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không hợp lệ hoặc đã hết hạn."
        )

    # Hash password và tạo user
    hashed = hash_password(body.password)
    try:
        create_user(body.username, hashed, email=body.email, prediction_tokens=5)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Tự động cấp token (để tránh phải login lại, tuỳ nhu cầu)
    # Tuy nhiên response model hiện tại là RegisterResponse không chứa token.
    # Ta có thể không cần cấp JWT luôn lúc đăng ký, bắt user login.
    # Do đó, chỉ cần return RegisterResponse như cũ.

    return RegisterResponse(
        message="Đăng ký thành công!",
        username=body.username,
        prediction_tokens=5,
    )


@router.get(
    "/google/config",
    response_model=GoogleConfigResponse,
    summary="Google Sign-In config",
    description="Trả về trạng thái bật/tắt đăng nhập Google và client ID cho frontend.",
)
def google_config():
    client_id = (get_site_config().get("google_client_id") or "").strip()
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
def login_google(request: GoogleLoginRequest, response: Response):
    client_id = (get_site_config().get("google_client_id") or "").strip()
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
            email=email,
            role="user",
            prediction_tokens=5,
        )

    token = create_access_token(data={"sub": str(user["id"])})
    
    # Thiết lập HttpOnly Cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True, # Đảm bảo HTTPS khi production
        samesite="lax",
        max_age=1440 * 60, # 24 tiếng
    )
    
    return TokenResponse(
        access_token=token, # Vẫn trả về ở payload để frontend có thể bỏ qua nếu muốn, nhưng frontend sẽ KHÔNG lưu localStorage nữa
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
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, response: Response):
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
    if "@" in body.username:
        user = get_user_by_email(body.username)
    
    if not user:
        user = get_user_by_username(body.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username, Email hoặc Password không đúng.",
        )

    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username, Email hoặc Password không đúng.",
        )

    # Tạo JWT token
    token = create_access_token(data={"sub": str(user["id"])})

    # Thiết lập HttpOnly Cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=1440 * 60,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user["username"],
        role=user.get("role", "user"),
        prediction_tokens=int(user.get("prediction_tokens", 0)),
    )

@router.post(
    "/logout",
    summary="Đăng xuất",
    description="Xóa JWT Cookie để đăng xuất.",
)
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Đã đăng xuất thành công."}


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
@limiter.limit("3/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest):
    user = get_user_by_email(body.email)
    if not user:
        # Giả vờ thành công để chống dò email
        return {"message": "Nếu email tồn tại trong hệ thống, mã OTP sẽ được gửi đi."}
    
    # Tạo mã OTP 6 số
    otp_code = str(random.randint(100000, 999999))
    save_email_otp(body.email, otp_code)
    
    # Gửi email
    send_otp_email(body.email, otp_code)
    
    return {"message": "Mã OTP đã được gửi đến email của bạn. Có hiệu lực 5 phút."}


@router.post(
    "/reset-password",
    summary="Đặt lại mật khẩu bằng OTP",
    description="Xác thực OTP và đặt mật khẩu mới.",
)
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest):
    user = get_user_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email không tồn tại trong hệ thống."
        )

    is_valid = verify_email_otp(body.email, body.otp_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không hợp lệ hoặc đã hết hạn."
        )
    
    new_hashed = hash_password(body.new_password)
    update_user_password(body.email, new_hashed)
    
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


@router.delete(
    "/me",
    summary="Xóa tài khoản hiện tại",
    description="Xóa mềm (vô hiệu hóa) tài khoản người dùng đang đăng nhập.",
)
def soft_delete_my_account(current_user: dict = Depends(get_current_user)):
    from app.models.base_db import _get_connection
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_active = 0 WHERE id = %s", (current_user["id"],))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa tài khoản: {str(e)}")
    finally:
        conn.close()
    return {"message": "Tài khoản của bạn đã được xóa thành công."}

# =============================================================================
# HYBRID APP CLOUD-SYNC LOGIN (FLUTTER WEBVIEW)
# =============================================================================

from fastapi import Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.models.base_db import (
    create_login_session,
    get_login_session,
    update_login_session,
    delete_login_session,
    cleanup_old_login_sessions,
    get_user_by_id
)
import urllib.parse
import requests

@router.post("/login-session")
def api_create_login_session(session_id: str = Form(...)):
    """Frontend khởi tạo một phiên đăng nhập (cho App Android)."""
    cleanup_old_login_sessions()
    success = create_login_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể tạo phiên chờ.")
    return {"message": "Đã tạo phiên", "session_id": session_id}

@router.get("/login-session/{session_id}")
def api_check_login_session(session_id: str):
    """Frontend gọi hàm này (polling) liên tục để check trạng thái đăng nhập."""
    session = get_login_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Phiên chờ đã hết hạn hoặc không tồn tại.")
        
    if session["status"] == "completed" and session["token"]:
        # Xóa phiên ngay sau khi trả về Token để đảm bảo dùng 1 lần (One-time use)
        delete_login_session(session_id)
        
        # Giả lập lại user profile từ DB hoặc trả về token (frontend tự lưu)
        from jose import jwt
        settings = get_settings()
        payload = jwt.decode(session["token"], settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        user_id = int(payload.get("sub"))
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User không tồn tại.")
            
        return {
            "status": "completed",
            "token": session["token"],
            "user": {
                "username": user["username"],
                "role": user["role"]
            }
        }
        
    return {"status": session["status"]}

from fastapi import Request

@router.get("/google/login/flutter")
def api_google_login_flutter(session_id: str, request: Request):
    """App WebView sẽ mở link này. Nó sẽ chuyển hướng người dùng sang trang Đăng nhập của Google."""
    client_id = get_site_config().get("google_client_id")
    if not client_id:
        return HTMLResponse("<h2>Hệ thống chưa cấu hình GOOGLE_CLIENT_ID. Hãy báo Admin!</h2>")
    
    # Xác định đường dẫn callback tự động
    base_url = str(request.base_url).rstrip('/')
    # Thường request.base_url trả về http://localhost:8000
    redirect_uri = f"{base_url}/auth/google/callback/flutter"
    
    # Sinh URL Google OAuth 2.0 (Dùng Implicit Flow để lấy id_token nếu ko có Secret, hoặc Authorization Code)
    # Vì Frontend GIS gửi thẳng `id_token`, ta có thể thử yêu cầu Google trả về thẳng `id_token` (Implicit Flow) qua URL Hash
    # Tuy nhiên, Implicit flow (response_type=id_token) không truyền state tới server (nó nằm ở Hash).
    # Buộc phải dùng `response_type=code` và có `client_secret` để lấy lại JWT, HOẶC trả về một trang web trung gian thu thập id_token.
    
    # Ở đây dùng trang web tĩnh chứa Google Signin, hoặc Form redirect:
    # Do policy của Google WebView không cho popup, nên dùng redirect.
    # Phương án an toàn: Chuyển thẳng về Google với response_type=code. Nếu không có SECRET, đoạn sau sẽ lỗi.
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        f"state={session_id}&"
        "access_type=online"
    )
    return RedirectResponse(auth_url)

@router.get("/google/callback/flutter")
def api_google_callback_flutter(state: str, code: Optional[str] = None, request: Request = None):
    """Callback nhận authorization_code từ Google, đổi lấy id_token và đăng nhập."""
    if not code:
        return HTMLResponse("<h2>Đăng nhập thất bại hoặc bị hủy. Hãy đóng tab này.</h2>")
        
    client_secret = get_site_config().get("google_client_secret")
    
    if not client_secret:
        return HTMLResponse("<h2>Hệ thống chưa cấu hình GOOGLE_CLIENT_SECRET. Hãy báo Admin!</h2>")
    
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/google/callback/flutter"
    
    # Đổi Code lấy Token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": get_site_config().get("google_client_id"),
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    res = requests.post(token_url, data=data)
    if not res.ok:
        return HTMLResponse(f"<h2>Lỗi chứng thực từ Google: {res.text}</h2>")
        
    token_data = res.json()
    id_token_jwt = token_data.get("id_token")
    if not id_token_jwt:
        return HTMLResponse("<h2>Không nhận được id_token từ Google.</h2>")
        
    # --- Xác thực ID Token y như login_google() ---
    try:
        from google.oauth2 import id_token as g_id_token
        from google.auth.transport import requests as google_requests
        idinfo = g_id_token.verify_oauth2_token(
            id_token_jwt,
            google_requests.Request(),
            get_site_config().get("google_client_id"),
            clock_skew_in_seconds=60
        )
    except Exception as e:
        return HTMLResponse(f"<h2>Token không hợp lệ: {str(e)}</h2>")
        
    email = idinfo.get("email")
    if not email:
        return HTMLResponse("<h2>Không lấy được Email từ Google.</h2>")
        
    # Tái sử dụng logic lấy user hoặc tạo user
    from app.routers.auth import _build_google_username
    username = _build_google_username(email)
    
    user = get_user_by_email(email)
    if not user:
        user = get_user_by_username(username)
        
    if not user:
        from uuid import uuid4
        auto_password = hash_password(f"google::{uuid4().hex}{uuid4().hex}")
        try:
            user = create_user(
                username=username,
                hashed_password=auto_password,
                email=email,
                role="user",
                prediction_tokens=5
            )
        except Exception as e:
            return HTMLResponse(f"<h2>Lỗi tạo tài khoản nội bộ: {str(e)}</h2>")
            
    # Fix bug cũ nếu email bị lưu sai hoặc thiếu
    if user and user.get("email") != email:
        from app.models.base_db import _get_connection
        conn = _get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET email = %s WHERE id = %s", (email, user["id"]))
            conn.commit()
            user["email"] = email
        except:
            pass
        finally:
            conn.close()
    # Tạo JWT của app mình
    access_token = create_access_token(
        data={"sub": str(user["id"]), "role": user["role"]}
    )
    
    # LƯU VÀO DATABASE CHO PHIÊN POLL (state chứa session_id)
    update_login_session(state, access_token)
    
    return HTMLResponse("""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; text-align: center; padding-top: 50px; background: #f0fdf4; color: #166534; }
            .box { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); display: inline-block; }
            h2 { margin-top: 0; }
            p { color: #555; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>Đăng nhập thành công! 🎉</h2>
            <p>Hệ thống đã kết nối tài khoản an toàn.</p>
            <p><strong>Bạn hãy đóng Tab này (hoặc bấm quay lại) để trở về App nhé.</strong></p>
        </div>
    </body>
    </html>
    """)

# =============================================================================
# DELETION REQUESTS
# =============================================================================

from pydantic import BaseModel

class DeletionRequestModel(BaseModel):
    contact_info: str
    reason: str = ""
    note: str = ""

class UpdateDeletionRequestModel(BaseModel):
    status: str

@router.post("/deletion-requests")
def submit_deletion_request(req: DeletionRequestModel):
    from app.models.base_db import create_deletion_request
    success = create_deletion_request(req.contact_info, req.reason, req.note)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể gửi yêu cầu.")
    return {"message": "Gửi yêu cầu xóa tài khoản thành công."}

@router.get("/deletion-requests")
def get_deletion_requests(current_user: dict = Depends(require_admin)):
    from app.models.base_db import get_all_deletion_requests
    return get_all_deletion_requests()

@router.put("/deletion-requests/{req_id}")
def update_deletion_request(req_id: int, payload: UpdateDeletionRequestModel, current_user: dict = Depends(require_admin)):
    from app.models.base_db import update_deletion_request_status, get_all_deletion_requests, _get_connection
    reqs = get_all_deletion_requests()
    req = next((r for r in reqs if r["id"] == req_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
        
    update_deletion_request_status(req_id, payload.status)
    
    # Nếu được duyệt (completed), tìm và vô hiệu hóa tài khoản
    if payload.status == "completed":
        contact = req["contact_info"]
        conn = _get_connection()
        try:
            with conn.cursor() as cur:
                # Cố gắng tìm user theo email hoặc username
                cur.execute("UPDATE users SET is_active = 0 WHERE email = %s OR username = %s OR email = %s", (contact, contact, contact))
            conn.commit()
        except Exception as e:
            pass
        finally:
            conn.close()
            
    return {"message": "Cập nhật thành công."}
