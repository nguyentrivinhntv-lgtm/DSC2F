"""
Advanced Dual-Stream CNN với ResNet Pretrained + các kỹ thuật tối ưu
- ResNet18/34/50 pretrained
- Squeeze-Excitation (SE) blocks
- Stochastic Depth (Drop Path)
- Better fusion với attention
- Frequency stream mạnh hơn
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import numpy as np
from functools import partial


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


class DropPath(nn.Module):
    """Stochastic Depth / Drop Path regularization"""
    def __init__(self, drop_prob=0.):
        super(DropPath, self).__init__()
        self.drop_prob = drop_prob

    def forward(self, x):
        if self.drop_prob == 0. or not self.training:
            return x
        
        keep_prob = 1 - self.drop_prob
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
        random_tensor.floor_()
        output = x.div(keep_prob) * random_tensor
        return output


class SEBlock(nn.Module):
    """Squeeze-and-Excitation block"""
    def __init__(self, channels, reduction=16):
        super(SEBlock, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False),
            nn.Sigmoid()
        )

    def forward(self, x):
        b, c, _, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1, 1)
        return x * y.expand_as(x)


class CBAM(nn.Module):
    """Convolutional Block Attention Module"""
    def __init__(self, channels, reduction=16, kernel_size=7):
        super(CBAM, self).__init__()
        
        # Channel attention
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.channel_fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False)
        )
        
        # Spatial attention
        self.spatial_conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size//2, bias=False)
    
    def forward(self, x):
        # Channel attention
        b, c, _, _ = x.size()
        avg_out = self.channel_fc(self.avg_pool(x).view(b, c))
        max_out = self.channel_fc(self.max_pool(x).view(b, c))
        channel_att = torch.sigmoid(avg_out + max_out).view(b, c, 1, 1)
        x = x * channel_att
        
        # Spatial attention
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        spatial_att = torch.sigmoid(self.spatial_conv(torch.cat([avg_out, max_out], dim=1)))
        x = x * spatial_att
        
        return x


class SpatialStreamResNetAdvanced(nn.Module):
    """Spatial stream với ResNet pretrained + SE blocks + Drop Path"""
    def __init__(self, pretrained=True, resnet_depth=34, use_se=True, drop_path_rate=0.1):
        super(SpatialStreamResNetAdvanced, self).__init__()
        
        # Load ResNet pretrained
        if resnet_depth == 18:
            resnet = models.resnet18(weights='IMAGENET1K_V1' if pretrained else None)
            self.out_channels = 512
        elif resnet_depth == 34:
            resnet = models.resnet34(weights='IMAGENET1K_V1' if pretrained else None)
            self.out_channels = 512
        elif resnet_depth == 50:
            resnet = models.resnet50(weights='IMAGENET1K_V2' if pretrained else None)
            self.out_channels = 2048
        else:
            raise ValueError(f"Unsupported ResNet depth: {resnet_depth}")
        
        # Lấy các layers
        self.conv1 = resnet.conv1
        self.bn1 = resnet.bn1
        self.relu = resnet.relu
        self.maxpool = resnet.maxpool
        
        self.layer1 = resnet.layer1
        self.layer2 = resnet.layer2
        self.layer3 = resnet.layer3
        self.layer4 = resnet.layer4
        
        self.avgpool = resnet.avgpool
        
        # Add SE blocks
        self.use_se = use_se
        if use_se:
            if resnet_depth in [18, 34]:
                self.se1 = SEBlock(64)
                self.se2 = SEBlock(128)
                self.se3 = SEBlock(256)
                self.se4 = SEBlock(512)
            else:  # ResNet50
                self.se1 = SEBlock(256)
                self.se2 = SEBlock(512)
                self.se3 = SEBlock(1024)
                self.se4 = SEBlock(2048)
        
        # Drop path
        num_layers = 4
        dpr = [drop_path_rate * i / (num_layers - 1) for i in range(num_layers)]
        self.drop_paths = nn.ModuleList([DropPath(dpr[i]) for i in range(num_layers)])
        
        # Freeze early layers
        if pretrained:
            for param in self.conv1.parameters():
                param.requires_grad = False
            for param in self.bn1.parameters():
                param.requires_grad = False
            for param in self.layer1.parameters():
                param.requires_grad = False
            for param in self.layer2.parameters():
                param.requires_grad = False
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        x = self.layer1(x)
        if self.use_se:
            x = self.se1(x)
        x = self.drop_paths[0](x)
        
        x = self.layer2(x)
        if self.use_se:
            x = self.se2(x)
        x = self.drop_paths[1](x)
        
        x = self.layer3(x)
        if self.use_se:
            x = self.se3(x)
        x = self.drop_paths[2](x)
        
        x = self.layer4(x)
        if self.use_se:
            x = self.se4(x)
        x = self.drop_paths[3](x)
        
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        
        return x


class FrequencyStreamAdvanced(nn.Module):
    """Frequency stream mạnh hơn với ResNet-style blocks"""
    def __init__(self, out_channels=512):
        super(FrequencyStreamAdvanced, self).__init__()
        
        # Initial conv
        self.stem = nn.Sequential(
            nn.Conv2d(3, 64, 7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1)
        )
        
        # ResNet-style blocks
        self.layer1 = self._make_layer(64, 128, 2, stride=1)
        self.layer2 = self._make_layer(128, 256, 2, stride=2)
        self.layer3 = self._make_layer(256, 512, 2, stride=2)
        
        # Attention
        self.cbam = CBAM(512)
        
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.out_channels = out_channels
        
        # Projection
        self.proj = nn.Linear(512, out_channels) if out_channels != 512 else nn.Identity()
    
    def _make_layer(self, in_channels, out_channels, num_blocks, stride=1):
        layers = []
        
        # First block với stride
        layers.append(nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, stride=stride, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
        ))
        
        # Residual connection
        if stride != 1 or in_channels != out_channels:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
        
        # Additional blocks
        for _ in range(1, num_blocks):
            layers.append(nn.Sequential(
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
            ))
        
        return nn.Sequential(*layers)
    
    def forward(self, x):
        x = self.stem(x)
        x = self.layer1(x)
        x = F.relu(x)
        x = self.layer2(x)
        x = F.relu(x)
        x = self.layer3(x)
        x = F.relu(x)
        x = self.cbam(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.proj(x)
        return x


class CrossModalAttention(nn.Module):
    """Cross-modal attention để fuse spatial và frequency features"""
    def __init__(self, dim, num_heads=8):
        super(CrossModalAttention, self).__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5
        
        self.q_proj = nn.Linear(dim, dim)
        self.k_proj = nn.Linear(dim, dim)
        self.v_proj = nn.Linear(dim, dim)
        self.out_proj = nn.Linear(dim, dim)
        
        self.norm1 = nn.LayerNorm(dim)
        self.norm2 = nn.LayerNorm(dim)
        
    def forward(self, x, context):
        """x attends to context"""
        B, C = x.shape
        
        q = self.q_proj(self.norm1(x)).view(B, self.num_heads, self.head_dim)
        k = self.k_proj(self.norm2(context)).view(B, self.num_heads, self.head_dim)
        v = self.v_proj(context).view(B, self.num_heads, self.head_dim)
        
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        
        out = (attn @ v).reshape(B, C)
        out = self.out_proj(out)
        
        return x + out


class FusionModule(nn.Module):
    """Advanced fusion với cross-modal attention"""
    def __init__(self, spatial_dim, freq_dim, hidden_dim=512, dropout=0.4):
        super(FusionModule, self).__init__()
        
        # Project to same dimension
        self.spatial_proj = nn.Linear(spatial_dim, hidden_dim)
        self.freq_proj = nn.Linear(freq_dim, hidden_dim)
        
        # Cross-modal attention
        self.spatial_attend_freq = CrossModalAttention(hidden_dim, num_heads=8)
        self.freq_attend_spatial = CrossModalAttention(hidden_dim, num_heads=8)
        
        # Final fusion
        self.fusion = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        
        self.out_dim = hidden_dim // 2
    
    def forward(self, spatial_feat, freq_feat):
        # Project
        spatial = self.spatial_proj(spatial_feat)
        freq = self.freq_proj(freq_feat)
        
        # Cross attention
        spatial_enhanced = self.spatial_attend_freq(spatial, freq)
        freq_enhanced = self.freq_attend_spatial(freq, spatial)
        
        # Concatenate and fuse
        combined = torch.cat([spatial_enhanced, freq_enhanced], dim=1)
        fused = self.fusion(combined)
        
        return fused


class DualStreamResNetAdvanced(nn.Module):
    """
    Advanced Dual-Stream với:
    - ResNet18/34/50 pretrained
    - SE blocks
    - Drop Path
    - Cross-modal attention fusion
    """
    def __init__(self, num_classes=1, dropout=0.4, pretrained=True, 
                 resnet_depth=34, use_se=True, drop_path_rate=0.1):
        super(DualStreamResNetAdvanced, self).__init__()
        
        # Two streams
        self.spatial_stream = SpatialStreamResNetAdvanced(
            pretrained=pretrained,
            resnet_depth=resnet_depth,
            use_se=use_se,
            drop_path_rate=drop_path_rate
        )
        
        self.frequency_stream = FrequencyStreamAdvanced(out_channels=512)
        
        # Advanced fusion
        self.fusion = FusionModule(
            spatial_dim=self.spatial_stream.out_channels,
            freq_dim=512,
            hidden_dim=512,
            dropout=dropout
        )
        
        # Classifier
        self.classifier = nn.Linear(self.fusion.out_dim, num_classes)
        
        # Initialize
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                if m.weight.shape[0] == 1:  # Classifier
                    nn.init.xavier_uniform_(m.weight)
                    if m.bias is not None:
                        nn.init.constant_(m.bias, 0)
    
    def forward(self, rgb, fft):
        spatial_feat = self.spatial_stream(rgb)
        freq_feat = self.frequency_stream(fft)
        
        fused = self.fusion(spatial_feat, freq_feat)
        output = self.classifier(fused)
        
        return output
    
    def get_features(self, rgb, fft):
        """Lấy features để visualization"""
        spatial_feat = self.spatial_stream(rgb)
        freq_feat = self.frequency_stream(fft)
        fused = self.fusion(spatial_feat, freq_feat)
        return {
            'spatial': spatial_feat,
            'frequency': freq_feat,
            'fused': fused
        }


if __name__ == "__main__":
    # Test model
    print("Testing DualStreamResNetAdvanced...")
    
    for resnet_depth in [18, 34, 50]:
        print(f"\n=== ResNet{resnet_depth} ===")
        model = DualStreamResNetAdvanced(
            pretrained=True,
            resnet_depth=resnet_depth,
            use_se=True,
            drop_path_rate=0.1
        )
        
        # Test input
        rgb = torch.randn(2, 3, 128, 128)
        fft = torch.randn(2, 3, 128, 128)
        
        # Forward pass
        output = model(rgb, fft)
        print(f"Input shape: {rgb.shape}")
        print(f"Output shape: {output.shape}")
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total parameters: {total_params:,}")
        print(f"Trainable parameters: {trainable_params:,}")
