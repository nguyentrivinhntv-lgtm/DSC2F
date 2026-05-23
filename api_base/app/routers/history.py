"""
=============================================================================
History Router - CNN Detection API
=============================================================================
API endpoints cho phép xem lại lịch sử nhận diện của user.
Admin có thể xem được tất cả lịch sử hệ thống.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.base_db import get_prediction_history
from app.security.security import get_current_user

router = APIRouter(prefix="/history", tags=["History"])

# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class PredictionLogResponse(BaseModel):
    id: int
    user_id: int
    username: str
    filename: str
    model_type: str
    probability: float
    label: str
    created_at: str

class HistoryResponse(BaseModel):
    items: List[PredictionLogResponse]
    total: int
    is_admin: bool

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=HistoryResponse,
    summary="Lấy lịch sử prediction",
    description="User thông thường xem lịch sử cá nhân. Admin sẽ xem tất cả.",
)
def get_history(current_user: dict = Depends(get_current_user)):
    """
    Lấy danh sách lịch sử prediction.
    """
    is_admin = current_user.get("role") == "admin"
    user_id = current_user["id"]
    
    # Lấy dữ liệu từ db
    logs = get_prediction_history(user_id=user_id, is_admin=is_admin)
    
    # Format
    results = []
    for row in logs:
        results.append(PredictionLogResponse(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            filename=row["filename"],
            model_type=row["model_type"],
            probability=row["probability"],
            label=row["label"],
            created_at=row["created_at"],
        ))
        
    return HistoryResponse(
        items=results,
        total=len(results),
        is_admin=is_admin
    )
