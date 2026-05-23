"""Test Enhanced Model với ảnh thật và giả"""
import torch
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from networks.enhanced_dual_stream import EnhancedDualStreamCNN
import os
import glob

# Load model
model_path = 'weights/enhanced/best_model.pth'
model = EnhancedDualStreamCNN(num_classes=1)
state_dict = torch.load(model_path, map_location='cpu', weights_only=False)
model.load_state_dict(state_dict['model'])
model.eval()
print(f"Model loaded from epoch {state_dict['epoch']}")
print(f"Best val acc: {state_dict.get('best_val_acc', 'N/A')}")
print(f"Best val AUC: {state_dict.get('best_val_auc', 'N/A')}")
print("-" * 50)

# Transforms
rgb_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def prepare_fft(image):
    """Chuẩn bị FFT tensor"""
    gray = image.convert('L').resize((224, 224), Image.Resampling.LANCZOS)
    gray_array = np.array(gray, dtype=np.float32) / 255.0
    
    fft = np.fft.fft2(gray_array)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    magnitude_log = np.log1p(magnitude)
    
    magnitude_norm = (magnitude_log - magnitude_log.min()) / (magnitude_log.max() - magnitude_log.min() + 1e-8)
    fft_tensor = torch.from_numpy(magnitude_norm).unsqueeze(0).unsqueeze(0)
    
    return fft_tensor.float()

def predict(image_path):
    """Predict một ảnh"""
    image = Image.open(image_path).convert('RGB')
    
    rgb_tensor = rgb_transform(image).unsqueeze(0)
    fft_tensor = prepare_fft(image)
    
    with torch.no_grad():
        output = model(rgb_tensor, fft_tensor)
        prob = torch.sigmoid(output).item() * 100
    
    return prob

# Test với dataset có sẵn
print("\n=== Test với REAL images ===")
real_dirs = ['dataset/cifake-raw/test/REAL', 'dataset/test/0_real', 'examples/realfakedir/0_real']
for dir_path in real_dirs:
    if os.path.exists(dir_path):
        images = glob.glob(os.path.join(dir_path, '*.*'))[:5]
        if images:
            print(f"\nFolder: {dir_path}")
            for img_path in images:
                try:
                    prob = predict(img_path)
                    verdict = "GIẢ" if prob > 50 else "THẬT"
                    status = "❌" if prob > 50 else "✓"
                    print(f"  {status} {os.path.basename(img_path)}: {prob:.1f}% fake ({verdict})")
                except Exception as e:
                    print(f"  Error: {e}")
            break

print("\n=== Test với FAKE images ===")
fake_dirs = ['dataset/cifake-raw/test/FAKE', 'dataset/test/1_fake', 'examples/realfakedir/1_fake']
for dir_path in fake_dirs:
    if os.path.exists(dir_path):
        images = glob.glob(os.path.join(dir_path, '*.*'))[:5]
        if images:
            print(f"\nFolder: {dir_path}")
            for img_path in images:
                try:
                    prob = predict(img_path)
                    verdict = "GIẢ" if prob > 50 else "THẬT"
                    status = "✓" if prob > 50 else "❌"
                    print(f"  {status} {os.path.basename(img_path)}: {prob:.1f}% fake ({verdict})")
                except Exception as e:
                    print(f"  Error: {e}")
            break
