"""
=============================================================================
Base Router - Health Check & System Info
=============================================================================
Các endpoint cơ bản: kiểm tra trạng thái server, danh sách model.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
import os
import uuid
import requests

from app.config import VALID_MODEL_TYPES, get_settings
from app.models.base_db import (
    get_all_models_config, update_model_status, is_model_active,
    get_site_config, update_site_config, reset_site_config,
)
from app.routers.auth import get_current_user
from chatbot.services.model_service import get_model_service

router = APIRouter(tags=["Base"])

class ToggleModelRequest(BaseModel):
    model_type: str
    is_active: bool


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
    Liệt kê các model type hỗ trợ (chỉ trả về những model đang active).

    Returns:
        dict: Danh sách model available và đã loaded.
    """
    service = get_model_service()
    settings = get_settings()
    
    # Lọc ra các model đang được bật
    active_models = [m for m in VALID_MODEL_TYPES if is_model_active(m)]
    
    return {
        "available_models": sorted(active_models),
        "loaded_models": service.loaded_models,
        "default_model": settings.DEFAULT_MODEL_TYPE,
    }


@router.get(
    "/admin/models",
    summary="Danh sách cấu hình model cho admin",
    description="Trả về trạng thái bật/tắt của tất cả model.",
)
def admin_list_models(current_user: dict = Depends(get_current_user)):
    """
    Lấy danh sách model kèm trạng thái is_active. Yêu cầu quyền admin.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền xem.")
        
    configs = get_all_models_config()
    # configs format: [{'model_type': 'resnet50', 'is_active': 1}, ...]
    config_dict = {c["model_type"]: bool(c["is_active"]) for c in configs}
    
    # Kết hợp với VALID_MODEL_TYPES để đảm bảo tất cả model đều có trạng thái
    result = []
    for m in VALID_MODEL_TYPES:
        result.append({
            "model_type": m,
            "is_active": config_dict.get(m, True) # Mặc định true nếu chưa lưu DB
        })
        
    return {"models": result}


@router.post(
    "/admin/models/toggle",
    summary="Bật/Tắt model",
    description="Thay đổi trạng thái kích hoạt của một model.",
)
def admin_toggle_model(req: ToggleModelRequest, current_user: dict = Depends(get_current_user)):
    """
    Bật tắt model. Yêu cầu quyền admin.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
        
    if req.model_type not in VALID_MODEL_TYPES:
        raise HTTPException(status_code=400, detail="Model không hợp lệ.")
        
    success = update_model_status(req.model_type, req.is_active)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể cập nhật trạng thái model.")
        
    return {"message": f"Đã {'bật' if req.is_active else 'tắt'} model {req.model_type}"}


# ====================== SITE CONFIG ======================

@router.get(
    "/site-config",
    summary="Lấy cấu hình giao diện website",
    description="Public endpoint - trả về toàn bộ config cho frontend.",
)
def public_get_site_config():
    """Trả về toàn bộ site config cho frontend render."""
    config = get_site_config()
    # Loại bỏ các key bảo mật
    keys_to_remove = [k for k in config.keys() if k.startswith("ai_") and k.endswith("_key")]
    for k in keys_to_remove:
        config.pop(k, None)
    return config

@router.get(
    "/admin/site-config",
    summary="Lấy toàn bộ cấu hình giao diện (Admin)",
    description="Trả về toàn bộ config bao gồm cả API Keys.",
)
def admin_get_site_config(current_user: dict = Depends(get_current_user)):
    """Trả về toàn bộ site config cho Admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
    return get_site_config()


@router.put(
    "/admin/site-config",
    summary="Cập nhật cấu hình giao diện",
    description="Admin cập nhật giao diện website.",
)
async def admin_update_site_config(
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Cập nhật site config. Yêu cầu quyền admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
    update_site_config(data)
    return {"message": "Đã cập nhật cấu hình giao diện.", "config": get_site_config()}


@router.post(
    "/admin/site-config/reset",
    summary="Khôi phục cấu hình mặc định",
    description="Reset toàn bộ giao diện về giá trị ban đầu.",
)
def admin_reset_site_config(current_user: dict = Depends(get_current_user)):
    """Khôi phục toàn bộ config về mặc định. Yêu cầu quyền admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
    config = reset_site_config()
    return {"message": "Đã khôi phục cấu hình mặc định.", "config": config}


@router.post(
    "/admin/upload-image",
    summary="Upload ảnh (logo, banner)",
    description="Admin upload ảnh cho giao diện website.",
)
async def admin_upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload ảnh. Yêu cầu quyền admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")

    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/webp", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file ảnh (PNG, JPG, WEBP, SVG).")

    # Save file
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1] or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Return URL path relative to static serving
    return {"url": f"/uploads/{filename}", "filename": filename}
class AITranslateRequest(BaseModel):
    title: str
    content: str

@router.post(
    "/admin/ai-translate",
    summary="Dịch nội dung bằng AI",
    description="Gọi API AI tương ứng để dịch HTML sang tiếng Anh.",
)
def admin_ai_translate(
    req: AITranslateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Dịch bằng AI."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
        
    config = get_site_config()
    provider = config.get("ai_provider", "groq")
    system_prompt = config.get("ai_system_prompt", "Translate to English. Keep HTML tags.")
    
    user_prompt = f"Title:\n{req.title}\n\nContent:\n{req.content}"
    
    try:
        if provider == "groq":
            key = config.get("ai_groq_key")
            if not key: raise ValueError("Chưa cấu hình Groq API Key")
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "llama3-8b-8192",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                },
                timeout=30
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            
        elif provider == "openai":
            key = config.get("ai_openai_key")
            if not key: raise ValueError("Chưa cấu hình OpenAI API Key")
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                },
                timeout=30
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            
        elif provider == "gemini":
            key = config.get("ai_gemini_key")
            if not key: raise ValueError("Chưa cấu hình Gemini API Key")
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
                headers={"Content-Type": "application/json"},
                json={
                    "system_instruction": {
                        "parts": [{"text": system_prompt}]
                    },
                    "contents": [{
                        "parts": [{"text": user_prompt}]
                    }]
                },
                timeout=30
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            raise ValueError(f"Provider {provider} không được hỗ trợ")
            
        # Tách Title và Content
        parts = text.split("Content:", 1)
        if len(parts) > 1:
            title_en = parts[0].replace("Title:", "").strip()
            content_en = parts[1].strip()
        else:
            title_en = req.title + " (Translated)"
            content_en = text.strip()
            
        return {"title_en": title_en, "content_en": content_en}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi dịch bằng {provider}: {str(e)}")
