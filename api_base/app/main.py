"""
=============================================================================
FastAPI Application Entry Point - CNN Detection API
=============================================================================
Khởi tạo FastAPI app, include routers, cấu hình middleware.

Ứng dụng phát hiện ảnh giả mạo (deepfake detection) sử dụng
các model CNN: ResNet50, DualStreamCNN, DualStreamCNNEnhanced,
DualStreamResNet.

Endpoints chính:
  - GET  /           : Health check
  - GET  /models     : Danh sách model
  - POST /auth/*     : Đăng ký, đăng nhập
  - POST /predict    : Upload ảnh → prediction
  - POST /predict/batch : Batch prediction
"""

import logging
import os

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.download_weights import download_weights_if_needed
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models.base_db import init_db
from app.routers import auth, base, file_upload, history

# Frontend directory (relative to api_base/)
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """
    Factory function tạo FastAPI application.

    Returns:
        FastAPI: Application instance đã cấu hình.
    """
    settings = get_settings()

    app = FastAPI(
        title="CNN Detection API",
        description=(
            "API phát hiện ảnh giả mạo (Deepfake Detection) sử dụng mạng CNN.\n\n"
            "## Tính năng\n"
            "- 🔐 Authentication (JWT)\n"
            "- 🖼️ Upload ảnh → Predict real/fake\n"
            "- 📊 Batch prediction\n"
            "- 🤖 Hỗ trợ 4 model: ResNet50, DualStreamCNN, "
            "DualStreamCNNEnhanced, DualStreamResNet\n\n"
            "## Sử dụng\n"
            "1. Đăng ký tài khoản: `POST /auth/register`\n"
            "2. Đăng nhập: `POST /auth/login` → lấy JWT token\n"
            "3. Predict: `POST /predict` + Bearer token"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- CORS Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Production: thay bằng domain cụ thể
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Include Routers ---
    app.include_router(base.router)
    app.include_router(auth.router)
    app.include_router(file_upload.router)
    app.include_router(history.router)

    # --- Mount Frontend Static Files ---
    # Đã tắt để giải phóng RAM cho Render, frontend được host trên Vercel
    # if FRONTEND_DIR.exists():
    #     app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    # --- Startup Event ---
    @app.on_event("startup")
    async def startup_event():
        """
        Khởi tạo khi server start:
        1. Tạo database tables
        2. Tạo thư mục cần thiết
        3. Preload model mặc định (optional)
        """
        logger.info("=" * 60)
        logger.info("  CNN Detection API - Starting up...")
        logger.info("=" * 60)

        # 1. Init database
        init_db()
        
        # Tải weights từ Google Drive nếu thiếu
        download_weights_if_needed()
        
        logger.info("Database initialized.")

        # 2. Tạo thư mục tạm
        from app.config import UPLOAD_TEMP_DIR, DOWNLOAD_DIR
        os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        logger.info("Temp directories created.")

        # 3. Preload model mặc định
        try:
            from chatbot.services.model_service import get_model_service
            service = get_model_service()
            service.load_model(settings.DEFAULT_MODEL_TYPE)
            logger.info(
                "Default model '%s' loaded on %s.",
                settings.DEFAULT_MODEL_TYPE,
                service.device,
            )
        except Exception as exc:
            logger.warning(
                "Could not preload default model: %s. "
                "Model will be loaded on first request.",
                exc,
            )

        logger.info("CNN Detection API ready!")

    return app


# Tạo app instance
app = create_app()
