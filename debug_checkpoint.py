"""Quick script to inspect checkpoint weight keys."""
import torch

for name, path in [
    ("Enhanced", "weights/enhanced/best_model.pth"),
    ("FFT-Only", "weights/fft_only_enhanced/best_model.pth"),
]:
    print(f"\n{'='*60}")
    print(f"  {name}: {path}")
    print(f"{'='*60}")
    ckpt = torch.load(path, map_location='cpu', weights_only=False)
    keys = list(ckpt['model'].keys())
    print(f"Total keys: {len(keys)}")
    print("First 20 keys:")
    for k in keys[:20]:
        print(f"  {k}: {ckpt['model'][k].shape}")
    print("...")
    print(f"Has srm? {any('srm' in k for k in keys)}")
    print(f"Has spatial_stream? {any('spatial_stream' in k for k in keys)}")
    print(f"Has frequency_stream? {any('frequency_stream' in k for k in keys)}")
    print(f"Has cross_attention? {any('cross_attention' in k for k in keys)}")
    print(f"Has fusion? {any('fusion' in k for k in keys)}")
    print(f"Has classifier? {any('classifier' in k for k in keys)}")
    
    # Check args
    args_ = ckpt.get('args', None)
    if args_ is not None:
        img_size = getattr(args_, 'image_size', 'N/A')
        print(f"image_size from args: {img_size}")
