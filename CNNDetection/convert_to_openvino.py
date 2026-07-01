"""
Chuyển đổi PyTorch model sang OpenVINO để inference nhanh trên Intel CPU/iGPU
"""

import os
import sys
import torch
import numpy as np
from pathlib import Path

def convert_to_openvino():
    print("="*60)
    print("  CONVERT DUAL-STREAM CNN TO OPENVINO")
    print("="*60)
    
    # Kiểm tra OpenVINO
    try:
        import openvino as ov
        print(f"✓ OpenVINO version: {ov.__version__}")
    except ImportError:
        print("❌ OpenVINO chưa được cài đặt!")
        print("Chạy: pip install openvino")
        return
    
    # Load model
    from networks.dual_stream_cnn import DualStreamCNN
    
    model_path = 'weights/dual_stream/best_model.pth'
    if not os.path.exists(model_path):
        print(f"❌ Không tìm thấy model tại: {model_path}")
        print("Vui lòng train model trước!")
        return
    
    print(f"\n✓ Loading model từ: {model_path}")
    
    model = DualStreamCNN(num_classes=1)
    checkpoint = torch.load(model_path, map_location='cpu')
    model.load_state_dict(checkpoint['model'])
    model.eval()
    
    print(f"✓ Model loaded (AUC: {checkpoint.get('best_auc', 'N/A')})")
    
    # Tạo wrapper model cho export
    class DualStreamWrapper(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model
        
        def forward(self, rgb, fft):
            return torch.sigmoid(self.model(rgb, fft))
    
    wrapper = DualStreamWrapper(model)
    wrapper.eval()
    
    # Dummy inputs
    image_size = 32  # CIFAKE image size
    dummy_rgb = torch.randn(1, 3, image_size, image_size)
    dummy_fft = torch.randn(1, 1, image_size, image_size)
    
    # Export to ONNX
    onnx_path = 'weights/dual_stream/dual_stream_model.onnx'
    print(f"\n📦 Exporting to ONNX: {onnx_path}")
    
    torch.onnx.export(
        wrapper,
        (dummy_rgb, dummy_fft),
        onnx_path,
        input_names=['rgb_input', 'fft_input'],
        output_names=['probability'],
        dynamic_axes={
            'rgb_input': {0: 'batch_size'},
            'fft_input': {0: 'batch_size'},
            'probability': {0: 'batch_size'}
        },
        opset_version=14
    )
    print("✓ ONNX export successful!")
    
    # Convert to OpenVINO IR
    print(f"\n🔄 Converting to OpenVINO IR format...")
    
    core = ov.Core()
    ov_model = core.read_model(onnx_path)
    
    # Save OpenVINO model
    ir_path = 'weights/dual_stream/dual_stream_openvino'
    ov.save_model(ov_model, f'{ir_path}.xml')
    print(f"✓ OpenVINO model saved to: {ir_path}.xml")
    
    # Test inference
    print(f"\n🧪 Testing OpenVINO inference...")
    
    # Compile model
    compiled_model = core.compile_model(ov_model, 'CPU')
    
    # Run inference
    import time
    
    # Warmup
    for _ in range(5):
        _ = compiled_model([dummy_rgb.numpy(), dummy_fft.numpy()])
    
    # Benchmark
    n_runs = 100
    start = time.time()
    for _ in range(n_runs):
        result = compiled_model([dummy_rgb.numpy(), dummy_fft.numpy()])
    elapsed = time.time() - start
    
    print(f"✓ OpenVINO inference: {elapsed/n_runs*1000:.2f} ms/image")
    print(f"  Throughput: {n_runs/elapsed:.1f} images/sec")
    
    # Compare với PyTorch
    print(f"\n📊 Comparing with PyTorch...")
    
    start = time.time()
    with torch.no_grad():
        for _ in range(n_runs):
            _ = wrapper(dummy_rgb, dummy_fft)
    pytorch_elapsed = time.time() - start
    
    print(f"  PyTorch:   {pytorch_elapsed/n_runs*1000:.2f} ms/image ({n_runs/pytorch_elapsed:.1f} img/s)")
    print(f"  OpenVINO:  {elapsed/n_runs*1000:.2f} ms/image ({n_runs/elapsed:.1f} img/s)")
    print(f"  Speedup:   {pytorch_elapsed/elapsed:.2f}x faster with OpenVINO!")
    
    print("\n" + "="*60)
    print("✅ CONVERSION COMPLETE!")
    print("="*60)
    print(f"\nFiles created:")
    print(f"  - {onnx_path}")
    print(f"  - {ir_path}.xml")
    print(f"  - {ir_path}.bin")
    print(f"\nSử dụng trong GUI bằng cách chọn OpenVINO mode!")


if __name__ == "__main__":
    convert_to_openvino()
