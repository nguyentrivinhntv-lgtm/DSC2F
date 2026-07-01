import torch
from networks.dual_stream_enhanced import DualStreamCNNEnhanced, FFTOnlyCNNEnhanced
from networks.resnet import resnet50

try:
    m1 = DualStreamCNNEnhanced(num_classes=1)
    print('DualStreamCNNEnhanced (Mô hình 2 nhánh): {:,}'.format(sum(p.numel() for p in m1.parameters())))
    
    m2 = FFTOnlyCNNEnhanced(num_classes=1)
    print('FFTOnlyCNNEnhanced (Mô hình nhánh FFT): {:,}'.format(sum(p.numel() for p in m2.parameters())))
    
    m3 = resnet50(num_classes=1)
    print('ResNet50 (Baseline mô hình gốc): {:,}'.format(sum(p.numel() for p in m3.parameters())))
except Exception as e:
    print('Error:', e)
