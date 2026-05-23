"""
=============================================================================
Cấu hình ứng dụng - CNN Detection API
=============================================================================
Quản lý toàn bộ cấu hình dự án. Đọc từ file .env và cung cấp
giá trị mặc định cho các thiết lập.

Sử dụng pydantic-settings để validate và type-check config.
"""

import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


ENV_FILE_PATH = str(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseSettings):
    """
    Cấu hình chính của ứng dụng.

    Tất cả giá trị được đọc từ file .env hoặc biến môi trường hệ thống.
    Ưu tiên: biến môi trường > .env > giá trị mặc định.
    """

    # --- Security ---
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 giờ
    GOOGLE_CLIENT_ID: str = "467356155966-9tv52397cuqllc6pe02c9fc32j1nfb8j.apps.googleusercontent.com"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./database.db"

    # --- Model ---
    DEFAULT_MODEL_TYPE: str = "dual_stream_enhanced"
    WEIGHTS_DIR: str = "../weights"

    # --- Server ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    class Config:
        """Cấu hình cho pydantic-settings."""
        env_file = ENV_FILE_PATH
        env_file_encoding = "utf-8"
        case_sensitive = True


# ---------------------------------------------------------------------------
# Hằng số ứng dụng (không thay đổi)
# ---------------------------------------------------------------------------

# Các loại model hỗ trợ
VALID_MODEL_TYPES = {
    "resnet50",
    "dual_stream_enhanced",
    "dual_stream_resnet",
}

# Mapping model type → đường dẫn weights tương đối (từ WEIGHTS_DIR)
MODEL_WEIGHT_PATHS = {
    "resnet50": "blur_jpg_prob0.1.pth",
    "dual_stream_enhanced": "enhanced/best_model.pth",
    "dual_stream_resnet": "dual_stream_resnet/best_model.pth",
}

# Image processing constants (ImageNet)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Định dạng ảnh hợp lệ
VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

# Kích thước crop theo paper
CROP_SIZE = 224
RESIZE_SIZE = 256

# Thư mục lưu trữ tạm
UPLOAD_TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "upload_temp")
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "download")


@lru_cache()
def get_settings() -> Settings:
    """
    Lấy instance Settings (cached - singleton pattern).

    Returns:
        Settings: Instance cấu hình duy nhất của ứng dụng.
    """
    return Settings()
