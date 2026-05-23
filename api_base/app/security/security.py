"""
=============================================================================
Security Module - CNN Detection API
=============================================================================
Xử lý JWT authentication và password hashing.

- Password hashing dùng bcrypt (passlib)
- JWT token dùng python-jose
- Dependency get_current_user cho FastAPI routes
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.models.base_db import get_user_by_id, get_user_by_username

# ---------------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme cho Swagger UI
_bearer_scheme = HTTPBearer(auto_error=True)


def hash_password(plain_password: str) -> str:
    """
    Hash password bằng bcrypt.

    Args:
        plain_password: Password dạng text.

    Returns:
        str: Password đã được hash.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    So sánh password text với hash.

    Args:
        plain_password: Password dạng text.
        hashed_password: Password đã hash.

    Returns:
        bool: True nếu khớp.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT Token
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Tạo JWT access token.

    Args:
        data: Payload data (thường chứa 'sub' = user_id).
        expires_delta: Thời gian hết hạn. Mặc định từ config.

    Returns:
        str: JWT token string.
    """
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Giải mã JWT token.

    Args:
        token: JWT token string.

    Returns:
        dict: Payload data.

    Raises:
        HTTPException: Nếu token không hợp lệ hoặc hết hạn.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token không hợp lệ: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """
    FastAPI dependency - Lấy user hiện tại từ JWT token.

    Sử dụng trong route bằng cách thêm parameter:
        current_user: dict = Depends(get_current_user)

    Args:
        credentials: HTTP Bearer credentials (tự động extract từ header).

    Returns:
        dict: Thông tin user từ database.

    Raises:
        HTTPException 401: Nếu token không hợp lệ hoặc user không tồn tại.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không chứa thông tin user.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User không tồn tại.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa.",
        )

    return dict(user)
