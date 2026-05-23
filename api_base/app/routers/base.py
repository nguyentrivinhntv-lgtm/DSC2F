"""
=============================================================================
Base Router - Health Check & System Info
=============================================================================
Các endpoint cơ bản: kiểm tra trạng thái server, danh sách model.
"""

from fastapi import APIRouter

from app.config import VALID_MODEL_TYPES, get_settings
from chatbot.services.model_service import get_model_service

router = APIRouter(tags=["Base"])


@router.get(
    "/",
    summary="Health Check",
    description="Kiểm tra API server có đang hoạt động không.",
)
def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Trạng thái server và thông tin cơ bản.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "message": "CNN Detection API is running",
        "default_model": settings.DEFAULT_MODEL_TYPE,
        "device": str(get_model_service().device),
    }


@router.get(
    "/models",
    summary="Danh sách model",
    description="Trả về danh sách các model type có sẵn và model đã load.",
)
def list_models():
    """
    Liệt kê các model type hỗ trợ.

    Returns:
        dict: Danh sách model available và đã loaded.
    """
    service = get_model_service()
    settings = get_settings()
    return {
        "available_models": sorted(VALID_MODEL_TYPES),
        "loaded_models": service.loaded_models,
        "default_model": settings.DEFAULT_MODEL_TYPE,
    }
