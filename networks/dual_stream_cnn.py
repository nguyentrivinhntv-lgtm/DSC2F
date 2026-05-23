"""
Dual-Stream CNN Network for Deepfake Detection
Kết hợp Spatial Stream (RGB) và Frequency Stream (FFT)

Kiến trúc hình chữ Y:
    RGB Image ──► Spatial CNN ──┐
                                ├──► Fusion ──► Classifier ──► Output
    FFT Spectrum ──► Freq CNN ──┘
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class SpatialStream(nn.Module):
    """
    Nhánh Spatial: Xử lý ảnh RGB
    Học các đặc trưng về màu sắc, texture, edges
    """
    def __init__(self, pretrained=True):
        super(SpatialStream, self).__init__()
        
        # CNN layers cho spatial features
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        # Block 1
        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(128)
        
        # Block 2
        self.conv3 = nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1)
        self.bn3 = nn.BatchNorm2d(256)
        
        # Block 3
        self.conv4 = nn.Conv2d(256, 512, kernel_size=3, stride=2, padding=1)
        self.bn4 = nn.BatchNorm2d(512)
        
        # Global Average Pooling
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        
        # Output feature dimension
        self.out_features = 512
        
    def forward(self, x):
        # Initial convolution
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        # Block 1
        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        
        # Block 2
        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        
        # Block 3
        x = self.conv4(x)
        x = self.bn4(x)
        x = self.relu(x)
        
        # Global pooling
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        
        return x


class FrequencyStream(nn.Module):
    """
    Nhánh Frequency: Xử lý phổ FFT
    Học các đặc trưng tần số - rất hiệu quả với ảnh AI-generated
    """
    def __init__(self):
        super(FrequencyStream, self).__init__()
        
        # FFT spectrum có 1 channel (magnitude)
        self.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        # Block 1
        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(128)
        
        # Block 2
        self.conv3 = nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1)
        self.bn3 = nn.BatchNorm2d(256)
        
        # Block 3
        self.conv4 = nn.Conv2d(256, 512, kernel_size=3, stride=2, padding=1)
        self.bn4 = nn.BatchNorm2d(512)
        
        # Global Average Pooling
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        
        # Output feature dimension
        self.out_features = 512
        
    def forward(self, x):
        # Initial convolution
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        # Block 1
        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        
        # Block 2
        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        
        # Block 3
        x = self.conv4(x)
        x = self.bn4(x)
        x = self.relu(x)
        
        # Global pooling
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        
        return x


class DualStreamCNN(nn.Module):
    """
    Mạng Dual-Stream CNN kết hợp Spatial và Frequency
    
    Kiến trúc:
    - Spatial Stream: Học đặc trưng từ ảnh RGB
    - Frequency Stream: Học đặc trưng từ phổ FFT
    - Fusion: Concatenate + FC layers
    """
    def __init__(self, num_classes=1, dropout=0.5):
        super(DualStreamCNN, self).__init__()
        
        # Hai nhánh CNN
        self.spatial_stream = SpatialStream()
        self.frequency_stream = FrequencyStream()
        
        # Fusion layers
        combined_features = self.spatial_stream.out_features + self.frequency_stream.out_features
        
        self.fusion = nn.Sequential(
            nn.Linear(combined_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes)
        )
        
        # Khởi tạo weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, rgb_input, fft_input):
        """
        Forward pass với cả RGB và FFT input
        
        Args:
            rgb_input: Tensor (B, 3, H, W) - ảnh RGB
            fft_input: Tensor (B, 1, H, W) - phổ FFT
        
        Returns:
            output: Tensor (B, 1) - xác suất fake
        """
        # Spatial features từ RGB
        spatial_features = self.spatial_stream(rgb_input)
        
        # Frequency features từ FFT
        freq_features = self.frequency_stream(fft_input)
        
        # Concatenate (Fusion)
        combined = torch.cat([spatial_features, freq_features], dim=1)
        
        # Classification
        output = self.fusion(combined)
        
        return output
    
    def get_features(self, rgb_input, fft_input):
        """Lấy features từ cả hai nhánh (để visualize)"""
        spatial_features = self.spatial_stream(rgb_input)
        freq_features = self.frequency_stream(fft_input)
        return spatial_features, freq_features


class DualStreamResNet(nn.Module):
    """
    Phiên bản mạnh hơn sử dụng ResNet backbone
    """
    def __init__(self, num_classes=1, dropout=0.5):
        super(DualStreamResNet, self).__init__()
        
        from networks.resnet import resnet50
        
        # Spatial Stream - ResNet50
        self.spatial_stream = resnet50(pretrained=True)
        self.spatial_stream.fc = nn.Identity()  # Remove classification layer
        spatial_out = 2048
        
        # Frequency Stream - Custom CNN (lighter)
        self.frequency_stream = FrequencyStream()
        freq_out = 512
        
        # Fusion
        combined_features = spatial_out + freq_out
        
        self.fusion = nn.Sequential(
            nn.Linear(combined_features, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(1024, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, rgb_input, fft_input):
        spatial_features = self.spatial_stream(rgb_input)
        freq_features = self.frequency_stream(fft_input)
        combined = torch.cat([spatial_features, freq_features], dim=1)
        output = self.fusion(combined)
        return output


def compute_fft_spectrum(image_tensor):
    """
    Tính phổ FFT từ ảnh RGB
    
    Args:
        image_tensor: Tensor (B, 3, H, W) hoặc (3, H, W)
    
    Returns:
        fft_spectrum: Tensor (B, 1, H, W) hoặc (1, H, W)
    """
    # Chuyển về grayscale
    if image_tensor.dim() == 4:
        # Batch mode
        gray = 0.299 * image_tensor[:, 0] + 0.587 * image_tensor[:, 1] + 0.114 * image_tensor[:, 2]
    else:
        # Single image
        gray = 0.299 * image_tensor[0] + 0.587 * image_tensor[1] + 0.114 * image_tensor[2]
    
    # FFT
    fft = torch.fft.fft2(gray)
    fft_shift = torch.fft.fftshift(fft)
    
    # Magnitude spectrum (log scale)
    magnitude = torch.abs(fft_shift)
    magnitude = torch.log1p(magnitude)  # log(1 + x) để tránh log(0)
    
    # Normalize về [0, 1]
    if magnitude.dim() == 3:
        for i in range(magnitude.shape[0]):
            magnitude[i] = (magnitude[i] - magnitude[i].min()) / (magnitude[i].max() - magnitude[i].min() + 1e-8)
    else:
        magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-8)
    
    # Thêm channel dimension
    if magnitude.dim() == 2:
        magnitude = magnitude.unsqueeze(0)  # (1, H, W)
    else:
        magnitude = magnitude.unsqueeze(1)  # (B, 1, H, W)
    
    return magnitude


# Test module
if __name__ == "__main__":
    print("Testing Dual-Stream CNN...")
    
    # Tạo dummy input
    batch_size = 4
    rgb_input = torch.randn(batch_size, 3, 224, 224)
    fft_input = compute_fft_spectrum(rgb_input)
    
    print(f"RGB input shape: {rgb_input.shape}")
    print(f"FFT input shape: {fft_input.shape}")
    
    # Test DualStreamCNN
    model = DualStreamCNN(num_classes=1)
    output = model(rgb_input, fft_input)
    print(f"DualStreamCNN output shape: {output.shape}")
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params:,}")
    
    print("\n✅ Dual-Stream CNN hoạt động tốt!")
