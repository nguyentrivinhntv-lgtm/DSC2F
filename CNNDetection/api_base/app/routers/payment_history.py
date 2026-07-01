"""
=============================================================================
Payment History Router - CNN Detection API
=============================================================================
API endpoint để xem lịch sử mua token.
User thường chỉ thấy của mình. Admin thêm ?all=true để thấy tất cả.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.models.base_db import get_payment_history
from app.security.security import get_current_user

router = APIRouter(prefix="/payment-history", tags=["Payment History"])


class PaymentLogResponse(BaseModel):
    id: int
    user_id: int
    username: str
    order_id: str
    amount: int
    tokens: int
    status: str
    bank_code: Optional[str] = None
    card_type: Optional[str] = None
    vnp_transaction_no: Optional[str] = None
    created_at: str


class PaymentHistoryResponse(BaseModel):
    items: List[PaymentLogResponse]
    total: int
    is_admin: bool


@router.get(
    "/",
    response_model=PaymentHistoryResponse,
    summary="Lấy lịch sử mua token",
    description="User thường xem của mình. Admin thêm ?all=true để xem tất cả.",
)
def get_history(all: bool = False, current_user: dict = Depends(get_current_user)):
    is_admin = current_user.get("role") == "admin"
    fetch_all = is_admin and all
    user_id = current_user["id"]

    rows = get_payment_history(user_id=user_id, is_admin=fetch_all)

    results = []
    for row in rows:
        results.append(PaymentLogResponse(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            order_id=row["order_id"],
            amount=row["amount"],
            tokens=row["tokens"],
            status=row["status"],
            bank_code=row.get("bank_code"),
            card_type=row.get("card_type"),
            vnp_transaction_no=row.get("vnp_transaction_no"),
            created_at=str(row["created_at"]),
        ))

    return PaymentHistoryResponse(
        items=results,
        total=len(results),
        is_admin=is_admin,
    )
