"""
Dataset và DataLoader cho Dual-Stream CNN
Xử lý cả RGB và FFT spectrum
"""

import os
import torch
import numpy as np
from PIL import Image
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms


def compute_fft_from_pil(image, size=224, output_channels=1):
    """
    Tính FFT spectrum từ PIL Image
    
    Args:
        image: PIL Image (RGB)
        size: Kích thước output
        output_channels: Số channels output (1 hoặc 3)
    
    Returns:
        fft_tensor: Tensor (C, size, size) với C = output_channels
    """
    # Resize và chuyển về grayscale
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    gray = image.convert('L')
    gray_array = np.array(gray, dtype=np.float32) / 255.0
    
    # Compute FFT
    fft = np.fft.fft2(gray_array)
    fft_shift = np.fft.fftshift(fft)
    
    # Magnitude spectrum (log scale)
    magnitude = np.abs(fft_shift)
    magnitude = np.log1p(magnitude)
    
    # Normalize về [0, 1]
    magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-8)
    
    # Chuyển về tensor
    fft_tensor = torch.from_numpy(magnitude).float().unsqueeze(0)  # (1, H, W)
    
    # Expand to 3 channels if needed
    if output_channels == 3:
        fft_tensor = fft_tensor.repeat(3, 1, 1)  # (3, H, W)
    
    return fft_tensor


class DualStreamDataset(Dataset):
    """
    Dataset cho Dual-Stream CNN
    Trả về cả RGB image và FFT spectrum
    """
    def __init__(self, root_dir, transform=None, image_size=224, fft_channels=1):
        """
        Args:
            root_dir: Thư mục chứa data theo cấu trúc:
                root_dir/
                    0_real/
                        img1.jpg
                        img2.jpg
                        ...
                    1_fake/
                        img1.jpg
                        img2.jpg
                        ...
            transform: Transform cho RGB image
            image_size: Kích thước resize
            fft_channels: Số kênh FFT (1 hoặc 3)
        """
        self.root_dir = root_dir
        self.image_size = image_size
        self.fft_channels = fft_channels
        self.samples = []
        
        # Default transform cho RGB
        if transform is None:
            self.transform = transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
        else:
            self.transform = transform
        
        # Load samples
        self._load_samples()
    
    def _load_samples(self):
        """Load danh sách file và labels"""
        # Real images (label = 0) - hỗ trợ nhiều format thư mục
        for real_name in ['0_real', 'REAL', 'real']:
            real_dir = os.path.join(self.root_dir, real_name)
            if os.path.exists(real_dir):
                for fname in os.listdir(real_dir):
                    if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        self.samples.append((os.path.join(real_dir, fname), 0))
                break
        
        # Fake images (label = 1) - hỗ trợ nhiều format thư mục
        for fake_name in ['1_fake', 'FAKE', 'fake']:
            fake_dir = os.path.join(self.root_dir, fake_name)
            if os.path.exists(fake_dir):
                for fname in os.listdir(fake_dir):
                    if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        self.samples.append((os.path.join(fake_dir, fname), 1))
                break
        
        print(f"Loaded {len(self.samples)} samples from {self.root_dir}")
        real_count = sum(1 for _, label in self.samples if label == 0)
        fake_count = sum(1 for _, label in self.samples if label == 1)
        print(f"  - Real: {real_count}, Fake: {fake_count}")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        
        # Load image
        image = Image.open(img_path).convert('RGB')
        
        # Compute FFT trước khi transform RGB
        fft_spectrum = compute_fft_from_pil(image, self.image_size, output_channels=self.fft_channels)
        
        # Transform RGB
        rgb_tensor = self.transform(image)
        
        return rgb_tensor, fft_spectrum, torch.tensor(label, dtype=torch.float32)


class DualStreamDatasetFromFolder(Dataset):
    """
    Dataset đọc từ cấu trúc thư mục của torchvision.datasets.ImageFolder
    Compatible với dataset hiện có
    """
    def __init__(self, image_folder_dataset, image_size=224):
        """
        Args:
            image_folder_dataset: torchvision.datasets.ImageFolder instance
            image_size: Kích thước resize cho FFT
        """
        self.dataset = image_folder_dataset
        self.image_size = image_size
        
        # Transform cho FFT (cần original image)
        self.to_pil = transforms.ToPILImage()
    
    def __len__(self):
        return len(self.dataset)
    
    def __getitem__(self, idx):
        # Lấy đường dẫn ảnh gốc
        img_path, label = self.dataset.samples[idx]
        
        # Load original image cho FFT
        original_image = Image.open(img_path).convert('RGB')
        fft_spectrum = compute_fft_from_pil(original_image, self.image_size)
        
        # Lấy transformed RGB từ dataset gốc
        rgb_tensor, _ = self.dataset[idx]
        
        return rgb_tensor, fft_spectrum, torch.tensor(label, dtype=torch.float32)


def get_dual_stream_dataloader(data_dir, batch_size=32, num_workers=4, 
                                image_size=224, shuffle=True, is_train=True):
    """
    Tạo DataLoader cho Dual-Stream training
    
    Args:
        data_dir: Thư mục chứa data (có 0_real và 1_fake)
        batch_size: Batch size
        num_workers: Số worker cho data loading
        image_size: Kích thước ảnh
        shuffle: Có shuffle không
        is_train: Training mode (có augmentation)
    
    Returns:
        dataloader: DataLoader instance
    """
    if is_train:
        transform = transforms.Compose([
            transforms.Resize((image_size + 32, image_size + 32)),
            transforms.RandomCrop(image_size),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
    else:
        transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
    
    dataset = DualStreamDataset(data_dir, transform=transform, image_size=image_size)
    
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return dataloader


# Test
if __name__ == "__main__":
    print("Testing Dual-Stream Dataset...")
    
    # Test với dummy data
    test_dir = "examples/realfakedir"
    if os.path.exists(test_dir):
        dataset = DualStreamDataset(test_dir, image_size=224)
        print(f"\nDataset size: {len(dataset)}")
        
        if len(dataset) > 0:
            rgb, fft, label = dataset[0]
            print(f"RGB shape: {rgb.shape}")
            print(f"FFT shape: {fft.shape}")
            print(f"Label: {label}")
    else:
        print(f"Test directory '{test_dir}' not found")
    
    print("\n✅ Dataset test completed!")
