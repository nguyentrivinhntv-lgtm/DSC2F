@echo off
chcp 65001 >nul
title 🌙 AI Detector Pro - Dark Mode Professional
color 0A
cls

echo.
echo     ███████╗ ███████╗ ██████╗ ██████╗   ██████╗  
echo     ██╔══██╗ ██╔═══██╗██╔══██╗██╔══██╗ ██╔═══██╗ 
echo     ██████╔╝ ██████╔╝██║   ██║██████╔╝ ██║   ██║ 
echo     ██╔═══╝  ██╔══██╗██║   ██║██╔═══╝  ██║   ██║ 
echo     ██║      ██║  ██║╚██████╔╝██║      ╚██████╔╝ 
echo     ╚═╝      ╚═╝  ╚═╝ ╚═════╝ ╚═╝       ╚═════╝  
echo.                              
echo     🌙 AI DETECTOR PRO - DARK MODE PROFESSIONAL
echo     📊 Dashboard chuyên nghiệp cho phân tích AI deepfake
echo.
echo ═══════════════════════════════════════════════════════════════════════

echo 🔍 Kiểm tra môi trường Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ KHÔNG TÌM THẤY PYTHON!
    echo 📝 Vui lòng cài đặt Python 3.8+ từ python.org
    pause
    exit /b 1
)

echo ✅ Python đã sẵn sàng
echo 🧠 Kiểm tra thư viện AI...

python -c "import torch, torchvision, PIL, numpy" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Thiếu thư viện cần thiết!
    echo 📦 Đang cài đặt dependencies...
    pip install torch torchvision pillow numpy
    if %errorlevel% neq 0 (
        echo ❌ Lỗi cài đặt thư viện!
        pause
        exit /b 1
    )
)

echo ✅ Thư viện AI hoàn chỉnh
echo 🚀 Khởi động Professional Dark Mode GUI...
echo.

python gui_dark_pro.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Ứng dụng gặp lỗi (Exit code: %errorlevel%)
    echo 🔧 Thử các bước sau:
    echo    1. Kiểm tra file gui_dark_pro.py có tồn tại
    echo    2. Đảm bảo thư mục 'weights' có model files  
    echo    3. Chạy lệnh: pip install --upgrade torch pillow
    echo.
) else (
    echo.
    echo ✅ Ứng dụng đã đóng thành công
)

echo.
pause