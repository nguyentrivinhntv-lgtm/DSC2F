FROM python:3.10-slim

# Cài đặt các thư viện hệ thống cần thiết (bao gồm gcc, libgl cho opencv nếu có)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy file requirements
COPY api_base/requirements.txt ./

# Cài đặt PyTorch CPU-only để giảm kích thước image
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
# Cài đặt các requirements khác
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code và weights
COPY networks/ ./networks/
COPY api_base/ ./api_base/
COPY frontend/ ./frontend/

# Tạo sẵn thư mục weights trống (code Python sẽ tự tải model vào đây)
RUN mkdir -p ./weights/

# Tải weights ngay trong lúc build Docker để tránh lỗi Timeout khi deploy
RUN python api_base/app/download_weights.py

# Môi trường
ENV PYTHONPATH=/app
ENV WEIGHTS_DIR=/app/weights
ENV DEBUG=False

# Chạy app
CMD ["python", "api_base/run_api.py", "--host", "0.0.0.0"]
