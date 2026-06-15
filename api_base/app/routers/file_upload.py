"""
=============================================================================
File Upload Router - Predict API
=============================================================================
API endpoints cho upload ảnh và chạy prediction:
  - POST /predict       : Upload 1 ảnh → kết quả prediction
  - POST /predict/batch : Upload nhiều ảnh → batch prediction

Tất cả endpoints đều yêu cầu JWT authentication.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.config import VALID_MODEL_TYPES, get_settings
from app.models.base_db import log_prediction, is_model_active
from app.models.base_db import decrement_prediction_tokens
from app.security.security import get_current_user
from app.utils.helpers import (
    cleanup_temp_file,
    generate_unique_filename,
    save_upload_file,
    validate_image_file,
)
from chatbot.services.model_service import get_model_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Prediction"])


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class PredictionResult(BaseModel):
    """Schema cho kết quả prediction 1 ảnh."""
    filename: str = Field(..., description="Tên file ảnh.")
    probability: float = Field(..., description="Xác suất fake (0.0 - 1.0).")
    percentage: str = Field(..., description="Xác suất dạng %.")
    label: str = Field(..., description="Nhãn: 'real' hoặc 'fake'.")
    confidence: str = Field(..., description="Độ tin cậy dạng %.")
    model_used: str = Field(..., description="Model type đã sử dụng.")
    fft_base64: Optional[str] = Field(None, description="Ảnh FFT Encode Base64 để hiển thị.")


class BatchPredictionResponse(BaseModel):
    """Schema cho kết quả batch prediction."""
    total: int = Field(..., description="Tổng số ảnh.")
    results: List[PredictionResult] = Field(..., description="Danh sách kết quả.")
    model_used: str = Field(..., description="Model type đã sử dụng.")
    remaining_tokens: Optional[int] = Field(None, description="Số token còn lại của user.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/predict",
    response_model=PredictionResult,
    summary="Phát hiện ảnh giả",
    description=(
        "Upload 1 ảnh để kiểm tra real/fake. "
        "Trả về xác suất và nhãn dự đoán."
    ),
)
async def predict_single(
    file: UploadFile = File(..., description="File ảnh cần kiểm tra."),
    model_type: Optional[str] = Form(
        default=None,
        description=(
            "Loại model sử dụng. Mặc định từ config. "
            "Các giá trị: resnet50, dual_stream, dual_stream_enhanced, dual_stream_resnet."
        ),
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Predict 1 ảnh - kiểm tra real hay fake.

    Flow:
        1. Validate file ảnh
        2. Lưu tạm + load bằng PIL
        3. Chạy model inference
        4. Log kết quả vào DB
        5. Cleanup file tạm
        6. Trả kết quả

    Args:
        file: File ảnh upload.
        model_type: Loại model (optional).
        current_user: User hiện tại (từ JWT).

    Returns:
        PredictionResult: Kết quả prediction.
    """
    is_admin = current_user.get("role") == "admin"

    # 1. Validate
    if not validate_image_file(file.filename or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File không phải ảnh hợp lệ. Hỗ trợ: jpg, png, bmp, tiff, webp.",
        )

    # Validate model_type
    settings = get_settings()
    selected_model = model_type or settings.DEFAULT_MODEL_TYPE
    if selected_model not in VALID_MODEL_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model type '{selected_model}' không hợp lệ. Chọn: {sorted(VALID_MODEL_TYPES)}",
        )
    if not is_model_active(selected_model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{selected_model}' hiện đang bị tắt bởi hệ thống.",
        )

    if (not is_admin) and int(current_user.get("prediction_tokens", 0)) <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn đã hết token prediction. Vui lòng nạp thêm token để tiếp tục.",
        )

    # 2. Lưu tạm
    file_content = await file.read()
    unique_name = generate_unique_filename(file.filename or "image.jpg")
    temp_path = save_upload_file(file_content, unique_name)

    try:
        # 3. Load ảnh và predict
        from PIL import Image
        image = Image.open(temp_path).convert("RGB")

        service = get_model_service()
        result = service.predict(image, selected_model)

        # 4. Log prediction
        try:
            log_prediction(
                user_id=current_user["id"],
                filename=file.filename or unique_name,
                model_type=selected_model,
                probability=result["probability"],
                label=result["label"],
            )
        except Exception as log_err:
            logger.warning("Failed to log prediction: %s", log_err)

        # 5. Trừ token sau khi prediction thành công
        if not is_admin:
            if not decrement_prediction_tokens(current_user["id"], amount=1):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn đã hết token prediction. Vui lòng nạp thêm token để tiếp tục.",
                )

        # 6. Trả kết quả
        return PredictionResult(
            filename=file.filename or unique_name,
            probability=result["probability"],
            percentage=result["percentage"],
            label=result["label"],
            confidence=result["confidence"],
            model_used=result["model_used"],
            fft_base64=result.get("fft_base64"),
            remaining_tokens=None if is_admin else max(0, int(current_user.get("prediction_tokens", 0)) - 1)
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không tìm thấy weights model: {str(exc)}",
        )
    except Exception as exc:
        logger.error("Prediction error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý ảnh: {str(exc)}",
        )
    finally:
        # 5. Cleanup
        cleanup_temp_file(temp_path)


@router.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    summary="Batch prediction",
    description="Upload nhiều ảnh cùng lúc để kiểm tra real/fake.",
)
async def predict_batch(
    files: List[UploadFile] = File(..., description="Danh sách file ảnh."),
    model_type: Optional[str] = Form(
        default=None,
        description="Loại model sử dụng.",
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Batch prediction - kiểm tra nhiều ảnh cùng lúc.

    Args:
        files: Danh sách file ảnh.
        model_type: Loại model (optional).
        current_user: User hiện tại (từ JWT).

    Returns:
        BatchPredictionResponse: Danh sách kết quả.
    """
    is_admin = current_user.get("role") == "admin"

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần ít nhất 1 file ảnh.",
        )

    if len(files) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tối đa 20 ảnh mỗi lần batch predict.",
        )

    if not is_admin:
        available_tokens = int(current_user.get("prediction_tokens", 0))
        if available_tokens <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn đã hết token prediction. Vui lòng nạp thêm token để tiếp tục.",
            )
        if len(files) > available_tokens:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Bạn chỉ còn {available_tokens} token, nhưng đang gửi {len(files)} ảnh. "
                    "Vui lòng giảm số ảnh hoặc nạp thêm token."
                ),
            )

    settings = get_settings()
    selected_model = model_type or settings.DEFAULT_MODEL_TYPE
    if selected_model not in VALID_MODEL_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model type '{selected_model}' không hợp lệ.",
        )
    if not is_model_active(selected_model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{selected_model}' hiện đang bị tắt bởi hệ thống.",
        )

    results = []
    service = get_model_service()

    for upload_file in files:
        if not validate_image_file(upload_file.filename or ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File '{upload_file.filename or 'unknown'}' không phải ảnh hợp lệ. "
                    "Hỗ trợ: jpg, png, bmp, tiff, webp."
                ),
            )

        file_content = await upload_file.read()
        unique_name = generate_unique_filename(upload_file.filename or "image.jpg")
        temp_path = save_upload_file(file_content, unique_name)

        try:
            from PIL import Image
            image = Image.open(temp_path).convert("RGB")
            result = service.predict(image, selected_model)

            # Log prediction
            try:
                log_prediction(
                    user_id=current_user["id"],
                    filename=upload_file.filename or unique_name,
                    model_type=selected_model,
                    probability=result["probability"],
                    label=result["label"],
                )
            except Exception:
                pass

            # Trừ 1 token cho mỗi ảnh xử lý thành công
            if not is_admin:
                if not decrement_prediction_tokens(current_user["id"], amount=1):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn đã hết token prediction trong lúc batch đang chạy.",
                    )

            results.append(PredictionResult(
                filename=upload_file.filename or unique_name,
                probability=result["probability"],
                percentage=result["percentage"],
                label=result["label"],
                confidence=result["confidence"],
                model_used=result["model_used"],
            ))
        except Exception as exc:
            logger.error("Batch predict error for %s: %s", upload_file.filename, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khi xử lý ảnh '{upload_file.filename or 'unknown'}': {str(exc)}",
            )
        finally:
            cleanup_temp_file(temp_path)

    return BatchPredictionResponse(
        total=len(results),
        results=results,
        model_used=selected_model,
        remaining_tokens=None if is_admin else max(0, int(current_user.get("prediction_tokens", 0)) - len(results))
    )
