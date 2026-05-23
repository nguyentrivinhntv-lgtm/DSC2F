"""
Test nhanh với ảnh của bạn
Chạy: python test_your_image.py "đường/dẫn/ảnh/của/bạn.jpg"
"""
import sys
import torch
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import os

if len(sys.argv) < 2:
    print("Cách dùng: python test_your_image.py 'duong/dan/anh.jpg'")
    print()
    print("Hoặc kéo thả ảnh vào đây rồi nhấn Enter:")
    image_path = input().strip().strip('"').strip("'")
else:
    image_path = sys.argv[1]

if not os.path.exists(image_path):
    print(f"Không tìm thấy file: {image_path}")
    sys.exit(1)

print(f"Testing: {image_path}")
print("-" * 50)

# Load Enhanced model
from networks.enhanced_dual_stream import EnhancedDualStreamCNN
model = EnhancedDualStreamCNN(num_classes=1)
state = torch.load('weights/enhanced/best_model.pth', map_location='cpu', weights_only=False)
model.load_state_dict(state['model'])
model.eval()
print("Loaded model: Enhanced Dual-Stream")

# Transform
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def prepare_fft(image):
    gray = image.convert('L').resize((224, 224), Image.Resampling.LANCZOS)
    gray_array = np.array(gray, dtype=np.float32) / 255.0
    fft = np.fft.fft2(gray_array)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    magnitude_log = np.log1p(magnitude)
    magnitude_norm = (magnitude_log - magnitude_log.min()) / (magnitude_log.max() - magnitude_log.min() + 1e-8)
    return torch.from_numpy(magnitude_norm).unsqueeze(0).unsqueeze(0).float()

# Test
img = Image.open(image_path).convert('RGB')
print(f"Image size: {img.size}")
print(f"Image mode: {img.mode}")

rgb = transform(img).unsqueeze(0)
fft = prepare_fft(img)

print(f"RGB tensor shape: {rgb.shape}")
print(f"FFT tensor shape: {fft.shape}")

with torch.no_grad():
    raw_output = model(rgb, fft)
    prob = torch.sigmoid(raw_output).item() * 100

print("-" * 50)
print(f"Raw output (trước sigmoid): {raw_output.item():.4f}")
print(f"Xác suất GIẢ: {prob:.1f}%")
print()

if prob < 30:
    print("✓ KẾT LUẬN: ẢNH THẬT (xác suất giả thấp)")
elif prob < 70:
    print("? KẾT LUẬN: KHÔNG RÕ (cần kiểm tra thêm)")
else:
    print("✗ KẾT LUẬN: ẢNH GIẢ (xác suất giả cao)")

print()
print("Nếu kết quả sai, có thể do:")
print("1. Ảnh từ nguồn AI khác (Midjourney, DALL-E, Stable Diffusion...)")
print("2. Ảnh đã bị chỉnh sửa/nén nhiều")
print("3. Model chưa được train với loại ảnh này")
