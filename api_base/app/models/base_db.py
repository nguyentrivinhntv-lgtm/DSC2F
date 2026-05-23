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
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    prediction_tokens INT NOT NULL DEFAULT 5,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """
            )

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
        conn.commit()
    finally:
        conn.close()


def get_user_by_username(username: str, db_path: Optional[str] = None) -> Optional[dict]:
    """
    Tìm user theo username.

    Args:
        username: Tên đăng nhập.
        db_path: Đường dẫn database.

    Returns:
        dict hoặc None: Thông tin user nếu tìm thấy.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
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


def create_user(
    username: str,
    hashed_password: str,
    role: str = 'user',
    prediction_tokens: int = 5,
    db_path: Optional[str] = None,
) -> dict:
    """
    Tạo user mới.

    Args:
        username: Tên đăng nhập.
        hashed_password: Password đã hash.
        role: Vai trò người dùng ('user' hoặc 'admin').
        db_path: Đường dẫn database.

    Returns:
        dict: Thông tin user vừa tạo.

    Raises:
        ValueError: Nếu username đã tồn tại.
    """
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, hashed_password, role, prediction_tokens) VALUES (%s, %s, %s, %s)",
                (username, hashed_password, role, prediction_tokens),
            )
        conn.commit()
        return get_user_by_username(username, db_path)
    except MySQLError as exc:
        # 1062: Duplicate entry
        if getattr(exc, "args", [None])[0] == 1062:
            raise ValueError(f"Username '{username}' đã tồn tại.")
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
