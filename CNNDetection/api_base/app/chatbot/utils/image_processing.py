"""
=============================================================================
Image Processing Utilities - CNN Detection API
=============================================================================
Tiền xử lý ảnh cho các model CNN Detection.
Bao gồm: transform, FFT computation, resize/crop.

Theo đúng quy trình paper CNNDetection:
  - CenterCrop(224) + Normalize(ImageNet mean/std)
  - FFT spectrum cho dual-stream models
"""

import sys
import os

import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image

from app.config import IMAGENET_MEAN, IMAGENET_STD

def preprocess_image(image: Image.Image, model_type: str = "enhanced") -> torch.Tensor:
    """
    Tiền xử lý ảnh PIL thành tensor khớp hoàn toàn với bản desktop (gui_dark_pro) và eval_cifar10.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    image_size = (224, 224)
    
    transform = transforms.Compose([
        transforms.Resize(image_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])
    
    return transform(image).unsqueeze(0)

def compute_fft_spectrum_gui(image: Image.Image, model_type: str = "enhanced") -> torch.Tensor:
    """
    Logic tính FFT giống hệt Hàm prepare_fft_tensor trong gui_dark_pro.py và eval_cifar10.py.
    """
    # 1. Resize & Grayscale
    size = 224
    gray = image.convert('L').resize((size, size), Image.Resampling.LANCZOS)
    gray_array = np.array(gray, dtype=np.float32) / 255.0
    
    # 2. Compute FFT
    fft = np.fft.fft2(gray_array)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    magnitude_log = np.log1p(magnitude)
    
    # 3. Normalize
    magnitude_norm = (magnitude_log - magnitude_log.min()) / (magnitude_log.max() - magnitude_log.min())
    
    # 4. Shape for specific models
    if model_type == 'dual_stream_resnet':
        # 3 channels
        fft_tensor = torch.from_numpy(magnitude_norm).unsqueeze(0).repeat(3, 1, 1).unsqueeze(0)
    else:
        # 1 channel
        fft_tensor = torch.from_numpy(magnitude_norm).unsqueeze(0).unsqueeze(0)
        
    return fft_tensor.float()
