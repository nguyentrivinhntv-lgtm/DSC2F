"""
Dual-Stream CNN với ResNet Pretrained Backbone
- Sử dụng ResNet18 pretrained làm backbone
- Transfer learning từ ImageNet
- Hiệu suất cao hơn nhờ features đã học sẵn
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import numpy as np


def compute_fft_spectrum(img_tensor):
    """Tính FFT spectrum từ RGB image"""
    if img_tensor.dim() == 3:
        img_tensor = img_tensor.unsqueeze(0)
    
    gray = 0.299 * img_tensor[:, 0] + 0.587 * img_tensor[:, 1] + 0.114 * img_tensor[:, 2]
    
    fft = torch.fft.fft2(gray)
    fft_shift = torch.fft.fftshift(fft)
    magnitude = torch.abs(fft_shift)
    spectrum = torch.log1p(magnitude)
    
    spectrum = (spectrum - spectrum.min()) / (spectrum.max() - spectrum.min() + 1e-8)
    spectrum = spectrum.unsqueeze(1).repeat(1, 3, 1, 1)
    
    return spectrum.squeeze(0) if spectrum.size(0) == 1 else spectrum


class SpatialStreamResNet(nn.Module):
    """Spatial stream sử dụng ResNet18 pretrained"""
    def __init__(self, pretrained=True, freeze_early=True):
        super(SpatialStreamResNet, self).__init__()
        
        # Load ResNet18 pretrained
        resnet = models.resnet18(weights='IMAGENET1K_V1' if pretrained else None)
        
        # Lấy các layers (bỏ fc cuối)
        self.conv1 = resnet.conv1
        self.bn1 = resnet.bn1
        self.relu = resnet.relu
        self.maxpool = resnet.maxpool
        
        self.layer1 = resnet.layer1  # 64 channels
        self.layer2 = resnet.layer2  # 128 channels
        self.layer3 = resnet.layer3  # 256 channels
        self.layer4 = resnet.layer4  # 512 channels
        
        self.avgpool = resnet.avgpool
        
        # Freeze early layers để giữ features ImageNet
        if freeze_early and pretrained:
            for param in self.conv1.parameters():
                param.requires_grad = False
            for param in self.bn1.parameters():
                param.requires_grad = False
            for param in self.layer1.parameters():
                param.requires_grad = False
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        
        return x  # Output: 512


class FrequencyStreamResNet(nn.Module):
    """Frequency stream cho FFT input"""
    def __init__(self):
        super(FrequencyStreamResNet, self).__init__()
        
        # Lightweight CNN cho FFT features
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(3, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Block 2
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Block 3
            nn.Conv2d(128, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Block 4
            nn.Conv2d(256, 512, 3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1))
        )
    
    def forward(self, x):
        x = self.features(x)
        x = torch.flatten(x, 1)
        return x  # Output: 512


class DualStreamResNet(nn.Module):
    """
    Dual-Stream với ResNet Pretrained
    - Spatial: ResNet18 pretrained trên ImageNet
    - Frequency: Custom CNN cho FFT
    """
    def __init__(self, num_classes=1, dropout=0.5, pretrained=True):
        super(DualStreamResNet, self).__init__()
        
        # Two streams
        self.spatial_stream = SpatialStreamResNet(pretrained=pretrained)
        self.frequency_stream = FrequencyStreamResNet()
        
        # Fusion layer
        self.fusion = nn.Sequential(
            nn.Linear(512 + 512, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        
        # Classifier
        self.classifier = nn.Linear(256, num_classes)
        
        # Initialize fusion layers
        self._init_weights()
    
    def _init_weights(self):
        for m in self.fusion.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
        
        nn.init.xavier_uniform_(self.classifier.weight)
        nn.init.constant_(self.classifier.bias, 0)
    
    def forward(self, rgb, fft):
        spatial_feat = self.spatial_stream(rgb)
        freq_feat = self.frequency_stream(fft)
        
        combined = torch.cat([spatial_feat, freq_feat], dim=1)
        fused = self.fusion(combined)
        output = self.classifier(fused)
        
        return output
    
    def get_features(self, rgb, fft):
        """Lấy features để visualization"""
        spatial_feat = self.spatial_stream(rgb)
        freq_feat = self.frequency_stream(fft)
        combined = torch.cat([spatial_feat, freq_feat], dim=1)
        fused = self.fusion(combined)
        return {
            'spatial': spatial_feat,
            'frequency': freq_feat,
            'fused': fused
        }


if __name__ == "__main__":
    # Test model
    model = DualStreamResNet(pretrained=True)
    
    # Test input
    rgb = torch.randn(2, 3, 32, 32)
    fft = torch.randn(2, 3, 32, 32)
    
    # Forward pass
    output = model(rgb, fft)
    print(f"Input RGB shape: {rgb.shape}")
    print(f"Input FFT shape: {fft.shape}")
    print(f"Output shape: {output.shape}")
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")
