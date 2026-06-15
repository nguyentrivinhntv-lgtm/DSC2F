import os
import smtplib
from email.message import EmailMessage
from app.config import get_settings

def send_otp_email(to_email: str, otp_code: str, purpose: str = 'reset') -> bool:
    """
    Gửi email chứa mã OTP đến người dùng.
    purpose: 'reset' (Quên mật khẩu) hoặc 'register' (Đăng ký tài khoản).
    Yêu cầu thiết lập các biến môi trường:
    - SMTP_SERVER (mặc định: smtp.gmail.com)
    - SMTP_PORT (mặc định: 587)
    - SMTP_USER (email gửi)
    - SMTP_PASS (App Password)
    """
    settings = get_settings()
    smtp_server = settings.SMTP_SERVER
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS

    if not smtp_user or not smtp_pass:
        print(f"[DUMMY EMAIL] Gửi mã OTP {otp_code} tới {to_email} (Chưa cấu hình SMTP)")
        return True

    msg = EmailMessage()
    
    if purpose == 'register':
        msg['Subject'] = 'Mã Xác Thực Đăng Ký Tài Khoản - CNN Detection Hub'
        content = f"""Chào bạn,
        
Bạn đang thực hiện đăng ký tài khoản mới tại CNN Detection Hub.
Dưới đây là mã xác nhận (OTP) của bạn:

{otp_code}

Mã này có hiệu lực trong vòng 5 phút. Vui lòng không chia sẻ mã này cho bất kỳ ai.

Trân trọng,
Đội ngũ CNN Detection Hub"""
    else:
        msg['Subject'] = 'Mã Xác Nhận Đặt Lại Mật Khẩu - CNN Detection Hub'
        content = f"""Chào bạn,
        
Bạn vừa yêu cầu đặt lại mật khẩu tại CNN Detection Hub.
Dưới đây là mã xác nhận (OTP) của bạn:

{otp_code}

Mã này có hiệu lực trong vòng 5 phút. Vui lòng không chia sẻ mã này cho bất kỳ ai.

Trân trọng,
Đội ngũ CNN Detection Hub"""

    msg['From'] = f"CNN Detection Hub <{smtp_user}>"
    msg['To'] = to_email
    msg.set_content(content)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Lỗi gửi email: {e}")
        return False


def send_payment_success_email(to_email: str, username: str, tokens: int, amount: int, order_id: str) -> bool:
    """Gửi email xác nhận thanh toán thành công."""
    settings = get_settings()
    smtp_server = settings.SMTP_SERVER
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS

    if not smtp_user or not smtp_pass:
        print(f"[DUMMY EMAIL] Payment confirmation to {to_email}: +{tokens} tokens, {amount} VND")
        return True

    msg = EmailMessage()
    msg['Subject'] = f'Xác Nhận Nạp Token Thành Công - CNN Detection Hub'
    msg['From'] = f"CNN Detection Hub <{smtp_user}>"
    msg['To'] = to_email

    from datetime import datetime
    now = datetime.now().strftime('%d/%m/%Y %H:%M')

    content = f"""Chào {username},

Giao dịch nạp token của bạn đã thành công!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Chi tiết giao dịch:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Mã đơn hàng : {order_id}
  Số token    : +{tokens} token
  Số tiền     : {amount:,} VND
  Thời gian   : {now}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Token đã được cộng vào tài khoản của bạn và sẵn sàng sử dụng.

Nếu bạn không thực hiện giao dịch này, vui lòng liên hệ với chúng tôi ngay.

Trân trọng,
Đội ngũ CNN Detection Hub"""

    msg.set_content(content)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Lỗi gửi email thanh toán: {e}")
        return False
