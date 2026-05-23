"""
Enhanced Dual-Stream CNN với các kỹ thuật tiên tiến
Thiết kế để phát hiện ảnh AI-generated từ các model mới như Gemini, DALL-E 3, Midjourney v6
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
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
    
    # Normalize to [0, 1]
    spectrum = (spectrum - spectrum.min()) / (spectrum.max() - spectrum.min() + 1e-8)
    
    return spectrum.unsqueeze(1) if spectrum.dim() == 3 else spectrum


class SRMFilterLayer(nn.Module):
    """
    Steganalysis Rich Model (SRM) Filters
    Phát hiện các artifact vi mô trong ảnh AI-generated
    """
    def __init__(self):
        super(SRMFilterLayer, self).__init__()
        
        # 30 SRM filters để phát hiện manipulation
        # Đây là các high-pass filters phát hiện noise patterns
        self.srm_filters = self._get_srm_filters()
        
        # Conv layer với SRM filters (không trainable)
        self.conv = nn.Conv2d(3, 30, kernel_size=5, padding=2, bias=False)
        self.conv.weight = nn.Parameter(self.srm_filters, requires_grad=False)
        
    def _get_srm_filters(self):
        """Tạo 30 SRM filters"""
        filters = []
        
        # Filter 1: First-order edge detector
        f1 = np.array([
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 1, -1, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0]
        ], dtype=np.float32)
        filters.append(f1)
        
        # Filter 2: Second-order edge detector
        f2 = np.array([
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 1, -2, 1, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0]
        ], dtype=np.float32)
        filters.append(f2)
        
        # Filter 3: Third-order edge detector
        f3 = np.array([
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, -1, 3, -3, 1],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0]
        ], dtype=np.float32)
        filters.append(f3)
        
        # SQUARE filters
        f4 = np.array([
            [0, 0, 0, 0, 0],
            [0, -1, 2, -1, 0],
            [0, 2, -4, 2, 0],
            [0, -1, 2, -1, 0],
            [0, 0, 0, 0, 0]
        ], dtype=np.float32) / 4.0
        filters.append(f4)
        
        # EDGE3x3 filter
        f5 = np.array([
            [0, 0, 0, 0, 0],
            [0, -1, 2, -1, 0],
            [0, 2, -4, 2, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0]
        ], dtype=np.float32) / 2.0
        filters.append(f5)
        
        # Generate rotations and more filters
        for i in range(25):
            angle = i * 15  # 15 degree increments
            rad = np.radians(angle)
            
            # Create directional filters
            kernel = np.zeros((5, 5), dtype=np.float32)
            center = 2
            for j in range(-2, 3):
                x = int(center + j * np.cos(rad))
                y = int(center + j * np.sin(rad))
                if 0 <= x < 5 and 0 <= y < 5:
                    if j == 0:
                        kernel[y, x] = -2
                    else:
                        kernel[y, x] = 1
            
            # Normalize
            if kernel.sum() != 0:
                kernel = kernel / max(abs(kernel.sum()), 1)
            filters.append(kernel)
        
        # Stack filters: (30, 5, 5)
        filters = np.stack(filters[:30], axis=0)
        
        # Expand for 3 input channels: (30, 3, 5, 5)
        filters_3ch = np.stack([filters, filters, filters], axis=1) / 3.0
        
        return torch.from_numpy(filters_3ch).float()
    
    def forward(self, x):
        return self.conv(x)


class ChannelAttention(nn.Module):
    """Channel Attention Module"""
    def __init__(self, channels, reduction=16):
        super(ChannelAttention, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False)
        )
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        b, c, _, _ = x.size()
        
        avg_out = self.fc(self.avg_pool(x).view(b, c))
        max_out = self.fc(self.max_pool(x).view(b, c))
        
        out = avg_out + max_out
        return self.sigmoid(out).view(b, c, 1, 1) * x


class SpatialAttention(nn.Module):
    """Spatial Attention Module"""
    def __init__(self, kernel_size=7):
        super(SpatialAttention, self).__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size//2, bias=False)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        concat = torch.cat([avg_out, max_out], dim=1)
        attention = self.sigmoid(self.conv(concat))
        return attention * x


class CBAM(nn.Module):
    """Convolutional Block Attention Module"""
    def __init__(self, channels, reduction=16):
        super(CBAM, self).__init__()
        self.channel_attention = ChannelAttention(channels, reduction)
        self.spatial_attention = SpatialAttention()
    
    def forward(self, x):
        x = self.channel_attention(x)
        x = self.spatial_attention(x)
        return x


class EnhancedSpatialStream(nn.Module):
    """
    Nhánh Spatial nâng cao với SRM filters và Attention
    """
    def __init__(self):
        super(EnhancedSpatialStream, self).__init__()
        
        # SRM filters để detect manipulation
        self.srm = SRMFilterLayer()
        
        # Initial convolution
        self.conv1_rgb = nn.Conv2d(3, 32, kernel_size=7, stride=2, padding=3, bias=False)
        self.conv1_srm = nn.Conv2d(30, 32, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        # Blocks with CBAM attention
        self.block1 = self._make_block(64, 128)
        self.cbam1 = CBAM(128)
        
        self.block2 = self._make_block(128, 256)
        self.cbam2 = CBAM(256)
        
        self.block3 = self._make_block(256, 512)
        self.cbam3 = CBAM(512)
        
        # Global pooling
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.out_features = 512
    
    def _make_block(self, in_ch, out_ch):
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        # SRM features
        srm_out = self.srm(x)
        srm_features = self.conv1_srm(srm_out)
        
        # RGB features
        rgb_features = self.conv1_rgb(x)
        
        # Concatenate
        x = torch.cat([rgb_features, srm_features], dim=1)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        # Blocks with attention
        x = self.block1(x)
        x = self.cbam1(x)
        
        x = self.block2(x)
        x = self.cbam2(x)
        
        x = self.block3(x)
        x = self.cbam3(x)
        
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        
        return x


class EnhancedFrequencyStream(nn.Module):
    """
    Nhánh Frequency nâng cao với multi-scale analysis
    """
    def __init__(self):
        super(EnhancedFrequencyStream, self).__init__()
        
        # Multi-scale FFT processing
        self.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        # Multi-scale branches
        self.branch1 = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        self.branch2 = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        self.branch3 = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=5, padding=2),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        # Fusion
        self.fusion = nn.Sequential(
            nn.Conv2d(192, 128, kernel_size=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True)
        )
        
        # Deeper blocks
        self.block1 = self._make_block(128, 256)
        self.cbam1 = CBAM(256)
        
        self.block2 = self._make_block(256, 512)
        self.cbam2 = CBAM(512)
        
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.out_features = 512
    
    def _make_block(self, in_ch, out_ch):
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        # Multi-scale processing
        b1 = self.branch1(x)
        b2 = self.branch2(x)
        b3 = self.branch3(x)
        
        x = torch.cat([b1, b2, b3], dim=1)
        x = self.fusion(x)
        
        x = self.block1(x)
        x = self.cbam1(x)
        
        x = self.block2(x)
        x = self.cbam2(x)
        
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        
        return x


class CrossModalAttention(nn.Module):
    """Cross-modal attention giữa spatial và frequency features"""
    def __init__(self, dim):
        super(CrossModalAttention, self).__init__()
        self.query = nn.Linear(dim, dim)
        self.key = nn.Linear(dim, dim)
        self.value = nn.Linear(dim, dim)
        self.scale = dim ** -0.5
        
    def forward(self, spatial, frequency):
        q = self.query(spatial)
        k = self.key(frequency)
        v = self.value(frequency)
        
        attn = torch.softmax(q @ k.transpose(-2, -1) * self.scale, dim=-1)
        out = attn @ v
        
        return spatial + out


class DualStreamCNNEnhanced(nn.Module):
    """
    Enhanced Dual-Stream CNN cho phát hiện ảnh AI-generated
    
    Cải tiến:
    1. SRM filters để phát hiện manipulation artifacts
    2. CBAM attention cho spatial và frequency streams
    3. Multi-scale frequency analysis
    4. Cross-modal attention để fusion features
    5. Deeper architecture với residual connections
    """
    def __init__(self, num_classes=1, dropout=0.5):
        super(DualStreamCNNEnhanced, self).__init__()
        
        # Two enhanced streams
        self.spatial_stream = EnhancedSpatialStream()
        self.frequency_stream = EnhancedFrequencyStream()
        
        # Cross-modal attention
        self.cross_attention = CrossModalAttention(512)
        
        # Feature dimension
        combined_features = 1024  # 512 + 512
        
        # Enhanced classifier
        self.classifier = nn.Sequential(
            nn.Linear(combined_features, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout * 0.5),
            
            nn.Linear(256, num_classes)
        )
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d) or isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                if m.weight.requires_grad:
                    nn.init.xavier_uniform_(m.weight)
                    if m.bias is not None:
                        nn.init.constant_(m.bias, 0)
    
    def forward(self, rgb_input, fft_input):
        # Extract features
        spatial_features = self.spatial_stream(rgb_input)
        frequency_features = self.frequency_stream(fft_input)
        
        # Cross-modal attention
        spatial_enhanced = self.cross_attention(
            spatial_features.unsqueeze(1), 
            frequency_features.unsqueeze(1)
        ).squeeze(1)
        
        # Concatenate features
        combined = torch.cat([spatial_enhanced, frequency_features], dim=1)
        
        # Classification
        output = self.classifier(combined)
        
        return output
    
    def get_features(self, rgb_input, fft_input):
        """Extract features without classification"""
        spatial_features = self.spatial_stream(rgb_input)
        frequency_features = self.frequency_stream(fft_input)
        return spatial_features, frequency_features


class FFTOnlyCNNEnhanced(nn.Module):
    """
    Sử dụng nhánh Frequency của kiến trúc Enhanced (bản mới) 
    nhưng giữ Classifier cũ để khớp trọng số.
    """
    def __init__(self, num_classes=1, dropout=0.5):
        super(FFTOnlyCNNEnhanced, self).__init__()
        # Backbone mới (Enchan)
        self.frequency_stream = EnhancedFrequencyStream() 
        
        # Classifier cấu trúc cũ để load được weight
        self.classifier = nn.Sequential(
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, 64), # Khớp với size 64 trong checkpoint
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.Linear(64, num_classes)
        )

    def forward(self, rgb_input, fft_input):
        features = self.frequency_stream(fft_input)
        output = self.classifier(features)
        return output

# End of file
