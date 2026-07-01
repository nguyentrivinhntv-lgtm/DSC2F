"""
=============================================================================
Helpers - Các hàm tiện ích dùng chung
=============================================================================
Cung cấp các utility function cho xử lý file, validation, v.v.
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from app.config import VALID_IMAGE_EXTENSIONS, UPLOAD_TEMP_DIR


def validate_image_file(filename: str) -> bool:
    """
    Kiểm tra file có phải ảnh hợp lệ không.

    Args:
        filename: Tên file cần kiểm tra.

    Returns:
        bool: True nếu extension hợp lệ.
    """
    if not filename:
        return False
    ext = os.path.splitext(filename.lower())[1]
    return ext in VALID_IMAGE_EXTENSIONS


def generate_unique_filename(original_filename: str) -> str:
    """
    Tạo tên file unique để tránh trùng lặp khi upload.

    Kết hợp UUID + timestamp + extension gốc.

    Args:
        original_filename: Tên file gốc.

    Returns:
        str: Tên file unique.

    Example:
        >>> generate_unique_filename("photo.jpg")
        '20260415_130500_a1b2c3d4.jpg'
    """
    ext = os.path.splitext(original_filename)[1].lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique_id}{ext}"


def ensure_directory(dir_path: str) -> str:
    """
    Đảm bảo thư mục tồn tại, tạo nếu chưa có.

    Args:
        dir_path: Đường dẫn thư mục.

    Returns:
        str: Đường dẫn thư mục (để chain).
    """
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def save_upload_file(file_content: bytes, filename: str, upload_dir: Optional[str] = None) -> str:
    """
    Lưu file upload tạm thời.

    Args:
        file_content: Nội dung file dạng bytes.
        filename: Tên file unique.
        upload_dir: Thư mục lưu. Mặc định UPLOAD_TEMP_DIR.

    Returns:
        str: Đường dẫn đầy đủ tới file đã lưu.
    """
    target_dir = upload_dir or UPLOAD_TEMP_DIR
    ensure_directory(target_dir)
    file_path = os.path.join(target_dir, filename)
    with open(file_path, "wb") as f:
        f.write(file_content)
    return file_path


def cleanup_temp_file(file_path: str) -> None:
    """
    Xóa file tạm sau khi xử lý xong.

    Args:
        file_path: Đường dẫn file cần xóa.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass  # Bỏ qua lỗi xóa file


def format_probability(probability: float) -> dict:
    """
    Format kết quả probability thành response dict.

    Args:
        probability: Xác suất fake (0.0 - 1.0).

    Returns:
        dict: Kết quả format {"probability", "percentage", "label", "confidence"}.
    """
    label = "fake" if probability >= 0.5 else "real"
    confidence = probability if probability >= 0.5 else (1.0 - probability)

    return {
        "probability": round(probability, 6),
        "percentage": f"{probability * 100:.2f}%",
        "label": label,
        "confidence": f"{confidence * 100:.2f}%",
    }
