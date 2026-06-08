"""
=============================================================================
Database Module - CNN Detection API
=============================================================================
Kết nối và thao tác với MySQL database.
Quản lý bảng users cho authentication.

Sử dụng PyMySQL thuần (không ORM) để giữ đơn giản.
"""

from urllib.parse import unquote, urlparse
from typing import Optional

import pymysql
from pymysql.err import MySQLError

from app.config import get_settings


def _resolve_database_url(db_path: Optional[str] = None) -> str:
    """
    Lấy database URL ưu tiên từ tham số, sau đó từ settings.

    Args:
        db_path: Giữ tương thích chữ ký cũ; thực chất là database URL.

    Returns:
        str: Database URL.
    """
    if db_path:
        return db_path
    return get_settings().DATABASE_URL


def _parse_mysql_url(database_url: str) -> dict:
    """
    Parse DATABASE_URL dạng mysql://user:pass@host:port/dbname.

    Args:
        database_url: Chuỗi DATABASE_URL.

    Returns:
        dict: Cấu hình kết nối MySQL.
    """
    parsed = urlparse(database_url)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise ValueError(
            "DATABASE_URL phải có schema mysql:// hoặc mysql+pymysql://"
        )

    database = parsed.path.lstrip("/")
    if not database:
        raise ValueError("DATABASE_URL phải chứa tên database ở phần path.")

    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or "root"),
        "password": unquote(parsed.password or ""),
        "database": database,
    }


def _get_connection(db_path: Optional[str] = None, use_database: bool = True):
    """
    Tạo kết nối tới MySQL database.

    Args:
        db_path: Giữ tương thích chữ ký cũ; thực chất là database URL.
        use_database: Nếu False chỉ kết nối server MySQL, không chọn DB.

    Returns:
        Connection: Kết nối database.
    """
    database_url = _resolve_database_url(db_path)
    cfg = _parse_mysql_url(database_url)
    return pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"] if use_database else None,
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
        autocommit=False,
    )


def init_db(db_path: Optional[str] = None) -> None:
    """
    Khởi tạo database - tạo các bảng cần thiết nếu chưa tồn tại.

    Args:
        db_path: Giữ tương thích chữ ký cũ; thực chất là database URL.
    """
    database_url = _resolve_database_url(db_path)
    cfg = _parse_mysql_url(database_url)

    # Tạo database nếu chưa tồn tại
    server_conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with server_conn.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS `{}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(
                    cfg["database"]
                )
            )
    finally:
        server_conn.close()

    conn = _get_connection(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(100) UNIQUE NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    prediction_tokens INT NOT NULL DEFAULT 5,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """
            )

            # Cố gắng thêm cột email nếu table cũ chưa có
            try:
                cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(100) UNIQUE NULL")
            except MySQLError as exc:
                if getattr(exc, "args", [None])[0] != 1060:
                    raise

            # Cố gắng thêm cột role nếu table cũ chưa có
            try:
                cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            except MySQLError as exc:
                # 1060: Duplicate column name
                if getattr(exc, "args", [None])[0] != 1060:
                    raise

            # Cố gắng thêm cột prediction_tokens nếu table cũ chưa có
            try:
                cur.execute("ALTER TABLE users ADD COLUMN prediction_tokens INT NOT NULL DEFAULT 5")
            except MySQLError as exc:
                # 1060: Duplicate column name
                if getattr(exc, "args", [None])[0] != 1060:
                    raise

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS prediction_logs (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    probability DOUBLE NOT NULL,
                    label VARCHAR(10) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_prediction_user
                        FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB
                """
            )
            
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS model_config (
                    model_type VARCHAR(50) PRIMARY KEY,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """
            )
            
            # Khởi tạo mặc định nếu bảng trống
            cur.execute("SELECT COUNT(*) as cnt FROM model_config")
            row = cur.fetchone()
            if row and row['cnt'] == 0:
                default_models = ["resnet50", "dual_stream_enhanced", "dual_stream_resnet"]
                for m in default_models:
                    cur.execute("INSERT INTO model_config (model_type, is_active) VALUES (%s, 1)", (m,))

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS site_config (
                    config_key VARCHAR(100) PRIMARY KEY,
                    config_value TEXT,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """
            )

            # Xóa các biến pkg cũ do đã chuyển sang token_packages (Migration)
            cur.execute("DELETE FROM site_config WHERE config_key LIKE 'pkg_%'")

            # Khởi tạo config mặc định nếu bảng trống
            cur.execute("SELECT COUNT(*) as cnt FROM site_config")
            row = cur.fetchone()
            if row and row['cnt'] == 0:
                _insert_default_site_config(cur)

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS email_otps (
                    email VARCHAR(100) PRIMARY KEY,
                    otp_code VARCHAR(6) NOT NULL,
                    expires_at DATETIME NOT NULL
                ) ENGINE=InnoDB
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    order_id VARCHAR(100) NOT NULL,
                    amount INT NOT NULL,
                    tokens INT NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'success',
                    bank_code VARCHAR(50),
                    card_type VARCHAR(50),
                    vnp_transaction_no VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB
                """
            )

            # Cố gắng thêm các cột VNPay nếu bảng payment_logs cũ chưa có
            try:
                cur.execute("ALTER TABLE payment_logs ADD COLUMN bank_code VARCHAR(50)")
                cur.execute("ALTER TABLE payment_logs ADD COLUMN card_type VARCHAR(50)")
                cur.execute("ALTER TABLE payment_logs ADD COLUMN vnp_transaction_no VARCHAR(100)")
            except MySQLError as exc:
                if getattr(exc, "args", [None])[0] != 1060:
                    raise

        conn.commit()
    finally:
        conn.close()


def get_user_by_username(username: str, db_path: Optional[str] = None) -> Optional[dict]:
    """Tìm user theo username."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            return row if row else None
    finally:
        conn.close()


def get_user_by_email(email: str, db_path: Optional[str] = None) -> Optional[dict]:
    """Tìm user theo email."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            return row if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    """
    Tìm user theo ID.

    Args:
        user_id: ID của user.
        db_path: Đường dẫn database.

    Returns:
        dict hoặc None: Thông tin user nếu tìm thấy.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return row if row else None
    finally:
        conn.close()


def get_all_users(db_path: Optional[str] = None) -> list:
    """Lấy danh sách tất cả user (trừ mật khẩu)."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, email, role, prediction_tokens, created_at, is_active FROM users ORDER BY id DESC")
            rows = cur.fetchall()
            
            # Format datetime to string if needed
            for row in rows:
                created_at = row.get("created_at")
                if hasattr(created_at, "isoformat"):
                    row["created_at"] = created_at.isoformat()
                    
            return rows
    finally:
        conn.close()


def update_user_role(username: str, new_role: str, db_path: Optional[str] = None) -> bool:
    """Cập nhật quyền của user."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET role = %s WHERE username = %s",
                (new_role, username)
            )
        conn.commit()
        return True
    finally:
        conn.close()



def create_user(
    username: str,
    hashed_password: str,
    email: Optional[str] = None,
    role: str = 'user',
    prediction_tokens: int = 5,
    db_path: Optional[str] = None,
) -> dict:
    """Tạo user mới."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email, hashed_password, role, prediction_tokens) VALUES (%s, %s, %s, %s, %s)",
                (username, email, hashed_password, role, prediction_tokens),
            )
        conn.commit()
        return get_user_by_username(username, db_path)
    except MySQLError as exc:
        if getattr(exc, "args", [None])[0] == 1062:
            raise ValueError(f"Username hoặc Email đã tồn tại.")
        raise
    finally:
        conn.close()


def log_prediction(
    user_id: int,
    filename: str,
    model_type: str,
    probability: float,
    label: str,
    db_path: Optional[str] = None
) -> None:
    """
    Lưu log kết quả prediction.

    Args:
        user_id: ID user thực hiện prediction.
        filename: Tên file ảnh.
        model_type: Loại model sử dụng.
        probability: Xác suất fake.
        label: Nhãn kết quả (real/fake).
        db_path: Đường dẫn database.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO prediction_logs
                   (user_id, filename, model_type, probability, label)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, filename, model_type, probability, label),
            )
        conn.commit()
    finally:
        conn.close()


def decrement_prediction_tokens(
    user_id: int,
    amount: int = 1,
    db_path: Optional[str] = None,
) -> bool:
    """
    Trừ prediction tokens của user theo kiểu atomic.

    Args:
        user_id: ID user.
        amount: Số token cần trừ.
        db_path: Đường dẫn database.

    Returns:
        bool: True nếu trừ thành công, False nếu không đủ token.
    """
    if amount <= 0:
        return True

    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET prediction_tokens = prediction_tokens - %s
                WHERE id = %s AND prediction_tokens >= %s
                """,
                (amount, user_id, amount),
            )
            updated = cur.rowcount
        conn.commit()
        return updated == 1
    finally:
        conn.close()


def add_prediction_tokens(
    username: str,
    amount: int,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """
    Cộng thêm prediction tokens cho user và trả thông tin user mới nhất.

    Args:
        username: Username cần nạp token.
        amount: Số token cộng thêm (>0).
        db_path: Đường dẫn database.

    Returns:
        dict hoặc None: User sau khi cập nhật, hoặc None nếu user không tồn tại.
    """
    if amount <= 0:
        raise ValueError("Số token nạp phải lớn hơn 0.")

    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET prediction_tokens = prediction_tokens + %s
                WHERE username = %s
                """,
                (amount, username),
            )
            updated = cur.rowcount
        conn.commit()
        if updated != 1:
            return None
        return get_user_by_username(username, db_path)
    finally:
        conn.close()


def get_prediction_history(user_id: int, is_admin: bool = False, db_path: Optional[str] = None) -> list:
    """
    Lấy lịch sử nhận diện.

    Args:
        user_id: ID của user đang yêu cầu.
        is_admin: Nếu là admin, trả về toàn bộ.
        db_path: Đường dẫn database.
        
    Returns:
        list: Danh sách lịch sử.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            if is_admin:
                cur.execute(
                    """SELECT p.*, u.username
                       FROM prediction_logs p
                       JOIN users u ON p.user_id = u.id
                       ORDER BY p.created_at DESC"""
                )
            else:
                cur.execute(
                    """SELECT p.*, u.username
                       FROM prediction_logs p
                       JOIN users u ON p.user_id = u.id
                       WHERE p.user_id = %s
                       ORDER BY p.created_at DESC""",
                    (user_id,),
                )
            rows = cur.fetchall()

        # Đảm bảo created_at là string để tương thích schema response hiện tại.
        for row in rows:
            created_at = row.get("created_at")
            if hasattr(created_at, "isoformat"):
                row["created_at"] = created_at.isoformat()
        return rows
    finally:
        conn.close()


def get_all_models_config(db_path: Optional[str] = None) -> list:
    """
    Lấy trạng thái cấu hình của tất cả các model.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT model_type, is_active FROM model_config")
            return cur.fetchall()
    finally:
        conn.close()


def update_model_status(model_type: str, is_active: bool, db_path: Optional[str] = None) -> bool:
    """
    Cập nhật trạng thái bật/tắt của một model.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE model_config 
                SET is_active = %s 
                WHERE model_type = %s
                """,
                (1 if is_active else 0, model_type)
            )
            if cur.rowcount == 0:
                # Nếu chưa có thì insert
                cur.execute(
                    "INSERT INTO model_config (model_type, is_active) VALUES (%s, %s)",
                    (model_type, 1 if is_active else 0)
                )
        conn.commit()
        return True
    finally:
        conn.close()

def is_model_active(model_type: str, db_path: Optional[str] = None) -> bool:
    """
    Kiểm tra xem model có đang được bật không.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_active FROM model_config WHERE model_type = %s", (model_type,))
            row = cur.fetchone()
            if row:
                return bool(row['is_active'])
            return True # Mặc định bật nếu chưa có config
    finally:
        conn.close()


# ====================== SITE CONFIG ======================

DEFAULT_SITE_CONFIG = {
    # Màu sắc
    "color_primary": "#0ea5a4",
    "color_accent": "#f59e0b",
    "color_bg": "#f7f9fc",
    "color_bg2": "#eff3f9",
    "color_bg3": "#e2e8f0",
    "color_text": "#162437",
    # Thông tin chung
    "site_name": "CNN Detection Hub",
    "site_slogan": "AI Forensics Platform",
    "footer_text": "© 2026 CNN Detection Hub — AI Deepfake Detection Platform",
    # Hero Section
    "hero_title_line1": "Nhận Diện Ảnh Giả Mạo",
    "hero_title_line2": "Bằng AI Chuyên Nghiệp",
    "hero_desc": "Bảo vệ bạn khỏi thông tin sai lệch bằng hệ thống phân tích hình ảnh chuyên sâu, sử dụng các mô hình Deep Learning tiên tiến nhất hiện nay.",
    "hero_cta_text": "Bắt đầu sử dụng miễn phí",
    # Features
    "feature1_title": "Dual Stream Enhanced",
    "feature1_desc": "Kiến trúc hai luồng song song trích xuất đặc trưng hình ảnh và nhiễu (noise) để phát hiện dấu vết cắt ghép tinh vi nhất.",
    "feature2_title": "Xử Lý Thời Gian Thực",
    "feature2_desc": "Tốc độ phân tích cực nhanh, trả về kết quả xác suất thật/giả kèm độ tin cậy chỉ trong vài giây.",
    "feature3_title": "Batch Scan",
    "feature3_desc": "Phân tích hàng loạt tối đa 20 ảnh cùng lúc, giúp tiết kiệm thời gian tối đa cho quản trị viên.",
    # Steps
    "step1_title": "Tải Ảnh Lên",
    "step1_desc": "Kéo thả hoặc chọn bức ảnh bạn nghi ngờ là sản phẩm AI hoặc Deepfake.",
    "step2_title": "AI Phân Tích",
    "step2_desc": "Hệ thống đưa ảnh qua mạng nơ-ron CNN để phân tích ở cấp độ điểm ảnh và tần số.",
    "step3_title": "Nhận Kết Quả",
    "step3_desc": "Nhận đánh giá FAKE/REAL kèm biểu đồ trực quan (Heatmap, Phổ FFT) giải thích lý do.",
    # Section visibility (1 = hiện, 0 = ẩn)
    "show_stats": "1",
    "show_marquee": "1",
    "show_features": "1",
    "show_howitworks": "1",
    "show_cta": "1",
    # Logo URL (empty = default icon)
    "logo_url": "",
    # Pricing Packages (JSON array)
    "token_packages": '[{"id":"pkg_1","name":"Gói Cơ Bản","price":10000,"tokens":10,"popular":false,"features":["Phân tích ảnh cơ bản","Hỗ trợ lưu lịch sử"]},{"id":"pkg_2","name":"Gói Nâng Cao","price":45000,"tokens":50,"popular":true,"features":["Phân tích ảnh nâng cao","Hỗ trợ Batch Scan","Tiết kiệm 10%"]},{"id":"pkg_3","name":"Gói Chuyên Gia","price":100000,"tokens":120,"popular":false,"features":["Mọi tính năng cao cấp","Ưu tiên phân tích (Fast)","Tiết kiệm 20%"]}]'
}


def _insert_default_site_config(cursor) -> None:
    """Insert các giá trị mặc định vào bảng site_config."""
    for key, value in DEFAULT_SITE_CONFIG.items():
        cursor.execute(
            "INSERT IGNORE INTO site_config (config_key, config_value) VALUES (%s, %s)",
            (key, value),
        )


def get_site_config(db_path: Optional[str] = None) -> dict:
    """
    Lấy toàn bộ site config dưới dạng dict.
    Nếu key chưa có trong DB, trả về giá trị mặc định.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT config_key, config_value FROM site_config")
            rows = cur.fetchall()
        result = {**DEFAULT_SITE_CONFIG}
        for row in rows:
            result[row["config_key"]] = row["config_value"]
        return result
    finally:
        conn.close()


def update_site_config(data: dict, db_path: Optional[str] = None) -> None:
    """
    Cập nhật nhiều key-value config cùng lúc.
    Chỉ cập nhật các key hợp lệ (có trong DEFAULT_SITE_CONFIG).
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            for key, value in data.items():
                if key in DEFAULT_SITE_CONFIG:
                    cur.execute(
                        """
                        INSERT INTO site_config (config_key, config_value)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
                        """,
                        (key, str(value)),
                    )
        conn.commit()
    finally:
        conn.close()


def reset_site_config(db_path: Optional[str] = None) -> dict:
    """
    Khôi phục toàn bộ config về giá trị mặc định.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM site_config")
            _insert_default_site_config(cur)
        conn.commit()
        return {**DEFAULT_SITE_CONFIG}
    finally:
        conn.close()


def save_email_otp(email: str, otp_code: str, db_path: Optional[str] = None) -> None:
    """Lưu mã OTP cho email với hạn dùng 5 phút."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            # Expires in 5 minutes
            cur.execute(
                """
                INSERT INTO email_otps (email, otp_code, expires_at) 
                VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 5 MINUTE))
                ON DUPLICATE KEY UPDATE otp_code = VALUES(otp_code), expires_at = DATE_ADD(NOW(), INTERVAL 5 MINUTE)
                """,
                (email, otp_code)
            )
        conn.commit()
    finally:
        conn.close()


def verify_email_otp(email: str, otp_code: str, db_path: Optional[str] = None) -> bool:
    """Kiểm tra mã OTP có hợp lệ và chưa hết hạn hay không. Nếu đúng, xóa OTP."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM email_otps WHERE email = %s AND otp_code = %s AND expires_at > NOW()",
                (email, otp_code)
            )
            row = cur.fetchone()
            if row:
                cur.execute("DELETE FROM email_otps WHERE email = %s", (email,))
                conn.commit()
                return True
            return False
    finally:
        conn.close()


def update_user_password(email: str, hashed_password: str, db_path: Optional[str] = None) -> bool:
    """Cập nhật mật khẩu mới cho user dựa vào email."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET hashed_password = %s WHERE email = %s",
                (hashed_password, email)
            )
        conn.commit()
        return True
    finally:
        conn.close()
def update_user_password_by_username(username: str, hashed_password: str, db_path: Optional[str] = None) -> bool:
    """Cập nhật mật khẩu mới cho user dựa vào username."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users 
                SET hashed_password = %s, updated_at = CURRENT_TIMESTAMP
                WHERE username = %s
                """,
                (hashed_password, username),
            )
            updated = cur.rowcount
        conn.commit()
        return updated == 1
    finally:
        conn.close()


def save_payment_log(
    user_id: int, 
    order_id: str, 
    amount: int, 
    tokens: int, 
    bank_code: Optional[str] = None,
    card_type: Optional[str] = None,
    vnp_transaction_no: Optional[str] = None,
    db_path: Optional[str] = None
):
    """Lưu lịch sử thanh toán vào bảng payment_logs."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payment_logs (user_id, order_id, amount, tokens, status, bank_code, card_type, vnp_transaction_no)
                VALUES (%s, %s, %s, %s, 'success', %s, %s, %s)
                """,
                (user_id, order_id, amount, tokens, bank_code, card_type, vnp_transaction_no),
            )
        conn.commit()
    finally:
        conn.close()


def get_payment_history(user_id: int, is_admin: bool = False, db_path: Optional[str] = None) -> list:
    """Lấy lịch sử thanh toán. Admin lấy tất cả, user chỉ lấy của mình."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            if is_admin:
                cur.execute(
                    """SELECT p.*, u.username
                       FROM payment_logs p
                       JOIN users u ON p.user_id = u.id
                       ORDER BY p.created_at DESC"""
                )
            else:
                cur.execute(
                    """SELECT p.*, u.username
                       FROM payment_logs p
                       JOIN users u ON p.user_id = u.id
                       WHERE p.user_id = %s
                       ORDER BY p.created_at DESC""",
                    (user_id,),
                )
            return cur.fetchall() or []
    finally:
        conn.close()
