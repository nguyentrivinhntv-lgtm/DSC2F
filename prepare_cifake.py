"""
Script tải và chuẩn bị CIFAKE Dataset cho Dual-Stream CNN Training

CIFAKE Dataset:
- 60,000 ảnh REAL từ CIFAR-10
- 60,000 ảnh FAKE được tạo bởi Stable Diffusion
- Kích thước: 32x32 pixels
- Link: https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images
"""

import os
import shutil
import zipfile
import requests
from tqdm import tqdm
import random


def download_file(url, dest_path):
    """Download file với progress bar"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(dest_path, 'wb') as f:
        with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                pbar.update(len(chunk))


def prepare_cifake_structure(source_dir, target_dir):
    """
    Chuyển đổi cấu trúc CIFAKE sang format của chúng ta
    
    CIFAKE structure:
        train/REAL/
        train/FAKE/
        test/REAL/
        test/FAKE/
    
    Target structure:
        train/0_real/
        train/1_fake/
        val/0_real/
        val/1_fake/
        test/0_real/
        test/1_fake/
    """
    print("Chuẩn bị cấu trúc thư mục...")
    
    # Tạo thư mục đích
    for split in ['train', 'val', 'test']:
        os.makedirs(os.path.join(target_dir, split, '0_real'), exist_ok=True)
        os.makedirs(os.path.join(target_dir, split, '1_fake'), exist_ok=True)
    
    # Copy train data
    train_real_src = os.path.join(source_dir, 'train', 'REAL')
    train_fake_src = os.path.join(source_dir, 'train', 'FAKE')
    
    if os.path.exists(train_real_src):
        print("Copying training REAL images...")
        real_files = os.listdir(train_real_src)
        random.shuffle(real_files)
        
        # 90% train, 10% val
        split_idx = int(len(real_files) * 0.9)
        train_real = real_files[:split_idx]
        val_real = real_files[split_idx:]
        
        for f in tqdm(train_real, desc="Train REAL"):
            shutil.copy2(
                os.path.join(train_real_src, f),
                os.path.join(target_dir, 'train', '0_real', f)
            )
        
        for f in tqdm(val_real, desc="Val REAL"):
            shutil.copy2(
                os.path.join(train_real_src, f),
                os.path.join(target_dir, 'val', '0_real', f)
            )
    
    if os.path.exists(train_fake_src):
        print("Copying training FAKE images...")
        fake_files = os.listdir(train_fake_src)
        random.shuffle(fake_files)
        
        split_idx = int(len(fake_files) * 0.9)
        train_fake = fake_files[:split_idx]
        val_fake = fake_files[split_idx:]
        
        for f in tqdm(train_fake, desc="Train FAKE"):
            shutil.copy2(
                os.path.join(train_fake_src, f),
                os.path.join(target_dir, 'train', '1_fake', f)
            )
        
        for f in tqdm(val_fake, desc="Val FAKE"):
            shutil.copy2(
                os.path.join(train_fake_src, f),
                os.path.join(target_dir, 'val', '1_fake', f)
            )
    
    # Copy test data
    test_real_src = os.path.join(source_dir, 'test', 'REAL')
    test_fake_src = os.path.join(source_dir, 'test', 'FAKE')
    
    if os.path.exists(test_real_src):
        print("Copying test REAL images...")
        for f in tqdm(os.listdir(test_real_src), desc="Test REAL"):
            shutil.copy2(
                os.path.join(test_real_src, f),
                os.path.join(target_dir, 'test', '0_real', f)
            )
    
    if os.path.exists(test_fake_src):
        print("Copying test FAKE images...")
        for f in tqdm(os.listdir(test_fake_src), desc="Test FAKE"):
            shutil.copy2(
                os.path.join(test_fake_src, f),
                os.path.join(target_dir, 'test', '1_fake', f)
            )
    
    print("\n✅ Hoàn tất chuẩn bị dataset!")
    
    # Thống kê
    for split in ['train', 'val', 'test']:
        real_count = len(os.listdir(os.path.join(target_dir, split, '0_real')))
        fake_count = len(os.listdir(os.path.join(target_dir, split, '1_fake')))
        print(f"  {split}: {real_count} real, {fake_count} fake")


def download_from_kaggle():
    """Hướng dẫn tải từ Kaggle"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           HƯỚNG DẪN TẢI CIFAKE DATASET TỪ KAGGLE                ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. Truy cập: https://www.kaggle.com/datasets/birdy654/          ║
║     cifake-real-and-ai-generated-synthetic-images                ║
║                                                                   ║
║  2. Đăng nhập Kaggle (hoặc tạo tài khoản)                        ║
║                                                                   ║
║  3. Nhấn nút "Download" để tải file ZIP (~600MB)                 ║
║                                                                   ║
║  4. Giải nén vào thư mục: dataset/cifake_raw/                    ║
║                                                                   ║
║  5. Chạy lại script này để chuẩn bị data                         ║
║                                                                   ║
╠══════════════════════════════════════════════════════════════════╣
║  HOẶC sử dụng Kaggle CLI:                                        ║
║                                                                   ║
║  pip install kaggle                                               ║
║  kaggle datasets download -d birdy654/cifake-real-and-ai-        ║
║  generated-synthetic-images                                       ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
""")


def main():
    print("="*60)
    print("  CIFAKE Dataset Preparation for Dual-Stream CNN")
    print("="*60)
    
    # Đường dẫn
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(base_dir, 'dataset')
    cifake_raw = os.path.join(dataset_dir, 'cifake_raw')
    
    # Kiểm tra xem đã có raw data chưa
    if os.path.exists(cifake_raw) and os.path.exists(os.path.join(cifake_raw, 'train')):
        print(f"\n✓ Tìm thấy CIFAKE raw data tại: {cifake_raw}")
        prepare_cifake_structure(cifake_raw, dataset_dir)
    else:
        # Kiểm tra file zip
        zip_files = [f for f in os.listdir(dataset_dir) if f.endswith('.zip')] if os.path.exists(dataset_dir) else []
        
        if zip_files:
            print(f"\n✓ Tìm thấy file ZIP: {zip_files[0]}")
            zip_path = os.path.join(dataset_dir, zip_files[0])
            
            print("Giải nén dataset...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(cifake_raw)
            
            prepare_cifake_structure(cifake_raw, dataset_dir)
        else:
            print("\n❌ Không tìm thấy CIFAKE dataset!")
            download_from_kaggle()
            return
    
    print("\n" + "="*60)
    print("  SẴN SÀNG TRAINING!")
    print("  Chạy: python train_dual_stream.py --train_dir dataset/train --val_dir dataset/val")
    print("="*60)


if __name__ == "__main__":
    main()
