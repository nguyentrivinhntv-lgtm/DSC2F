@echo off
chcp 65001 >nul
title 🌙 AI Detector Pro - Dark Mode Only
color 0A
cls

echo.
echo     🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙
echo     🌙                                              🌙
echo     🌙    AI DETECTOR PRO - DARK MODE ONLY        🌙
echo     🌙    Professional Dashboard Interface         🌙
echo     🌙                                              🌙
echo     🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙🌙
echo.
echo ✨ Tất cả giao diện cũ đã bị xóa
echo 🚀 Chỉ còn lại Dark Mode Professional
echo 💫 Đang khởi động...
echo.

python gui_dark_pro.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Lỗi khởi động (Exit code: %errorlevel%)
    echo 🔧 Thử chạy trực tiếp: python gui_dark_pro.py
    echo.
) else (
    echo.
    echo ✅ Dark Mode đã đóng thành công
)

echo.
pause
