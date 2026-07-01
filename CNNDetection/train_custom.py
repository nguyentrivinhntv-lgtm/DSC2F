"""
HƯỚNG DẪN TRAIN MODEL VỚI DỮ LIỆU MỚI
=====================================

Vấn đề: Model hiện tại được train trên CIFAKE (Stable Diffusion), 
không phát hiện tốt ảnh Gemini 3 Pro và ảnh chụp điện thoại.

Giải pháp: Train lại với dữ liệu của bạn.

BƯỚC 1: Chuẩn bị dữ liệu
------------------------
Tạo cấu trúc thư mục:

dataset/
├── custom/
│   ├── train/
│   │   ├── REAL/     <- Đặt 500-1000 ảnh thật chụp từ điện thoại
│   │   └── FAKE/     <- Đặt 500-1000 ảnh từ Gemini 3 Pro
│   └── test/
│       ├── REAL/     <- Đặt 100-200 ảnh thật khác (không trùng train)
│       └── FAKE/     <- Đặt 100-200 ảnh Gemini khác

BƯỚC 2: Chạy script train
-------------------------
python train_custom.py

BƯỚC 3: Test model mới
----------------------
python test_your_image.py "path/to/image.jpg"
"""

import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image
import numpy as np
from tqdm import tqdm
import glob

# Import model
from networks.enhanced_dual_stream import EnhancedDualStreamCNN


class CustomDataset(Dataset):
    """Dataset cho ảnh custom (điện thoại + Gemini)"""
    
    def __init__(self, root_dir, transform=None, is_train=True):
        self.transform = transform
        self.images = []
        self.labels = []
        
        split = 'train' if is_train else 'test'
        
        # Load REAL images (label = 0)
        real_dir = os.path.join(root_dir, split, 'REAL')
        if os.path.exists(real_dir):
            real_images = glob.glob(os.path.join(real_dir, '*.*'))
            self.images.extend(real_images)
            self.labels.extend([0] * len(real_images))
            print(f"  Loaded {len(real_images)} REAL images from {real_dir}")
        
        # Load FAKE images (label = 1)
        fake_dir = os.path.join(root_dir, split, 'FAKE')
        if os.path.exists(fake_dir):
            fake_images = glob.glob(os.path.join(fake_dir, '*.*'))
            self.images.extend(fake_images)
            self.labels.extend([1] * len(fake_images))
            print(f"  Loaded {len(fake_images)} FAKE images from {fake_dir}")
        
        print(f"  Total: {len(self.images)} images")
    
    def __len__(self):
        return len(self.images)
    
    def prepare_fft(self, image):
        """Chuẩn bị FFT tensor"""
        gray = image.convert('L').resize((224, 224), Image.Resampling.LANCZOS)
        gray_array = np.array(gray, dtype=np.float32) / 255.0
        
        fft = np.fft.fft2(gray_array)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)
        magnitude_log = np.log1p(magnitude)
        magnitude_norm = (magnitude_log - magnitude_log.min()) / (magnitude_log.max() - magnitude_log.min() + 1e-8)
        
        return torch.from_numpy(magnitude_norm).unsqueeze(0).float()
    
    def __getitem__(self, idx):
        img_path = self.images[idx]
        label = self.labels[idx]
        
        try:
            image = Image.open(img_path).convert('RGB')
        except:
            # Return random noise if image fails to load
            return torch.randn(3, 224, 224), torch.randn(1, 224, 224), torch.tensor(0)
        
        if self.transform:
            rgb_tensor = self.transform(image)
        else:
            rgb_tensor = transforms.ToTensor()(image.resize((224, 224)))
        
        fft_tensor = self.prepare_fft(image)
        
        return rgb_tensor, fft_tensor, torch.tensor(label, dtype=torch.float32)


def train_model():
    print("=" * 60)
    print("TRAIN MODEL VỚI DỮ LIỆU CUSTOM (Điện thoại + Gemini)")
    print("=" * 60)
    
    # Config
    data_dir = 'dataset/custom'
    batch_size = 16
    epochs = 20
    lr = 0.0001
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print(f"\nDevice: {device}")
    print(f"Data directory: {data_dir}")
    
    # Check data exists
    if not os.path.exists(data_dir):
        print(f"\n❌ Không tìm thấy thư mục: {data_dir}")
        print("\nHãy tạo cấu trúc thư mục như sau:")
        print("  dataset/custom/train/REAL/  <- ảnh thật chụp điện thoại")
        print("  dataset/custom/train/FAKE/  <- ảnh từ Gemini")
        print("  dataset/custom/test/REAL/")
        print("  dataset/custom/test/FAKE/")
        return
    
    # Transforms
    train_transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    test_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Datasets
    print("\nLoading datasets...")
    train_dataset = CustomDataset(data_dir, transform=train_transform, is_train=True)
    test_dataset = CustomDataset(data_dir, transform=test_transform, is_train=False)
    
    if len(train_dataset) == 0:
        print("❌ Không có ảnh trong thư mục train!")
        return
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    # Model
    print("\nInitializing model...")
    model = EnhancedDualStreamCNN(num_classes=1)
    
    # Load pretrained weights (fine-tune)
    pretrained_path = 'weights/enhanced/best_model.pth'
    if os.path.exists(pretrained_path):
        print(f"Loading pretrained weights from {pretrained_path}")
        state = torch.load(pretrained_path, map_location='cpu', weights_only=False)
        model.load_state_dict(state['model'])
    
    model = model.to(device)
    
    # Loss & Optimizer
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    # Training
    best_acc = 0
    save_dir = 'weights/custom'
    os.makedirs(save_dir, exist_ok=True)
    
    print("\n" + "=" * 60)
    print("BẮT ĐẦU TRAINING")
    print("=" * 60)
    
    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{epochs}')
        for rgb, fft, labels in pbar:
            rgb = rgb.to(device)
            fft = fft.to(device)
            labels = labels.to(device).unsqueeze(1)
            
            optimizer.zero_grad()
            outputs = model(rgb, fft)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            preds = (torch.sigmoid(outputs) > 0.5).float()
            train_correct += (preds == labels).sum().item()
            train_total += labels.size(0)
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}', 'acc': f'{100*train_correct/train_total:.1f}%'})
        
        scheduler.step()
        
        # Evaluate
        model.eval()
        test_correct = 0
        test_total = 0
        
        with torch.no_grad():
            for rgb, fft, labels in test_loader:
                rgb = rgb.to(device)
                fft = fft.to(device)
                labels = labels.to(device).unsqueeze(1)
                
                outputs = model(rgb, fft)
                preds = (torch.sigmoid(outputs) > 0.5).float()
                test_correct += (preds == labels).sum().item()
                test_total += labels.size(0)
        
        test_acc = 100 * test_correct / test_total if test_total > 0 else 0
        train_acc = 100 * train_correct / train_total
        
        print(f'  Train Acc: {train_acc:.1f}% | Test Acc: {test_acc:.1f}%')
        
        # Save best model
        if test_acc > best_acc:
            best_acc = test_acc
            torch.save({
                'epoch': epoch + 1,
                'model': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'best_acc': best_acc
            }, os.path.join(save_dir, 'best_model.pth'))
            print(f'  ✓ Saved best model (acc: {best_acc:.1f}%)')
        
        # Always save latest
        torch.save({
            'epoch': epoch + 1,
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'best_acc': best_acc
        }, os.path.join(save_dir, 'latest.pth'))
    
    print("\n" + "=" * 60)
    print(f"TRAINING HOÀN TẤT!")
    print(f"Best accuracy: {best_acc:.1f}%")
    print(f"Model saved to: {save_dir}/best_model.pth")
    print("=" * 60)
    print("\nĐể test model mới, chạy:")
    print('  python test_custom_model.py "path/to/image.jpg"')


if __name__ == '__main__':
    train_model()
