"""
Download CIFAKE Dataset và Training Dual-Stream CNN
"""

import os
import sys
import shutil
import random
from tqdm import tqdm

def download_cifake():
    """Tải CIFAKE dataset từ Kaggle"""
    print("="*60)
    print("  DOWNLOADING CIFAKE DATASET")
    print("="*60)
    
    try:
        import opendatasets as od
        
        # URL Kaggle dataset
        dataset_url = 'https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images'
        
        print("\n📥 Đang tải CIFAKE dataset từ Kaggle...")
        print("(Bạn cần nhập Kaggle username và API key)")
        print("Lấy API key tại: https://www.kaggle.com/settings → API → Create New Token\n")
        
        # Download vào thư mục dataset
        od.download(dataset_url, data_dir='dataset')
        
        print("\n✅ Tải dataset thành công!")
        return True
        
    except Exception as e:
        print(f"\n❌ Lỗi tải dataset: {e}")
        print("\nHướng dẫn tải thủ công:")
        print("1. Truy cập: https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images")
        print("2. Download file ZIP")
        print("3. Giải nén vào thư mục: dataset/cifake-real-and-ai-generated-synthetic-images/")
        return False


def prepare_dataset():
    """Chuẩn bị dataset theo format cần thiết"""
    print("\n" + "="*60)
    print("  PREPARING DATASET")
    print("="*60)
    
    base_dir = 'dataset'
    
    # Tìm thư mục CIFAKE
    cifake_dir = None
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and 'cifake' in item.lower():
            cifake_dir = item_path
            break
    
    if not cifake_dir:
        print("❌ Không tìm thấy thư mục CIFAKE trong dataset/")
        return False
    
    print(f"✓ Tìm thấy CIFAKE tại: {cifake_dir}")
    
    # Kiểm tra cấu trúc
    train_src = os.path.join(cifake_dir, 'train')
    test_src = os.path.join(cifake_dir, 'test')
    
    if not os.path.exists(train_src):
        print(f"❌ Không tìm thấy thư mục train trong {cifake_dir}")
        return False
    
    # Tạo thư mục đích
    for split in ['train', 'val', 'test']:
        os.makedirs(os.path.join(base_dir, split, '0_real'), exist_ok=True)
        os.makedirs(os.path.join(base_dir, split, '1_fake'), exist_ok=True)
    
    # Copy REAL images từ train
    real_src = os.path.join(train_src, 'REAL')
    if os.path.exists(real_src):
        real_files = [f for f in os.listdir(real_src) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.shuffle(real_files)
        
        # 90% train, 10% val
        split_idx = int(len(real_files) * 0.9)
        
        print(f"\n📁 Copying REAL images ({len(real_files)} files)...")
        for i, f in enumerate(tqdm(real_files)):
            src_path = os.path.join(real_src, f)
            if i < split_idx:
                dst_path = os.path.join(base_dir, 'train', '0_real', f)
            else:
                dst_path = os.path.join(base_dir, 'val', '0_real', f)
            shutil.copy2(src_path, dst_path)
    
    # Copy FAKE images từ train
    fake_src = os.path.join(train_src, 'FAKE')
    if os.path.exists(fake_src):
        fake_files = [f for f in os.listdir(fake_src) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.shuffle(fake_files)
        
        split_idx = int(len(fake_files) * 0.9)
        
        print(f"\n📁 Copying FAKE images ({len(fake_files)} files)...")
        for i, f in enumerate(tqdm(fake_files)):
            src_path = os.path.join(fake_src, f)
            if i < split_idx:
                dst_path = os.path.join(base_dir, 'train', '1_fake', f)
            else:
                dst_path = os.path.join(base_dir, 'val', '1_fake', f)
            shutil.copy2(src_path, dst_path)
    
    # Copy test data
    if os.path.exists(test_src):
        test_real = os.path.join(test_src, 'REAL')
        test_fake = os.path.join(test_src, 'FAKE')
        
        if os.path.exists(test_real):
            print(f"\n📁 Copying TEST REAL images...")
            for f in tqdm(os.listdir(test_real)):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    shutil.copy2(
                        os.path.join(test_real, f),
                        os.path.join(base_dir, 'test', '0_real', f)
                    )
        
        if os.path.exists(test_fake):
            print(f"\n📁 Copying TEST FAKE images...")
            for f in tqdm(os.listdir(test_fake)):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    shutil.copy2(
                        os.path.join(test_fake, f),
                        os.path.join(base_dir, 'test', '1_fake', f)
                    )
    
    # Thống kê
    print("\n" + "="*60)
    print("  DATASET STATISTICS")
    print("="*60)
    
    for split in ['train', 'val', 'test']:
        real_count = len(os.listdir(os.path.join(base_dir, split, '0_real')))
        fake_count = len(os.listdir(os.path.join(base_dir, split, '1_fake')))
        total = real_count + fake_count
        print(f"  {split:5s}: {real_count:6d} real + {fake_count:6d} fake = {total:6d} total")
    
    print("="*60)
    return True


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     CIFAKE DATASET DOWNLOAD & DUAL-STREAM CNN TRAINING       ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Kiểm tra xem dataset đã có chưa
    train_path = 'dataset/train/0_real'
    if os.path.exists(train_path) and len(os.listdir(train_path)) > 100:
        print("✓ Dataset đã được chuẩn bị sẵn!")
    else:
        # Kiểm tra thư mục CIFAKE raw
        cifake_exists = False
        if os.path.exists('dataset'):
            for item in os.listdir('dataset'):
                if 'cifake' in item.lower():
                    cifake_exists = True
                    break
        
        if not cifake_exists:
            # Download dataset
            download_cifake()
        
        # Prepare dataset
        if not prepare_dataset():
            print("\n❌ Không thể chuẩn bị dataset. Vui lòng tải thủ công.")
            return
    
    # Hỏi có muốn train không
    print("\n" + "="*60)
    print("  BẮT ĐẦU TRAINING?")
    print("="*60)
    
    answer = input("\nBạn có muốn bắt đầu training Dual-Stream CNN? (y/n): ").strip().lower()
    
    if answer == 'y':
        print("\n🚀 Bắt đầu training...")
        os.system('python train_dual_stream.py --train_dir dataset/train --val_dir dataset/val --epochs 30 --batch_size 64 --image_size 32')
    else:
        print("\nĐể training sau, chạy lệnh:")
        print("  python train_dual_stream.py --train_dir dataset/train --val_dir dataset/val --epochs 30 --batch_size 64 --image_size 32")


if __name__ == "__main__":
    main()
