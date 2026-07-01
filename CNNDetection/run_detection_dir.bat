@echo off
REM Script de chay ung dung CNN Detection tren thu muc
REM Su dung: run_detection_dir.bat <duong_dan_thu_muc>

if "%1"=="" (
    echo Su dung: run_detection_dir.bat ^<duong_dan_thu_muc^>
    echo Vi du: run_detection_dir.bat examples/realfakedir
    pause
    exit /b 1
)

echo Dang phan tich thu muc: %1
C:\Users\84328\miniconda3\Scripts\conda.exe run -p C:\Users\84328\miniconda3 --no-capture-output python demo_dir.py -d %1 -m weights/blur_jpg_prob0.5.pth --use_cpu

pause