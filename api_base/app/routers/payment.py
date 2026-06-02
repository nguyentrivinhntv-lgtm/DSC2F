from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from datetime import datetime

from app.config import get_settings
from app.utils.vnpay import vnpay
from app.models.base_db import _get_connection
from app.security.security import get_current_user

router = APIRouter(prefix="/payment", tags=["Payment"])

class PaymentRequest(BaseModel):
    amount: int
    tokens: int

@router.post("/create_payment_url")
async def create_payment_url(request: Request, body: PaymentRequest, current_user: dict = Depends(get_current_user)):
    settings = get_settings()
    amount = body.amount
    tokens_to_add = body.tokens
    
    user_id = current_user["id"]
    order_id = f"ORDER_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{tokens_to_add}"
    
    vnp = vnpay()
    vnp.requestData['vnp_Version'] = '2.1.0'
    vnp.requestData['vnp_Command'] = 'pay'
    vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
    vnp.requestData['vnp_Amount'] = str(amount * 100) # VNPay nhân 100
    vnp.requestData['vnp_CurrCode'] = 'VND'
    vnp.requestData['vnp_TxnRef'] = order_id
    vnp.requestData['vnp_OrderInfo'] = f"Nap {tokens_to_add} token phan tich anh"
    vnp.requestData['vnp_OrderType'] = 'billpayment'
    vnp.requestData['vnp_Locale'] = 'vn'
    vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp.requestData['vnp_IpAddr'] = getattr(request.client, 'host', '127.0.0.1')
    vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
    
    vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET)
    return {"payment_url": vnpay_payment_url}


@router.get("/vnpay_return")
async def vnpay_return(request: Request):
    settings = get_settings()
    inputData = request.query_params
    vnp = vnpay()
    vnp.responseData = dict(inputData)
    order_id = inputData.get('vnp_TxnRef')
    vnp_ResponseCode = inputData.get('vnp_ResponseCode')

    if vnp.validate_response(settings.VNPAY_HASH_SECRET):
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
            finally:
                conn.close()

            # 3. Chuyển hướng người dùng về Frontend kèm thông báo thành công
            return RedirectResponse(url=f"http://localhost:5500/app.html?payment=success&tokens={tokens_to_add}")
        else:
            return RedirectResponse(url=f"http://localhost:5500/app.html?payment=failed")
    else:
        # Sai chữ ký
        return RedirectResponse(url=f"http://localhost:5500/app.html?payment=invalid_signature")