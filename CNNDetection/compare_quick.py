"""
So sánh nhanh 2 mô hình Dual-Stream CNN và Dual-Stream ResNet
Chỉ test trên 1000 ảnh để tiết kiệm thời gian
"""

import os
import sys
import torch
import torch.nn as nn
import numpy as np
from PIL import Image
from tqdm import tqdm
import torchvision.transforms as transforms
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import time
import random

# Import models
from networks.dual_stream_cnn import DualStreamCNN
from networks.dual_stream_resnet import DualStreamResNet


def compute_fft_1channel(image, size=224):
    """FFT cho Dual-Stream CNN (1 channel)"""
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    gray = image.convert('L')
    gray_array = np.array(gray, dtype=np.float32) / 255.0
    
    fft = np.fft.fft2(gray_array)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    magnitude = np.log1p(magnitude)
    magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-8)
    
    return torch.from_numpy(magnitude).float().unsqueeze(0)


def compute_fft_3channel(image, size=32):
    """FFT cho Dual-Stream ResNet (3 channels)"""
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    gray = image.convert('L')
    gray_array = np.array(gray, dtype=np.float32) / 255.0
    
    fft = np.fft.fft2(gray_array)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    magnitude = np.log1p(magnitude)
    magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-8)
    
    fft_tensor = torch.from_numpy(magnitude).float().unsqueeze(0)
    return fft_tensor.repeat(3, 1, 1)


def load_test_data(test_dir, max_samples=500):
    """Load danh sách ảnh test (giới hạn số lượng)"""
    samples = []
    
    # Real images
    for real_name in ['0_real', 'REAL', 'real']:
        real_dir = os.path.join(test_dir, real_name)
        if os.path.exists(real_dir):
            files = [f for f in os.listdir(real_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            random.shuffle(files)
            for fname in files[:max_samples]:
                samples.append((os.path.join(real_dir, fname), 0))
            break
    
    # Fake images
    for fake_name in ['1_fake', 'FAKE', 'fake']:
        fake_dir = os.path.join(test_dir, fake_name)
        if os.path.exists(fake_dir):
            files = [f for f in os.listdir(fake_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            random.shuffle(files)
            for fname in files[:max_samples]:
                samples.append((os.path.join(fake_dir, fname), 1))
            break
    
    return samples


def evaluate_model(model, samples, model_name, image_size, fft_func, device):
    """Đánh giá 1 model"""
    
    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    model.eval()
    all_preds = []
    all_probs = []
    all_labels = []
    
    start_time = time.time()
    
    with torch.no_grad():
        for img_path, label in tqdm(samples, desc=f"{model_name}"):
            try:
                image = Image.open(img_path).convert('RGB')
                rgb = transform(image).unsqueeze(0).to(device)
                fft = fft_func(image, image_size).unsqueeze(0).to(device)
                
                output = model(rgb, fft)
                prob = torch.sigmoid(output).item()
                pred = 1 if prob > 0.5 else 0
                
                all_probs.append(prob)
                all_preds.append(pred)
                all_labels.append(label)
            except Exception as e:
                continue
    
    elapsed_time = time.time() - start_time
    
    all_preds = np.array(all_preds)
    all_probs = np.array(all_probs)
    all_labels = np.array(all_labels)
    
    return {
        'accuracy': accuracy_score(all_labels, all_preds),
        'precision': precision_score(all_labels, all_preds),
        'recall': recall_score(all_labels, all_preds),
        'f1': f1_score(all_labels, all_preds),
        'auc': roc_auc_score(all_labels, all_probs),
        'confusion_matrix': confusion_matrix(all_labels, all_preds),
        'time': elapsed_time,
        'samples': len(samples),
        'speed': len(samples) / elapsed_time
    }


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    
    test_dir = "dataset/test"
    cnn_weights = "weights/dual_stream/best_model.pth"
    resnet_weights = "weights/dual_stream_resnet/best_model.pth"
    
    # Load subset of test data
    print("\n" + "="*70)
    print("  LOADING TEST DATA (500 real + 500 fake = 1000 samples)")
    print("="*70)
    samples = load_test_data(test_dir, max_samples=500)
    print(f"Total: {len(samples)} samples")
    
    results = {}
    
    # ========== Dual-Stream CNN ==========
    if os.path.exists(cnn_weights):
        print("\n[1/2] Dual-Stream CNN (224x224, FFT 1ch)")
        model_cnn = DualStreamCNN(num_classes=1)
        state = torch.load(cnn_weights, map_location=device, weights_only=False)
        model_cnn.load_state_dict(state['model'])
        model_cnn.to(device)
        
        results['cnn'] = evaluate_model(
            model_cnn, samples, "CNN",
            image_size=224, fft_func=compute_fft_1channel, device=device
        )
    
    # ========== Dual-Stream ResNet ==========
    if os.path.exists(resnet_weights):
        print("\n[2/2] Dual-Stream ResNet (32x32, FFT 3ch)")
        model_resnet = DualStreamResNet(num_classes=1, pretrained=False)
        state = torch.load(resnet_weights, map_location=device, weights_only=False)
        model_resnet.load_state_dict(state['model'])
        model_resnet.to(device)
        
        results['resnet'] = evaluate_model(
            model_resnet, samples, "ResNet",
            image_size=32, fft_func=compute_fft_3channel, device=device
        )
    
    # ========== Print Results ==========
    print("\n" + "="*70)
    print("  KẾT QUẢ SO SÁNH")
    print("="*70)
    
    print(f"\n{'Metric':<15} {'Dual-Stream CNN':<20} {'Dual-Stream ResNet':<20} {'Better'}")
    print("-"*75)
    
    metrics = [
        ('Accuracy', 'accuracy'),
        ('Precision', 'precision'),
        ('Recall', 'recall'),
        ('F1-Score', 'f1'),
        ('AUC', 'auc'),
    ]
    
    for name, key in metrics:
        cnn_val = results['cnn'][key] * 100
        resnet_val = results['resnet'][key] * 100
        diff = resnet_val - cnn_val
        
        if diff > 0:
            better = f"ResNet (+{diff:.1f}%)"
        elif diff < 0:
            better = f"CNN (+{-diff:.1f}%)"
        else:
            better = "Tie"
        
        print(f"{name:<15} {cnn_val:>17.2f}%   {resnet_val:>17.2f}%   {better}")
    
    print("-"*75)
    print(f"{'Speed':<15} {results['cnn']['speed']:>14.1f} img/s   {results['resnet']['speed']:>14.1f} img/s")
    
    # Confusion matrices
    print("\n" + "="*70)
    print("  CONFUSION MATRICES")
    print("="*70)
    
    print("\nDual-Stream CNN:")
    cm = results['cnn']['confusion_matrix']
    print(f"                Predicted Real    Predicted Fake")
    print(f"  Actual Real        {cm[0][0]:5d}            {cm[0][1]:5d}")
    print(f"  Actual Fake        {cm[1][0]:5d}            {cm[1][1]:5d}")
    
    print("\nDual-Stream ResNet:")
    cm = results['resnet']['confusion_matrix']
    print(f"                Predicted Real    Predicted Fake")
    print(f"  Actual Real        {cm[0][0]:5d}            {cm[0][1]:5d}")
    print(f"  Actual Fake        {cm[1][0]:5d}            {cm[1][1]:5d}")
    
    # Summary
    print("\n" + "="*70)
    print("  TÓM TẮT")
    print("="*70)
    
    cnn_auc = results['cnn']['auc']
    resnet_auc = results['resnet']['auc']
    
    if resnet_auc > cnn_auc:
        print(f"\n  >>> DUAL-STREAM RESNET tốt hơn (AUC: {resnet_auc*100:.2f}% vs {cnn_auc*100:.2f}%)")
    else:
        print(f"\n  >>> DUAL-STREAM CNN tốt hơn (AUC: {cnn_auc*100:.2f}% vs {resnet_auc*100:.2f}%)")
    
    print(f"\n  Lưu ý: Dataset test này có ảnh 32x32 (CIFAKE)")
    print(f"  - ResNet được train với 32x32 → phù hợp hơn")
    print(f"  - CNN được train với 224x224 → cần resize")


if __name__ == "__main__":
    random.seed(42)
    main()
