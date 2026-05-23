import torch
from networks.dual_stream_cnn import DualStreamCNN, SpatialStream, FrequencyStream
from networks.dual_stream_enhanced import DualStreamCNNEnhanced
from networks.resnet import resnet50

def count_parameters(model):
    return sum(p.numel() for p in model.parameters())

def get_model_size(model):
    param_size = 0
    for param in model.parameters():
        param_size += param.numel() * param.element_size()
    buffer_size = 0
    for buffer in model.buffers():
        buffer_size += buffer.numel() * buffer.element_size()
    size_all_mb = (param_size + buffer_size) / 1024**2
    return size_all_mb

models = {
    "ResNet50 (Mô hình chuẩn quốc tế)": resnet50(num_classes=1),
    "SpatialStream (Nhánh RGB gốc)": SpatialStream(),
    "FrequencyStream (Nhánh FFT gốc)": FrequencyStream(),
    "DualStreamCNN (Bản ghép cơ bản)": DualStreamCNN(),
    "DualStreamCNNEnhanced (Nâng cao)": DualStreamCNNEnhanced()
}

print(f"{'Model Name':<35} | {'Parameters':<15} | {'Size (MB)':<10}")
print("-" * 65)

for name, model in models.items():
    try:
        params = count_parameters(model)
        size = get_model_size(model)
        # Use English prefix for print to avoid encoding issues
        simple_name = name.split('(')[0].strip()
        print(f"{simple_name:<35} | {params:>15,} | {size:>10.2f} MB")
    except Exception as e:
        print(f"Error counting {name}: {e}")
