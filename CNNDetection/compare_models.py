"""So sánh tất cả models với ảnh test"""
import torch
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import os
import glob
import sys

# Test với một ảnh cụ thể mà user báo sai
# Nếu không có, dùng mẫu từ dataset

print("=" * 60)
print("SO SANH HIEU SUAT CAC MO HINH")
print("=" * 60)

# 1. Load model gốc (ResNet50 pretrained)
print("\n[1] Model Gốc (CNN Detection - ResNet50)")
try:
    from networks.resnet import resnet50
    model1 = resnet50(num_classes=1)
    path1 = 'weights/blur_jpg_prob0.5.pth'
    if os.path.exists(path1):
        state = torch.load(path1, map_location='cpu', weights_only=False)
        model1.load_state_dict(state['model'])
        model1.eval()
        print(f"   ✓ Loaded từ {path1}")
    else:
        model1 = None
        print(f"   ✗ Không tìm thấy {path1}")
except Exception as e:
    model1 = None
    print(f"   ✗ Lỗi: {e}")

# 2. Load FFT-Only Enhanced
print("\n[2] FFT-Only Enhanced")
try:
    from networks.dual_stream_enhanced import FFTOnlyCNNEnhanced
    model2 = FFTOnlyCNNEnhanced(num_classes=1)
    path2 = 'weights/fft_only_enhanced/best_model.pth'
    if os.path.exists(path2):
        state = torch.load(path2, map_location='cpu', weights_only=False)
        if 'model' in state:
            model2.load_state_dict(state['model'])
        elif 'state_dict' in state:
            model2.load_state_dict(state['state_dict'])
        else:
            model2.load_state_dict(state)
        model2.eval()
        print(f"   ✓ Loaded từ {path2}")
    else:
        model2 = None
        print(f"   ✗ Không tìm thấy {path2}")
except Exception as e:
    model2 = None
    print(f"   ✗ Lỗi: {e}")

# 3. Load Enhanced Dual Stream
print("\n[3] Enhanced Dual Stream (Mới nhất)")
try:
    from networks.enhanced_dual_stream import EnhancedDualStreamCNN
    model3 = EnhancedDualStreamCNN(num_classes=1)
    path3 = 'weights/enhanced/best_model.pth'
    if os.path.exists(path3):
        state = torch.load(path3, map_location='cpu', weights_only=False)
        model3.load_state_dict(state['model'])
        model3.eval()
        print(f"   ✓ Loaded từ {path3}")
        print(f"   Best Acc: {state.get('best_val_acc', 'N/A')}")
    else:
        model3 = None
        print(f"   ✗ Không tìm thấy {path3}")
except Exception as e:
    model3 = None
    print(f"   ✗ Lỗi: {e}")

# Transforms
transform_224 = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

transform_32 = transforms.Compose([
    transforms.Resize((32, 32)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def prepare_fft(image, size=224):
    gray = image.convert('L').resize((size, size), Image.Resampling.LANCZOS)
    gray_array = np.array(gray, dtype=np.float32) / 255.0
    
    fft = np.fft.fft2(gray_array)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    magnitude_log = np.log1p(magnitude)
    magnitude_norm = (magnitude_log - magnitude_log.min()) / (magnitude_log.max() - magnitude_log.min() + 1e-8)
    
    return magnitude_norm

def predict_all(image_path):
    """Predict với tất cả models"""
    results = {}
    image = Image.open(image_path).convert('RGB')
    
    # Model 1: ResNet50 (224x224, no FFT)
    if model1:
        rgb = transform_224(image).unsqueeze(0)
        with torch.no_grad():
            out = model1(rgb)
            results['ResNet50'] = torch.sigmoid(out).item() * 100
    
    # Model 2: FFT-Only Enhanced (224x224)
    if model2:
        rgb = transform_224(image).unsqueeze(0)
        fft = prepare_fft(image, 224)
        fft_tensor = torch.from_numpy(fft).unsqueeze(0).unsqueeze(0).float()
        with torch.no_grad():
            out = model2(rgb, fft_tensor)
            results['FFT-Only'] = torch.sigmoid(out).item() * 100
    
    # Model 3: Enhanced (224x224)
    if model3:
        rgb = transform_224(image).unsqueeze(0)
        fft = prepare_fft(image, 224)
        fft_tensor = torch.from_numpy(fft).unsqueeze(0).unsqueeze(0).float()
        with torch.no_grad():
            out = model3(rgb, fft_tensor)
            results['Enhanced'] = torch.sigmoid(out).item() * 100
    
    return results

# Test
print("\n" + "=" * 60)
print("KẾT QUẢ PHÂN TÍCH")
print("=" * 60)

# Tìm ảnh test
test_folders = [
    ('REAL', ['dataset/cifake-raw/test/REAL', 'dataset/test/0_real']),
    ('FAKE', ['dataset/cifake-raw/test/FAKE', 'dataset/test/1_fake'])
]

for label, folders in test_folders:
    print(f"\n--- Ảnh {label} ---")
    for folder in folders:
        if os.path.exists(folder):
            images = glob.glob(os.path.join(folder, '*.*'))[:3]
            for img_path in images:
                try:
                    results = predict_all(img_path)
                    print(f"\n  📷 {os.path.basename(img_path)}")
                    for name, prob in results.items():
                        verdict = "GIẢ" if prob > 50 else "THẬT"
                        icon = "✗" if (label=="REAL" and prob>50) or (label=="FAKE" and prob<=50) else "✓"
                        print(f"     {icon} {name}: {prob:.1f}% fake -> {verdict}")
                except Exception as e:
                    print(f"  Error {img_path}: {e}")
            break
