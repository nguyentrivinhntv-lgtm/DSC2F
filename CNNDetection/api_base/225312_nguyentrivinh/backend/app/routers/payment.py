from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging

from app.config import get_settings
from app.utils.vnpay import vnpay
from app.models.base_db import _get_connection, save_payment_log, get_site_config
from app.security.security import get_current_user
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["Payment"])

class PaymentRequest(BaseModel):
    package_name: str = Field(..., min_length=1, max_length=50, description="Tên gói token (ví dụ: Gói Cơ Bản)")

@router.post("/create_payment_url")
@limiter.limit("5/minute")
async def create_payment_url(request: Request, body: PaymentRequest, current_user: dict = Depends(get_current_user)):
    settings = get_settings()
    site_config = get_site_config()
    
    # --- BẢO MẬT: Backend tự tra bảng giá từ Database ---
    try:
        packages = json.loads(site_config.get("token_packages") or "[]")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Cấu hình bảng giá không hợp lệ.")

    # Tìm gói nạp theo package_name
    package = next((p for p in packages if str(p.get("name")) == str(body.package_name)), None)
    if not package:
        raise HTTPException(
            status_code=400,
            detail=f"Gói nạp '{body.package_name}' không tồn tại."
        )

    amount = int(package["price"])
    tokens_to_add = int(package["tokens"])

    if amount <= 0 or tokens_to_add <= 0:
        raise HTTPException(status_code=400, detail="Gói nạp không hợp lệ.")

    tmn_code = site_config.get("vnpay_tmn_code") or ""
    hash_secret = site_config.get("vnpay_hash_secret") or ""
    payment_url = site_config.get("vnpay_payment_url") or "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    return_url = site_config.get("vnpay_return_url") or "http://localhost:8000/payment/vnpay_return"

    user_id = current_user["id"]
    order_id = f"ORDER_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{tokens_to_add}"
    
    vnp = vnpay()
    vnp.requestData['vnp_Version'] = '2.1.0'
    vnp.requestData['vnp_Command'] = 'pay'
    vnp.requestData['vnp_TmnCode'] = tmn_code
    vnp.requestData['vnp_Amount'] = str(amount * 100) # VNPay nhân 100
    vnp.requestData['vnp_CurrCode'] = 'VND'
    vnp.requestData['vnp_TxnRef'] = order_id
    vnp.requestData['vnp_OrderInfo'] = f"Nap {tokens_to_add} token phan tich anh"
    vnp.requestData['vnp_OrderType'] = 'billpayment'
    vnp.requestData['vnp_Locale'] = 'vn'
    vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp.requestData['vnp_IpAddr'] = getattr(request.client, 'host', '127.0.0.1')
    vnp.requestData['vnp_ReturnUrl'] = return_url
    
    vnpay_payment_url = vnp.get_payment_url(payment_url, hash_secret)
    return {"payment_url": vnpay_payment_url}


@router.get("/vnpay_return")
async def vnpay_return(request: Request):
    settings = get_settings()
    site_config = get_site_config()
    hash_secret = site_config.get("vnpay_hash_secret") or ""

    inputData = request.query_params
    vnp = vnpay()
    vnp.responseData = dict(inputData)
    order_id = inputData.get('vnp_TxnRef')
    vnp_ResponseCode = inputData.get('vnp_ResponseCode')

    if vnp.validate_response(hash_secret):
        if vnp_ResponseCode == "00":
            # 1. Tách thông tin từ order_id (Format: ORDER_{user_id}_{time}_{tokens})
            parts = order_id.split('_')
            user_id = int(parts[1])
            tokens_to_add = int(parts[3])
            
            # 2. Cộng Token vào cơ sở dữ liệu
            conn = _get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET prediction_tokens = prediction_tokens + %s WHERE id = %s",
                        (tokens_to_add, user_id)
                    )
                conn.commit()

                bank_code = inputData.get("vnp_BankCode")
                card_type = inputData.get("vnp_CardType")
                vnp_transaction_no = inputData.get("vnp_TransactionNo")
                amount_paid = int(inputData.get('vnp_Amount', '0')) // 100

                save_payment_log(
                    user_id=user_id,
                    order_id=order_id,
                    amount=amount_paid,
                    tokens=tokens_to_add,
                    bank_code=bank_code,
                    card_type=card_type,
                    vnp_transaction_no=vnp_transaction_no
                )
            finally:
                conn.close()

            # 3. Tạo thông báo in-app
            try:
                from app.models.base_db import create_notification
                create_notification(
                    user_id=user_id,
                    title="Nạp token thành công!",
                    message=f"Bạn đã nhận được {tokens_to_add} token từ giao dịch {order_id}. Số tiền: {amount_paid:,} VND.",
                    ntype="payment",
                )
            except Exception as e:
                print(f"Lỗi tạo notification: {e}")

            # 4. Gửi email xác nhận
            try:
                from app.models.base_db import get_user_by_id as get_user
                from app.services.email_service import send_payment_success_email
                payment_user = get_user(user_id)
                if payment_user and payment_user.get('email'):
                    send_payment_success_email(
                        to_email=payment_user['email'],
                        username=payment_user['username'],
                        tokens=tokens_to_add,
                        amount=amount_paid,
                        order_id=order_id,
                    )
            except Exception as e:
                print(f"Lỗi gửi email thanh toán: {e}")

            # 5. Chuyển hướng người dùng về Frontend kèm thông báo thành công
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/app.html?payment=success&tokens={tokens_to_add}")
        else:
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/app.html?payment=failed")
    else:
        # Sai chữ ký
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/app.html?payment=invalid_signature")