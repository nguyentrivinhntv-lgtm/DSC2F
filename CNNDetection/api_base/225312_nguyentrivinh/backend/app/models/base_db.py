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



import sqlite3
import re
import os

USE_SQLITE = False
_SQLITE_INITIALIZED = False

def sqlite_dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def _convert_sql(self, sql):
        sql = sql.replace('%s', '?')
        sql = re.sub(r'\bINT AUTO_INCREMENT PRIMARY KEY\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bINT PRIMARY KEY AUTOINCREMENT\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bINT PRIMARY KEY AUTO_INCREMENT\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bAUTO_INCREMENT\b', 'AUTOINCREMENT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bENGINE=InnoDB\b', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bON UPDATE CURRENT_TIMESTAMP\b', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bINSERT IGNORE INTO\b', 'INSERT OR IGNORE INTO', sql, flags=re.IGNORECASE)
        sql = sql.replace('DATE_ADD(NOW(), INTERVAL 5 MINUTE)', "datetime('now', '+5 minutes')")
        sql = re.sub(r'DATE_SUB\(NOW\(\),\s*INTERVAL\s*\?\s*MINUTE\)', "datetime('now', '-' || ? || ' minutes')", sql, flags=re.IGNORECASE)
        sql = sql.replace('NOW()', "datetime('now')")
        
        if 'email_otps' in sql and 'ON DUPLICATE KEY UPDATE' in sql:
            sql = sql.replace("ON DUPLICATE KEY UPDATE otp_code = VALUES(otp_code), expires_at = datetime('now', '+5 minutes')", 
                              "ON CONFLICT(email) DO UPDATE SET otp_code = excluded.otp_code, expires_at = datetime('now', '+5 minutes')")
        elif 'site_config' in sql and 'ON DUPLICATE KEY UPDATE' in sql:
            sql = sql.replace("ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)", 
                              "ON CONFLICT(config_key) DO UPDATE SET config_value = excluded.config_value")
        return sql

    def execute(self, sql, args=None):
        sql = self._convert_sql(sql)
        try:
            return self.cursor.execute(sql, args or ())
        except Exception:
            raise

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    @property
    def lastrowid(self):
        return self.cursor.lastrowid
    
    @property
    def rowcount(self):
        return self.cursor.rowcount
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()

class SQLiteConnectionWrapper:
    def __init__(self, db_path='database.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite_dict_factory

    def cursor(self):
        return SQLiteCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


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


def _ensure_sqlite_initialized():
    """Khi fallback sang SQLite giữa chừng, tự động tạo tất cả bảng."""
    global _SQLITE_INITIALIZED
    if _SQLITE_INITIALIZED:
        return
    _SQLITE_INITIALIZED = True
    print("Initializing SQLite tables for fallback...")
    try:
        _init_sqlite_tables()
    except Exception as e:
        print(f"SQLite init error: {e}")


def _init_sqlite_tables():
    """Tạo tất cả bảng cần thiết trong SQLite."""
    conn = SQLiteConnectionWrapper()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(100) UNIQUE NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    prediction_tokens INT NOT NULL DEFAULT 5,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS deletion_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    contact_info VARCHAR(150) NOT NULL,
                    reason VARCHAR(255),
                    note TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS prediction_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INT NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    probability DOUBLE NOT NULL,
                    label VARCHAR(10) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS model_config (
                    model_type VARCHAR(50) PRIMARY KEY,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("SELECT COUNT(*) as cnt FROM model_config")
            if cur.fetchone()['cnt'] == 0:
                for m in ["resnet50", "dual_stream_enhanced", "dual_stream_resnet"]:
                    cur.execute("INSERT OR IGNORE INTO model_config (model_type, is_active) VALUES (?, 1)", (m,))

            cur.execute("""
                CREATE TABLE IF NOT EXISTS site_config (
                    config_key VARCHAR(100) PRIMARY KEY,
                    config_value TEXT,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("SELECT COUNT(*) as cnt FROM site_config")
            if cur.fetchone()['cnt'] == 0:
                _insert_default_site_config(cur)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS email_otps (
                    email VARCHAR(100) PRIMARY KEY,
                    otp_code VARCHAR(6) NOT NULL,
                    expires_at DATETIME NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payment_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    title_en VARCHAR(255) NULL,
                    content TEXT,
                    content_en TEXT NULL,
                    is_active TINYINT(1) DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    type VARCHAR(30) DEFAULT 'info',
                    is_read TINYINT(1) DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    type VARCHAR(30) DEFAULT 'info',
                    target VARCHAR(50) DEFAULT 'all',
                    scheduled_at DATETIME NOT NULL,
                    is_sent TINYINT(1) DEFAULT 0,
                    created_by INT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS login_sessions (
                    session_id VARCHAR(100) PRIMARY KEY,
                    token TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tạo tài khoản admin mặc định
            cur.execute("SELECT COUNT(*) as cnt FROM users WHERE username = 'admin'")
            if cur.fetchone()['cnt'] == 0:
                try:
                    from app.security.security import hash_password
                    hashed_pwd = hash_password("admin123")
                    cur.execute(
                        "INSERT INTO users (username, hashed_password, role, prediction_tokens) VALUES (?, ?, ?, ?)",
                        ("admin", hashed_pwd, "admin", 999999)
                    )
                except Exception as e:
                    print(f"Failed to seed admin in SQLite: {e}")

        conn.commit()
        print("SQLite fallback tables initialized successfully!")
    finally:
        conn.close()


def _get_connection(db_path: Optional[str] = None, use_database: bool = True):
    global USE_SQLITE
    database_url = _resolve_database_url(db_path)
    cfg = _parse_mysql_url(database_url)
    
    if USE_SQLITE:
        _ensure_sqlite_initialized()
        return SQLiteConnectionWrapper()

    try:
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"] if use_database else None,
            cursorclass=pymysql.cursors.DictCursor,
            charset="utf8mb4",
            autocommit=False,
            connect_timeout=3
        )
        return conn
    except pymysql.err.OperationalError:
        print("MySQL Connection Failed. Falling back to SQLite...")
        USE_SQLITE = True
        _ensure_sqlite_initialized()
        return SQLiteConnectionWrapper()



def init_db(db_path: Optional[str] = None) -> None:
    """
    Khởi tạo database - tạo các bảng cần thiết nếu chưa tồn tại.

    Args:
        db_path: Giữ tương thích chữ ký cũ; thực chất là database URL.
    """
    database_url = _resolve_database_url(db_path)
    cfg = _parse_mysql_url(database_url)

    global USE_SQLITE
    # Check fallback first by trying to connect
    try:
        server_conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            cursorclass=pymysql.cursors.DictCursor,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=3
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
    except pymysql.err.OperationalError:
        print("MySQL Init Failed. Falling back to SQLite...")
        USE_SQLITE = True

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
            except (MySQLError, sqlite3.OperationalError) as exc:
                if isinstance(exc, sqlite3.OperationalError):
                    pass  # SQLite: duplicate column or can't add UNIQUE
                elif isinstance(exc, MySQLError) and getattr(exc, "args", [None])[0] == 1060:
                    pass
                else:
                    raise

            # Cố gắng thêm cột role nếu table cũ chưa có
            try:
                cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            except (MySQLError, sqlite3.OperationalError) as exc:
                if isinstance(exc, sqlite3.OperationalError):
                    pass
                elif isinstance(exc, MySQLError) and getattr(exc, "args", [None])[0] == 1060:
                    pass
                else:
                    raise

            # Cố gắng thêm cột prediction_tokens nếu table cũ chưa có
            try:
                cur.execute("ALTER TABLE users ADD COLUMN prediction_tokens INT NOT NULL DEFAULT 5")
            except (MySQLError, sqlite3.OperationalError) as exc:
                if isinstance(exc, sqlite3.OperationalError):
                    pass
                elif isinstance(exc, MySQLError) and getattr(exc, "args", [None])[0] == 1060:
                    pass
                else:
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

            # Bảng pages dùng cho CMS
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    title_en VARCHAR(255) NULL,
                    content LONGTEXT,
                    content_en LONGTEXT NULL,
                    is_active TINYINT(1) DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """
            )

            # Cố gắng thêm cột title_en và content_en nếu table cũ chưa có
            try:
                cur.execute("ALTER TABLE pages ADD COLUMN title_en VARCHAR(255) NULL")
            except (MySQLError, sqlite3.OperationalError) as exc:
                if isinstance(exc, sqlite3.OperationalError):
                    pass
                elif isinstance(exc, MySQLError) and getattr(exc, "args", [None])[0] == 1060:
                    pass
                else:
                    raise
            try:
                cur.execute("ALTER TABLE pages ADD COLUMN content_en LONGTEXT NULL")
            except (MySQLError, sqlite3.OperationalError) as exc:
                if isinstance(exc, sqlite3.OperationalError):
                    pass
                elif isinstance(exc, MySQLError) and getattr(exc, "args", [None])[0] == 1060:
                    pass
                else:
                    raise

            
            # Khởi tạo 5 trang mặc định nếu chưa có
            cur.execute("SELECT COUNT(*) as cnt FROM pages")
            if cur.fetchone()['cnt'] == 0:
                default_pages = [
                    ("chinh-sach-quyen-rieng-tu", "Chính sách Quyền riêng tư", "<h2>1. Thu thập thông tin</h2><p>Hệ thống thu thập các thông tin cơ bản bao gồm email, tên đăng nhập, và hình ảnh bạn tải lên để phân tích. Chúng tôi cam kết không chia sẻ dữ liệu nhận diện cá nhân của bạn cho bất kỳ bên thứ ba nào.</p><h2>2. Sử dụng thông tin</h2><p>Hình ảnh được tải lên chỉ được sử dụng cho mục đích phân tích Deepfake/AI. Chúng tôi không lưu trữ hình ảnh của bạn sau khi quá trình phân tích hoàn tất nhằm đảm bảo quyền riêng tư tối đa.</p><h2>3. Bảo mật dữ liệu</h2><p>Dữ liệu truyền tải giữa thiết bị của bạn và máy chủ được mã hóa bằng giao thức SSL/TLS. Mật khẩu của bạn được mã hóa an toàn (hashed) trước khi lưu vào cơ sở dữ liệu.</p>"),
                    ("dieu-khoan-su-dung", "Điều khoản Sử dụng", "<h2>1. Chấp nhận điều khoản</h2><p>Bằng việc truy cập và sử dụng dịch vụ nhận diện ảnh giả mạo của chúng tôi, bạn đồng ý tuân thủ các điều khoản sử dụng này.</p><h2>2. Trách nhiệm người dùng</h2><p>Bạn không được sử dụng hệ thống để phân tích các hình ảnh vi phạm pháp luật, đồi trụy hoặc xâm phạm quyền riêng tư của người khác. Bạn chịu hoàn toàn trách nhiệm về nguồn gốc của hình ảnh tải lên.</p><h2>3. Từ chối bảo đảm</h2><p>Hệ thống AI của chúng tôi cung cấp kết quả mang tính chất tham khảo. Mặc dù độ chính xác cao (>99%), chúng tôi không chịu trách nhiệm pháp lý cho bất kỳ quyết định nào của bạn dựa trên kết quả phân tích này.</p>"),
                    ("xoa-du-lieu", "Xóa Dữ liệu", "<h2>1. Quyền xóa tài khoản và dữ liệu</h2><p>Bạn có toàn quyền yêu cầu xóa tài khoản và tất cả dữ liệu liên quan khỏi hệ thống của chúng tôi bất kỳ lúc nào.</p><h2>2. Cách thức yêu cầu</h2><p>Để xóa dữ liệu, bạn có thể gửi yêu cầu trực tiếp đến bộ phận hỗ trợ của chúng tôi hoặc sử dụng chức năng tự động trong Cài đặt nếu có.</p><h2>3. Thời gian xử lý</h2><p>Sau khi xác nhận yêu cầu, toàn bộ thông tin cá nhân, lịch sử phân tích và tài khoản của bạn sẽ được xóa vĩnh viễn khỏi máy chủ trong vòng 7 ngày làm việc.</p>"),
                    ("chinh-sach-ai", "Chính sách AI", "<h2>1. Tính minh bạch của AI</h2><p>Hệ thống của chúng tôi sử dụng Mạng nơ-ron tích chập (CNN) và kiến trúc Dual-Stream để phát hiện ảnh giả mạo. Chúng tôi cam kết minh bạch về phương pháp tiếp cận và không sử dụng AI cho các mục đích theo dõi hoặc giám sát người dùng.</p><h2>2. Giới hạn của mô hình</h2><p>AI được huấn luyện trên các tập dữ liệu giả mạo phổ biến nhưng không thể phát hiện 100% tất cả các loại deepfake mới nhất. Kết quả trả về là xác suất (probability) và nên được kết hợp với đánh giá của con người.</p><h2>3. Cải thiện mô hình</h2><p>Chúng tôi liên tục cập nhật và huấn luyện lại AI để chống lại các kỹ thuật giả mạo mới. Quá trình huấn luyện không sử dụng hình ảnh thực tế mà người dùng tải lên trừ khi có sự cho phép rõ ràng.</p>"),
                    ("ho-tro-lien-he", "Hỗ trợ & Liên hệ", "<h2>1. Kênh hỗ trợ</h2><p>Nếu bạn gặp sự cố kỹ thuật, nạp token không thành công, hoặc có thắc mắc về kết quả phân tích, vui lòng liên hệ với chúng tôi qua các kênh sau:</p><ul><li><strong>Email:</strong> support@cnndetection.com</li><li><strong>Hotline:</strong> 1900 xxxx (Hoạt động 24/7)</li></ul><h2>2. Thời gian phản hồi</h2><p>Đội ngũ kỹ thuật của chúng tôi sẽ cố gắng phản hồi các yêu cầu hỗ trợ qua email trong vòng 24 giờ làm việc.</p><h2>3. Hợp tác & Doanh nghiệp</h2><p>Đối với các yêu cầu tích hợp API cho doanh nghiệp, vui lòng gửi email kèm tiêu đề [BUSINESS] để được ưu tiên tư vấn giải pháp.</p>"),
                ]
                for p in default_pages:
                    cur.execute("INSERT IGNORE INTO pages (slug, title, content, is_active) VALUES (%s, %s, %s, 1)", p)

            # --- Hệ thống thông báo ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    type VARCHAR(30) DEFAULT 'info',
                    is_read TINYINT(1) DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    type VARCHAR(30) DEFAULT 'info',
                    target VARCHAR(50) DEFAULT 'all',
                    scheduled_at DATETIME NOT NULL,
                    is_sent TINYINT(1) DEFAULT 0,
                    created_by INT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                ) ENGINE=InnoDB
                """
            )

            # --- Hệ thống đăng nhập phiên Hybrid ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS login_sessions (
                    session_id VARCHAR(100) PRIMARY KEY,
                    token TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """
            )

            # Cố gắng thêm các cột VNPay nếu bảng payment_logs cũ chưa có
            try:
                cur.execute("ALTER TABLE payment_logs ADD COLUMN bank_code VARCHAR(50)")
                cur.execute("ALTER TABLE payment_logs ADD COLUMN card_type VARCHAR(50)")
                cur.execute("ALTER TABLE payment_logs ADD COLUMN vnp_transaction_no VARCHAR(100)")
            except (MySQLError, sqlite3.OperationalError) as exc:
                if isinstance(exc, sqlite3.OperationalError):
                    pass
                elif isinstance(exc, MySQLError) and getattr(exc, "args", [None])[0] == 1060:
                    pass
                else:
                    raise

            # Tạo tài khoản admin mặc định nếu chưa có
            cur.execute("SELECT COUNT(*) as cnt FROM users WHERE username = 'admin'")
            row = cur.fetchone()
            if row and row['cnt'] == 0:
                try:
                    from app.security.security import hash_password
                    hashed_pwd = hash_password("admin123")
                    cur.execute(
                        "INSERT INTO users (username, hashed_password, role, prediction_tokens) VALUES (%s, %s, %s, %s)",
                        ("admin", hashed_pwd, "admin", 999999)
                    )
                except Exception as e:
                    print(f"Failed to seed admin: {e}")

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
    # --- API (Google / SMTP / VNPay) ---
    "google_client_id": "",
    "google_client_secret": "",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_pass": "",
    "vnpay_tmn_code": "",
    "vnpay_hash_secret": "",
    "vnpay_payment_url": "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html",
    "vnpay_return_url": "http://localhost:8000/payment/vnpay_return",
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
    "contact_email": "support@cnndetection.com",
    "contact_phone": "+1 800 123 4567",
    "footer_desc": "Ứng dụng nhận diện ảnh AI tiên tiến, sử dụng Deep Learning để phát hiện Deepfake. Hỗ trợ đa nền tảng Web, Android & iOS.",
    "footer_desc_en": "Advanced AI image recognition application, using Deep Learning to detect Deepfakes. Supports cross-platform Web, Android & iOS.",
    "footer_text": "© 2026 CNN Detection Hub — AI Deepfake Detection Platform",
    "footer_text_en": "© 2026 CNN Detection Hub — AI Deepfake Detection Platform",
    # Hero Section
    "hero_title_line1": "Nhận Diện Ảnh Giả Mạo",
    "hero_title_line1_en": "Fake Image Detection",
    "hero_title_line2": "Bằng AI Chuyên Nghiệp",
    "hero_title_line2_en": "With Professional AI",
    "hero_desc": "Bảo vệ bạn khỏi thông tin sai lệch bằng hệ thống phân tích hình ảnh chuyên sâu, sử dụng các mô hình Deep Learning tiên tiến nhất hiện nay.",
    "hero_desc_en": "Protect yourself from misinformation with an in-depth image analysis system, using the most advanced Deep Learning models available today.",
    "hero_cta_text": "Bắt đầu sử dụng miễn phí",
    "hero_cta_text_en": "Start using for free",
    # Features
    "feature1_title": "Dual Stream Enhanced",
    "feature1_title_en": "Dual Stream Enhanced",
    "feature1_desc": "Kiến trúc hai luồng song song trích xuất đặc trưng hình ảnh và nhiễu (noise) để phát hiện dấu vết cắt ghép tinh vi nhất.",
    "feature1_desc_en": "Parallel dual-stream architecture extracts image features and noise to detect the most sophisticated forgery traces.",
    "feature2_title": "Xử Lý Thời Gian Thực",
    "feature2_title_en": "Real-time Processing",
    "feature2_desc": "Tốc độ phân tích cực nhanh, trả về kết quả xác suất thật/giả kèm độ tin cậy chỉ trong vài giây.",
    "feature2_desc_en": "Ultra-fast analysis speed, returning real/fake probability results with confidence score in just a few seconds.",
    "feature3_title": "Batch Scan",
    "feature3_title_en": "Batch Scan",
    "feature3_desc": "Phân tích hàng loạt tối đa 20 ảnh cùng lúc, giúp tiết kiệm thời gian tối đa cho quản trị viên.",
    "feature3_desc_en": "Batch analysis of up to 20 images at once, saving maximum time for administrators.",
    # Steps
    "step1_title": "Tải Ảnh Lên",
    "step1_title_en": "Upload Image",
    "step1_desc": "Kéo thả hoặc chọn bức ảnh bạn nghi ngờ là sản phẩm AI hoặc Deepfake.",
    "step1_desc_en": "Drag and drop or select the image you suspect is an AI product or Deepfake.",
    "step2_title": "AI Phân Tích",
    "step2_title_en": "AI Analysis",
    "step2_desc": "Hệ thống đưa ảnh qua mạng nơ-ron CNN để phân tích ở cấp độ điểm ảnh và tần số.",
    "step2_desc_en": "The system passes the image through CNN neural networks for analysis at pixel and frequency levels.",
    "step3_title": "Nhận Kết Quả",
    "step3_title_en": "Get Results",
    "step3_desc": "Nhận đánh giá FAKE/REAL kèm biểu đồ trực quan (Heatmap, Phổ FFT) giải thích lý do.",
    "step3_desc_en": "Get FAKE/REAL assessment with visual charts (Heatmap, FFT Spectrum) explaining the reason.",
    # Section visibility (1 = hiện, 0 = ẩn)
    "show_stats": "1",
    "show_marquee": "1",
    "show_features": "1",
    "show_howitworks": "1",
    "show_cta": "1",
    "ai_provider": "groq",
    "ai_groq_key": "",
    "ai_gemini_key": "",
    "ai_openai_key": "",
    "ai_system_prompt": "You are a professional translator. Translate the following Vietnamese text or HTML content to English. Preserve all HTML tags, structure, and formatting. Return ONLY the translated English text/HTML, nothing else.",
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
        cur = conn.cursor()
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
                SET hashed_password = %s
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


# ====================== CMS PAGES ======================

def get_all_pages(db_path: Optional[str] = None) -> list:
    """Lấy danh sách tất cả các trang CMS."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, slug, title, title_en, is_active, created_at, updated_at FROM pages ORDER BY created_at DESC")
            rows = cur.fetchall()
            for row in rows:
                if hasattr(row.get("created_at"), "isoformat"):
                    row["created_at"] = row["created_at"].isoformat()
                if hasattr(row.get("updated_at"), "isoformat"):
                    row["updated_at"] = row["updated_at"].isoformat()
            return rows
    finally:
        conn.close()

def get_active_pages(db_path: Optional[str] = None) -> list:
    """Lấy danh sách các trang CMS đang active."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, slug, title, title_en, is_active, created_at, updated_at FROM pages WHERE is_active = 1 ORDER BY created_at DESC")
            rows = cur.fetchall()
            for row in rows:
                if hasattr(row.get("created_at"), "isoformat"):
                    row["created_at"] = row["created_at"].isoformat()
                if hasattr(row.get("updated_at"), "isoformat"):
                    row["updated_at"] = row["updated_at"].isoformat()
            return rows
    finally:
        conn.close()

def get_page_by_slug(slug: str, db_path: Optional[str] = None) -> Optional[dict]:
    """Lấy chi tiết một trang CMS."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pages WHERE slug = %s", (slug,))
            row = cur.fetchone()
            if row:
                if hasattr(row.get("created_at"), "isoformat"):
                    row["created_at"] = row["created_at"].isoformat()
                if hasattr(row.get("updated_at"), "isoformat"):
                    row["updated_at"] = row["updated_at"].isoformat()
            return row
    finally:
        conn.close()

def create_page(slug: str, title: str, content: str, title_en: Optional[str] = None, content_en: Optional[str] = None, is_active: int = 1, db_path: Optional[str] = None) -> bool:
    """Tạo mới một trang CMS."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pages (slug, title, content, title_en, content_en, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                (slug, title, content, title_en, content_en, is_active)
            )
        conn.commit()
        return True
    except MySQLError as exc:
        if getattr(exc, "args", [None])[0] == 1062:
            raise ValueError(f"Slug '{slug}' đã tồn tại.")
        raise
    finally:
        conn.close()

def update_page(slug: str, title: str, content: str, title_en: Optional[str] = None, content_en: Optional[str] = None, is_active: int = 1, db_path: Optional[str] = None) -> bool:
    """Cập nhật một trang CMS."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pages SET title = %s, content = %s, title_en = %s, content_en = %s, is_active = %s WHERE slug = %s",
                (title, content, title_en, content_en, is_active, slug)
            )
            updated = cur.rowcount
        conn.commit()
        return updated > 0
    finally:
        conn.close()

def delete_page(slug: str, db_path: Optional[str] = None) -> bool:
    """Xóa một trang CMS."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pages WHERE slug = %s", (slug,))
            updated = cur.rowcount
        conn.commit()
        return updated > 0
    finally:
        conn.close()


# ====================== NOTIFICATIONS ======================

def create_notification(user_id: int, title: str, message: str, ntype: str = 'info', db_path: Optional[str] = None) -> Optional[int]:
    """Tạo thông báo mới cho 1 user. Trả về id của notification."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, %s)",
                (user_id, title, message, ntype),
            )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def create_notification_broadcast(title: str, message: str, ntype: str = 'info', db_path: Optional[str] = None) -> int:
    """Tạo thông báo cho tất cả users. Trả về số lượng thông báo đã tạo."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE is_active = 1")
            users = cur.fetchall()
            for u in users:
                cur.execute(
                    "INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, %s)",
                    (u['id'], title, message, ntype),
                )
        conn.commit()
        return len(users)
    finally:
        conn.close()


def get_notifications(user_id: int, limit: int = 20, offset: int = 0, db_path: Optional[str] = None) -> list:
    """Lấy danh sách thông báo của user, mới nhất trước."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (user_id, limit, offset),
            )
            rows = cur.fetchall()
            for row in rows:
                if hasattr(row.get('created_at'), 'isoformat'):
                    row['created_at'] = row['created_at'].isoformat()
            return rows
    finally:
        conn.close()


def get_unread_count(user_id: int, db_path: Optional[str] = None) -> int:
    """Đếm số thông báo chưa đọc."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = %s AND is_read = 0",
                (user_id,),
            )
            row = cur.fetchone()
            return row['cnt'] if row else 0
    finally:
        conn.close()


def mark_notification_read(notification_id: int, user_id: int, db_path: Optional[str] = None) -> bool:
    """Đánh dấu 1 thông báo đã đọc."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s",
                (notification_id, user_id),
            )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_all_read(user_id: int, db_path: Optional[str] = None) -> int:
    """Đánh dấu tất cả thông báo đã đọc. Trả về số dòng affected."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
                (user_id,),
            )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_notification(notification_id: int, user_id: int, db_path: Optional[str] = None) -> bool:
    """Xóa 1 thông báo."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM notifications WHERE id = %s AND user_id = %s",
                (notification_id, user_id),
            )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ====================== SCHEDULED NOTIFICATIONS ======================

def create_scheduled_notification(
    title: str, message: str, ntype: str, target: str,
    scheduled_at: str, created_by: int, db_path: Optional[str] = None
) -> Optional[int]:
    """Tạo thông báo hẹn giờ."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO scheduled_notifications
                   (title, message, type, target, scheduled_at, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (title, message, ntype, target, scheduled_at, created_by),
            )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_pending_scheduled(db_path: Optional[str] = None) -> list:
    """Lấy thông báo hẹn giờ đã đến lúc gửi nhưng chưa gửi."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM scheduled_notifications WHERE is_sent = 0 AND scheduled_at <= NOW()"
            )
            return cur.fetchall()
    finally:
        conn.close()


def mark_scheduled_sent(scheduled_id: int, db_path: Optional[str] = None) -> bool:
    """Đánh dấu scheduled notification đã gửi."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE scheduled_notifications SET is_sent = 1 WHERE id = %s",
                (scheduled_id,),
            )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_all_scheduled(db_path: Optional[str] = None) -> list:
    """Lấy tất cả scheduled notifications cho admin xem."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.*, u.username as created_by_username
                   FROM scheduled_notifications s
                   JOIN users u ON s.created_by = u.id
                   ORDER BY s.scheduled_at DESC"""
            )
            rows = cur.fetchall()
            for row in rows:
                for key in ('scheduled_at', 'created_at'):
                    if hasattr(row.get(key), 'isoformat'):
                        row[key] = row[key].isoformat()
            return rows
    finally:
        conn.close()


def delete_scheduled(scheduled_id: int, db_path: Optional[str] = None) -> bool:
    """Xóa scheduled notification."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM scheduled_notifications WHERE id = %s",
                (scheduled_id,),
            )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

# ======================= LOGIN SESSIONS (HYBRID APP) =======================
def create_login_session(session_id: str, db_path: Optional[str] = None) -> bool:
    """Tạo một phiên chờ đăng nhập."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO login_sessions (session_id, status) VALUES (%s, 'pending')",
                (session_id,)
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error create_login_session: {e}")
        return False
    finally:
        conn.close()

def get_login_session(session_id: str, db_path: Optional[str] = None) -> Optional[dict]:
    """Lấy thông tin phiên chờ đăng nhập."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM login_sessions WHERE session_id = %s", (session_id,))
            return cur.fetchone()
    finally:
        conn.close()

def update_login_session(session_id: str, token: str, db_path: Optional[str] = None) -> bool:
    """Cập nhật token khi đăng nhập thành công."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE login_sessions SET token = %s, status = 'completed' WHERE session_id = %s",
                (token, session_id)
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()

def delete_login_session(session_id: str, db_path: Optional[str] = None) -> bool:
    """Xóa phiên sau khi hoàn thành hoặc hủy bỏ."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM login_sessions WHERE session_id = %s", (session_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()

def cleanup_old_login_sessions(minutes: int = 10, db_path: Optional[str] = None):
    """Xóa các phiên chờ cũ hơn `minutes` phút."""
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM login_sessions WHERE created_at < DATE_SUB(NOW(), INTERVAL %s MINUTE)",
                (minutes,)
            )
        conn.commit()
    except Exception as e:
        print(f"Error cleanup_old_login_sessions: {e}")
    finally:
        conn.close()

def create_deletion_request(contact_info: str, reason: str, note: str, db_path: Optional[str] = None):
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO deletion_requests (contact_info, reason, note, status) VALUES (%s, %s, %s, 'pending')",
                (contact_info, reason, note)
            )
        conn.commit()
        return True
    finally:
        conn.close()

def get_all_deletion_requests(db_path: Optional[str] = None):
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM deletion_requests ORDER BY id DESC")
            rows = cur.fetchall()
            for row in rows:
                if row.get("created_at") and hasattr(row["created_at"], "isoformat"):
                    row["created_at"] = row["created_at"].isoformat()
            return rows
    finally:
        conn.close()

def update_deletion_request_status(req_id: int, status: str, db_path: Optional[str] = None):
    conn = _get_connection(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE deletion_requests SET status = %s WHERE id = %s", (status, req_id))
        conn.commit()
        return True
    finally:
        conn.close()
