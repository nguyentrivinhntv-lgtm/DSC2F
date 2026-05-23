# CNN Detection API

API phát hiện ảnh giả mạo (Deepfake Detection) sử dụng FastAPI và các model CNN.

## Cài đặt

```bash
cd api_base
pip install -r requirements.txt
```

## Chạy server

```bash
python run_api.py
# hoặc
python run_api.py --port 8080 --reload
```

Server chạy tại: `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

## API Endpoints

### 🔓 Public

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/` | Health check |
| GET | `/models` | Danh sách model |
| POST | `/auth/register` | Đăng ký tài khoản |
| POST | `/auth/login` | Đăng nhập → JWT token |

### 🔐 Protected (cần JWT token)

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/predict` | Upload 1 ảnh → predict |
| POST | `/predict/batch` | Upload nhiều ảnh → batch predict |

## Sử dụng

### 1. Đăng ký

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test123"}'
```

### 2. Đăng nhập

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test123"}'
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "username": "test"
}
```

### 3. Predict

```bash
curl -X POST http://localhost:8000/predict \
  -H "Authorization: Bearer eyJ..." \
  -F "file=@image.jpg" \
  -F "model_type=dual_stream_enhanced"
```

Response:
```json
{
  "filename": "image.jpg",
  "probability": 0.9234,
  "percentage": "92.34%",
  "label": "fake",
  "confidence": "92.34%",
  "model_used": "dual_stream_enhanced"
}
```

## Models

| Model | Mô tả |
|-------|--------|
| `resnet50` | ResNet50 single-stream (paper gốc) |
| `dual_stream` | DualStreamCNN (RGB + FFT) |
| `dual_stream_enhanced` | DualStreamCNN + CBAM Attention (mặc định) |
| `dual_stream_resnet` | DualStream + ResNet18 backbone |

## Cấu trúc

```
api_base/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Cấu hình (.env)
│   ├── models/
│   │   └── base_db.py       # SQLite database
│   ├── routers/
│   │   ├── auth.py          # API đăng ký/đăng nhập
│   │   ├── base.py          # Health check
│   │   └── file_upload.py   # API predict
│   ├── security/
│   │   └── security.py      # JWT + bcrypt
│   └── utils/
│       └── helpers.py       # Tiện ích
├── chatbot/
│   ├── services/
│   │   └── model_service.py # Model inference
│   └── utils/
│       └── image_processing.py
├── utils/
│   ├── upload_temp/
│   └── download/
├── .env
├── requirements.txt
├── run_api.py
└── start.sh
```
