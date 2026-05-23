@echo off
echo ============================================
echo   ADVANCED RESNET TRAINING
echo ============================================
echo.
echo Cai thien so voi ban cu:
echo   - ResNet34 thay vi ResNet18
echo   - Image size 128 thay vi 32
echo   - MixUp + CutMix augmentation
echo   - Label Smoothing
echo   - SE (Squeeze-Excitation) blocks
echo   - Stochastic Depth (Drop Path)
echo   - EMA (Exponential Moving Average)
echo   - OneCycleLR scheduler
echo   - RandAugment
echo ============================================
echo.

python train_resnet_advanced.py ^
    --train_dir dataset/train ^
    --val_dir dataset/val ^
    --image_size 128 ^
    --resnet_depth 34 ^
    --use_se ^
    --dropout 0.4 ^
    --drop_path 0.1 ^
    --epochs 50 ^
    --batch_size 32 ^
    --lr 0.0005 ^
    --weight_decay 0.05 ^
    --patience 15 ^
    --scheduler onecycle ^
    --label_smoothing 0.1 ^
    --mixup_alpha 0.4 ^
    --cutmix_alpha 1.0 ^
    --use_randaugment ^
    --use_ema ^
    --save_dir weights/dual_stream_resnet_advanced

echo.
echo Training completed!
pause
