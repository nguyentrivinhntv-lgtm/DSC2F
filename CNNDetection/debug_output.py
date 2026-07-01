"""Debug model output"""
import torch
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from networks.enhanced_dual_stream import EnhancedDualStreamCNN
import os
import glob

# Load model Enhanced
model = EnhancedDualStreamCNN(num_classes=1)
state = torch.load('weights/enhanced/best_model.pth', map_location='cpu', weights_only=False)
model.load_state_dict(state['model'])
model.eval()

print('Model info:')
print(f'  Epoch: {state["epoch"]}')
print(f'  Best Val Acc: {state.get("best_val_acc", "N/A")}')
print()

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

# Test với ảnh thật
real_images = glob.glob('dataset/cifake-raw/test/REAL/*.*')[:5]
print('=== KIEM TRA ANH THAT ===')
for img_path in real_images:
    img = Image.open(img_path).convert('RGB')
    rgb = transform(img).unsqueeze(0)
    fft = prepare_fft(img)
    
    with torch.no_grad():
        raw_output = model(rgb, fft)
        prob = torch.sigmoid(raw_output).item() * 100
        
    print(f'{os.path.basename(img_path)}:')
    print(f'  Raw output (truoc sigmoid): {raw_output.item():.4f}')
    print(f'  Probability: {prob:.1f}% fake')
    print()

# Test với ảnh giả
fake_images = glob.glob('dataset/cifake-raw/test/FAKE/*.*')[:5]
print('=== KIEM TRA ANH GIA ===')
for img_path in fake_images:
    img = Image.open(img_path).convert('RGB')
    rgb = transform(img).unsqueeze(0)
    fft = prepare_fft(img)
    
    with torch.no_grad():
        raw_output = model(rgb, fft)
        prob = torch.sigmoid(raw_output).item() * 100
        
    print(f'{os.path.basename(img_path)}:')
    print(f'  Raw output (truoc sigmoid): {raw_output.item():.4f}')
    print(f'  Probability: {prob:.1f}% fake')
    print()
