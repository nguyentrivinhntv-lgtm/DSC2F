import sys
import os

# Thêm đường dẫn hiện tại vào path để import được thư mục app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.base_db import _get_connection

def make_admin(username):
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role = 'admin' WHERE username = %s", (username,))
            if cur.rowcount > 0:
                print(f"✅ Đã cấp quyền ADMIN thành công cho tài khoản: {username}")
                print("Hãy F5 lại trang web và kiểm tra, bạn sẽ thấy Admin Dashboard hiện lên.")
            else:
                print(f"❌ Không tìm thấy tài khoản '{username}' trong database.")
                print("Bạn cần phải đăng ký/đăng nhập tài khoản này trên website một lần trước đã.")
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("==============================")
        print("CÁCH SỬ DỤNG:")
        print("  python set_admin.py <tên_đăng_nhập_của_bạn>")
        print("Ví dụ:")
        print("  python set_admin.py admin_vinh")
        print("==============================")
    else:
        make_admin(sys.argv[1])
