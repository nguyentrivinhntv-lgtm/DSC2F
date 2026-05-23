"""
So sánh 2 mô hình Dual-Stream CNN và Dual-Stream ResNet
trên cùng bộ dữ liệu test
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
import matplotlib.pyplot as plt
import time

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
    
    return torch.from_numpy(magnitude).float().unsqueeze(0)  # (1, H, W)


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
    return fft_tensor.repeat(3, 1, 1)  # (3, H, W)


def load_test_data(test_dir):
    """Load danh sách ảnh test"""
    samples = []
    
    # Real images
    for real_name in ['0_real', 'REAL', 'real']:
        real_dir = os.path.join(test_dir, real_name)
        if os.path.exists(real_dir):
            for fname in os.listdir(real_dir):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    samples.append((os.path.join(real_dir, fname), 0))
            break
    
    # Fake images
    for fake_name in ['1_fake', 'FAKE', 'fake']:
        fake_dir = os.path.join(test_dir, fake_name)
        if os.path.exists(fake_dir):
            for fname in os.listdir(fake_dir):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    samples.append((os.path.join(fake_dir, fname), 1))
            break
    
    return samples


def evaluate_model(model, samples, model_name, image_size, fft_func, device):
    """Đánh giá 1 model"""
    
    # Transform cho RGB
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
        for img_path, label in tqdm(samples, desc=f"Evaluating {model_name}"):
            try:
                # Load image
                image = Image.open(img_path).convert('RGB')
                
                # Prepare inputs
                rgb = transform(image).unsqueeze(0).to(device)
                fft = fft_func(image, image_size).unsqueeze(0).to(device)
                
                # Forward
                output = model(rgb, fft)
                prob = torch.sigmoid(output).item()
                pred = 1 if prob > 0.5 else 0
                
                all_probs.append(prob)
                all_preds.append(pred)
                all_labels.append(label)
                
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
                continue
    
    elapsed_time = time.time() - start_time
    
    # Calculate metrics
    all_preds = np.array(all_preds)
    all_probs = np.array(all_probs)
    all_labels = np.array(all_labels)
    
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds)
    recall = recall_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds)
    auc = roc_auc_score(all_labels, all_probs)
    cm = confusion_matrix(all_labels, all_preds)
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'auc': auc,
        'confusion_matrix': cm,
        'time': elapsed_time,
        'samples': len(samples),
        'probs': all_probs,
        'labels': all_labels
    }


def print_results(name, results):
    """In kết quả đánh giá"""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  Accuracy:  {results['accuracy']*100:.2f}%")
    print(f"  Precision: {results['precision']*100:.2f}%")
    print(f"  Recall:    {results['recall']*100:.2f}%")
    print(f"  F1-Score:  {results['f1']*100:.2f}%")
    print(f"  AUC:       {results['auc']*100:.2f}%")
    print(f"  Time:      {results['time']:.2f}s ({results['samples']/results['time']:.1f} img/s)")
    print(f"\n  Confusion Matrix:")
    print(f"                 Predicted")
    print(f"                 Real    Fake")
    print(f"  Actual Real    {results['confusion_matrix'][0][0]:5d}   {results['confusion_matrix'][0][1]:5d}")
    print(f"  Actual Fake    {results['confusion_matrix'][1][0]:5d}   {results['confusion_matrix'][1][1]:5d}")


def plot_comparison(results_cnn, results_resnet, save_path='comparison_results.png'):
    """Vẽ biểu đồ so sánh"""
    metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'AUC']
    cnn_values = [
        results_cnn['accuracy']*100,
        results_cnn['precision']*100,
        results_cnn['recall']*100,
        results_cnn['f1']*100,
        results_cnn['auc']*100
    ]
    resnet_values = [
        results_resnet['accuracy']*100,
        results_resnet['precision']*100,
        results_resnet['recall']*100,
        results_resnet['f1']*100,
        results_resnet['auc']*100
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Bar chart
    ax1 = axes[0]
    bars1 = ax1.bar(x - width/2, cnn_values, width, label='Dual-Stream CNN', color='#2196F3')
    bars2 = ax1.bar(x + width/2, resnet_values, width, label='Dual-Stream ResNet', color='#FF5722')
    
    ax1.set_ylabel('Score (%)')
    ax1.set_title('So sánh hiệu suất 2 mô hình')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics)
    ax1.legend()
    ax1.set_ylim([0, 105])
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax1.annotate(f'{height:.1f}%',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8)
    for bar in bars2:
        height = bar.get_height()
        ax1.annotate(f'{height:.1f}%',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8)
    
    # ROC-like comparison (probability distributions)
    ax2 = axes[1]
    
    # Dual-Stream CNN
    real_probs_cnn = results_cnn['probs'][results_cnn['labels'] == 0]
    fake_probs_cnn = results_cnn['probs'][results_cnn['labels'] == 1]
    
    ax2.hist(real_probs_cnn, bins=50, alpha=0.5, label='CNN - Real', color='green')
    ax2.hist(fake_probs_cnn, bins=50, alpha=0.5, label='CNN - Fake', color='red')
    
    ax2.axvline(x=0.5, color='black', linestyle='--', label='Threshold')
    ax2.set_xlabel('Predicted Probability (Fake)')
    ax2.set_ylabel('Count')
    ax2.set_title('Phân bố xác suất dự đoán (Dual-Stream CNN)')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"\nĐã lưu biểu đồ so sánh: {save_path}")


def main():
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Paths
    test_dir = "dataset/test"
    cnn_weights = "weights/dual_stream/best_model.pth"
    resnet_weights = "weights/dual_stream_resnet/best_model.pth"
    
    # Check paths
    if not os.path.exists(test_dir):
        print(f"ERROR: Test directory not found: {test_dir}")
        return
    
    # Load test data
    print("\n" + "="*60)
    print("  LOADING TEST DATA")
    print("="*60)
    samples = load_test_data(test_dir)
    print(f"Loaded {len(samples)} test samples")
    real_count = sum(1 for _, l in samples if l == 0)
    fake_count = sum(1 for _, l in samples if l == 1)
    print(f"  - Real: {real_count}")
    print(f"  - Fake: {fake_count}")
    
    results = {}
    
    # ========== Evaluate Dual-Stream CNN ==========
    if os.path.exists(cnn_weights):
        print("\n" + "="*60)
        print("  LOADING DUAL-STREAM CNN")
        print("="*60)
        
        model_cnn = DualStreamCNN(num_classes=1)
        state = torch.load(cnn_weights, map_location=device, weights_only=False)
        if 'model' in state:
            model_cnn.load_state_dict(state['model'])
        elif 'model_state_dict' in state:
            model_cnn.load_state_dict(state['model_state_dict'])
        else:
            model_cnn.load_state_dict(state)
        model_cnn.to(device)
        
        print(f"Loaded weights from: {cnn_weights}")
        print(f"Image size: 224x224")
        print(f"FFT channels: 1")
        
        results['cnn'] = evaluate_model(
            model_cnn, samples, "Dual-Stream CNN",
            image_size=224, fft_func=compute_fft_1channel, device=device
        )
        print_results("DUAL-STREAM CNN", results['cnn'])
    else:
        print(f"WARNING: CNN weights not found: {cnn_weights}")
    
    # ========== Evaluate Dual-Stream ResNet ==========
    if os.path.exists(resnet_weights):
        print("\n" + "="*60)
        print("  LOADING DUAL-STREAM RESNET")
        print("="*60)
        
        model_resnet = DualStreamResNet(num_classes=1, pretrained=False)
        state = torch.load(resnet_weights, map_location=device, weights_only=False)
        if 'model' in state:
            model_resnet.load_state_dict(state['model'])
        elif 'model_state_dict' in state:
            model_resnet.load_state_dict(state['model_state_dict'])
        else:
            model_resnet.load_state_dict(state)
        model_resnet.to(device)
        
        print(f"Loaded weights from: {resnet_weights}")
        print(f"Image size: 32x32")
        print(f"FFT channels: 3")
        
        results['resnet'] = evaluate_model(
            model_resnet, samples, "Dual-Stream ResNet",
            image_size=32, fft_func=compute_fft_3channel, device=device
        )
        print_results("DUAL-STREAM RESNET (Transfer Learning)", results['resnet'])
    else:
        print(f"WARNING: ResNet weights not found: {resnet_weights}")
    
    # ========== Summary Comparison ==========
    if 'cnn' in results and 'resnet' in results:
        print("\n" + "="*60)
        print("  BẢNG SO SÁNH TỔNG HỢP")
        print("="*60)
        print(f"\n{'Metric':<15} {'Dual-Stream CNN':<20} {'Dual-Stream ResNet':<20} {'Winner'}")
        print("-"*75)
        
        metrics = [
            ('Accuracy', 'accuracy'),
            ('Precision', 'precision'),
            ('Recall', 'recall'),
            ('F1-Score', 'f1'),
            ('AUC', 'auc')
        ]
        
        cnn_wins = 0
        resnet_wins = 0
        
        for name, key in metrics:
            cnn_val = results['cnn'][key] * 100
            resnet_val = results['resnet'][key] * 100
            
            if cnn_val > resnet_val:
                winner = "CNN ✓"
                cnn_wins += 1
            elif resnet_val > cnn_val:
                winner = "ResNet ✓"
                resnet_wins += 1
            else:
                winner = "Tie"
            
            print(f"{name:<15} {cnn_val:>17.2f}%   {resnet_val:>17.2f}%   {winner}")
        
        print("-"*75)
        print(f"\nTotal wins: CNN={cnn_wins}, ResNet={resnet_wins}")
        
        # Speed comparison
        cnn_speed = results['cnn']['samples'] / results['cnn']['time']
        resnet_speed = results['resnet']['samples'] / results['resnet']['time']
        print(f"\nSpeed: CNN={cnn_speed:.1f} img/s, ResNet={resnet_speed:.1f} img/s")
        
        # Plot comparison
        plot_comparison(results['cnn'], results['resnet'])
        
        # Save results to file
        with open('comparison_results.txt', 'w', encoding='utf-8') as f:
            f.write("SO SÁNH 2 MÔ HÌNH DUAL-STREAM\n")
            f.write("="*60 + "\n\n")
            f.write(f"Test dataset: {test_dir}\n")
            f.write(f"Total samples: {len(samples)} (Real: {real_count}, Fake: {fake_count})\n\n")
            
            f.write("DUAL-STREAM CNN\n")
            f.write("-"*40 + "\n")
            f.write(f"  Accuracy:  {results['cnn']['accuracy']*100:.2f}%\n")
            f.write(f"  Precision: {results['cnn']['precision']*100:.2f}%\n")
            f.write(f"  Recall:    {results['cnn']['recall']*100:.2f}%\n")
            f.write(f"  F1-Score:  {results['cnn']['f1']*100:.2f}%\n")
            f.write(f"  AUC:       {results['cnn']['auc']*100:.2f}%\n")
            f.write(f"  Speed:     {cnn_speed:.1f} img/s\n\n")
            
            f.write("DUAL-STREAM RESNET (Transfer Learning)\n")
            f.write("-"*40 + "\n")
            f.write(f"  Accuracy:  {results['resnet']['accuracy']*100:.2f}%\n")
            f.write(f"  Precision: {results['resnet']['precision']*100:.2f}%\n")
            f.write(f"  Recall:    {results['resnet']['recall']*100:.2f}%\n")
            f.write(f"  F1-Score:  {results['resnet']['f1']*100:.2f}%\n")
            f.write(f"  AUC:       {results['resnet']['auc']*100:.2f}%\n")
            f.write(f"  Speed:     {resnet_speed:.1f} img/s\n")
        
        print(f"\nĐã lưu kết quả: comparison_results.txt")


if __name__ == "__main__":
    main()
