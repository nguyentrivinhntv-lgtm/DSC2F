@echo off
title Dual-Stream CNN Training
echo ================================================================
echo    DUAL-STREAM CNN TRAINING - Phat Hien Hinh Anh Gia Mao
echo ================================================================
echo.
echo Ket hop Spatial Stream (RGB) va Frequency Stream (FFT)
echo.

cd /d "%~dp0"

REM Kiem tra thu muc data
if not exist "dataset\train" (
    echo [LOI] Khong tim thay thu muc dataset\train
    echo Vui long tao cau truc:
    echo   dataset\train\0_real\  - Chua anh that
    echo   dataset\train\1_fake\  - Chua anh gia
    echo.
    pause
    exit /b 1
)

echo Bat dau training...
echo.

python train_dual_stream.py ^
    --train_dir dataset/train ^
    --val_dir dataset/val ^
    --model dual_stream ^
    --epochs 50 ^
    --batch_size 32 ^
    --lr 0.0001 ^
    --image_size 224 ^
    --save_dir weights/dual_stream

echo.
echo ================================================================
echo Training hoan tat!
echo Model duoc luu tai: weights/dual_stream/best_model.pth
echo ================================================================
pause
