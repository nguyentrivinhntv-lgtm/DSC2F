"""
Script chuẩn bị CIFAKE dataset cho training
"""

import os
import shutil
import random
from tqdm import tqdm

def prepare_cifake():
    base_dir = 'dataset'
    cifake_dir = 'dataset/cifake-raw'
    
    print("="*60)
    print("  CHUẨN BỊ CIFAKE DATASET")
    print("="*60)
    
    # Tạo thư mục
    for split in ['train', 'val', 'test']:
        os.makedirs(os.path.join(base_dir, split, '0_real'), exist_ok=True)
        os.makedirs(os.path.join(base_dir, split, '1_fake'), exist_ok=True)
    
    # Xóa file cũ nếu có
    for split in ['train', 'val']:
        for cls in ['0_real', '1_fake']:
            folder = os.path.join(base_dir, split, cls)
            for f in os.listdir(folder):
                if f.endswith(('.jpg', '.png', '.jpeg')):
                    os.remove(os.path.join(folder, f))
    
    # Copy REAL từ train
    train_real = os.path.join(cifake_dir, 'train', 'REAL')
    if os.path.exists(train_real):
        files = [f for f in os.listdir(train_real) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        random.shuffle(files)
        
        split_idx = int(len(files) * 0.9)
        print(f"\n📁 REAL images: {len(files)} total")
        print(f"   Train: {split_idx}, Val: {len(files) - split_idx}")
        
        for i, f in enumerate(tqdm(files, desc="Copying REAL")):
            src = os.path.join(train_real, f)
            if i < split_idx:
                dst = os.path.join(base_dir, 'train', '0_real', f)
            else:
                dst = os.path.join(base_dir, 'val', '0_real', f)
            shutil.copy2(src, dst)
    
    # Copy FAKE từ train
    train_fake = os.path.join(cifake_dir, 'train', 'FAKE')
    if os.path.exists(train_fake):
        files = [f for f in os.listdir(train_fake) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        random.shuffle(files)
        
        split_idx = int(len(files) * 0.9)
        print(f"\n📁 FAKE images: {len(files)} total")
        print(f"   Train: {split_idx}, Val: {len(files) - split_idx}")
        
        for i, f in enumerate(tqdm(files, desc="Copying FAKE")):
            src = os.path.join(train_fake, f)
            if i < split_idx:
                dst = os.path.join(base_dir, 'train', '1_fake', f)
            else:
                dst = os.path.join(base_dir, 'val', '1_fake', f)
            shutil.copy2(src, dst)
    
    # Copy test data
    test_real = os.path.join(cifake_dir, 'test', 'REAL')
    test_fake = os.path.join(cifake_dir, 'test', 'FAKE')
    
    if os.path.exists(test_real):
        print(f"\n📁 Copying TEST REAL...")
        for f in tqdm(os.listdir(test_real)):
            if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                shutil.copy2(
                    os.path.join(test_real, f),
                    os.path.join(base_dir, 'test', '0_real', f)
                )
    
    if os.path.exists(test_fake):
        print(f"\n📁 Copying TEST FAKE...")
        for f in tqdm(os.listdir(test_fake)):
            if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                shutil.copy2(
                    os.path.join(test_fake, f),
                    os.path.join(base_dir, 'test', '1_fake', f)
                )
    
    # Thống kê
    print("\n" + "="*60)
    print("  THỐNG KÊ DATASET")
    print("="*60)
    
    total = 0
    for split in ['train', 'val', 'test']:
        real_count = len([f for f in os.listdir(os.path.join(base_dir, split, '0_real')) 
                         if f.endswith(('.jpg', '.png', '.jpeg'))])
        fake_count = len([f for f in os.listdir(os.path.join(base_dir, split, '1_fake'))
                         if f.endswith(('.jpg', '.png', '.jpeg'))])
        print(f"  {split:5s}: {real_count:6d} real + {fake_count:6d} fake = {real_count + fake_count:6d}")
        total += real_count + fake_count
    
    print(f"  {'TOTAL':5s}: {total:6d} images")
    print("="*60)
    print("\n✅ Dataset sẵn sàng cho training!")

if __name__ == "__main__":
    prepare_cifake()
