#!/bin/bash
# =============================================================================
# Script khởi chạy API (Linux/Docker)
# =============================================================================

set -e

echo "=== CNN Detection API ==="

# Cài đặt dependencies
pip install -r requirements.txt

# Khởi động server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
