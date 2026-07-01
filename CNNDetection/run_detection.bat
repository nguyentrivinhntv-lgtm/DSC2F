@echo off
REM Script de chay ung dung CNN Detection
REM Su dung: run_detection.bat <image_path>

if "%1"=="" (
    echo Su dung: run_detection.bat ^<duong_dan_anh^>
    echo Vi du: run_detection.bat examples/real.png
    pause
    exit /b 1
)

echo Dang phan tich anh: %1
C:\Users\84328\miniconda3\Scripts\conda.exe run -p C:\Users\84328\miniconda3 --no-capture-output python demo.py -f %1 -m weights/blur_jpg_prob0.5.pth --use_cpu

pause