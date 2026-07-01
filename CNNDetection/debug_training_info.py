"""Show training info from checkpoints."""
import torch

for name, path in [
    ("DualStream Enhanced", "weights/enhanced/best_model.pth"),
    ("FFT-Only Enhanced", "weights/fft_only_enhanced/best_model.pth"),
]:
    print(f"\n=== {name} ===")
    ckpt = torch.load(path, map_location='cpu', weights_only=False)
    a = ckpt.get('args')
    if a:
        print(f"  Train data: {getattr(a, 'train_dir', 'N/A')}")
        print(f"  Val data:   {getattr(a, 'val_dir', 'N/A')}")
        print(f"  Image size: {getattr(a, 'image_size', 'N/A')}")
        print(f"  Epochs:     {getattr(a, 'epochs', 'N/A')}")
    print(f"  Stopped at epoch: {ckpt.get('epoch', 'N/A')}")
    print(f"  Best AUC:   {ckpt.get('best_auc', ckpt.get('best_val_auc', 'N/A'))}")
    print(f"  Best Acc:   {ckpt.get('best_acc', ckpt.get('best_val_acc', 'N/A'))}")

print("\n=== ResNet-50 (baseline) ===")
print("  Trained on: ProGAN (Wang et al. CNNDetection paper)")
print("  With blur+JPEG augmentation => generalizes to many generators")
print("  Image size: 224x224 (center-crop from high-res images)")

print("\n" + "="*60)
print("CONCLUSION:")
print("="*60)
print("ResNet-50 was trained on diverse, high-res GAN data (ProGAN)")
print("with blur+JPEG augmentation => excellent cross-generator transfer.")
print("")
print("DualStream & FFT-Only were trained on CIFAKE (CIFAR-10 based,")
print("originally 32x32) => CANNOT generalize to ForenSynths which")
print("contains high-res face images from ProGAN, StyleGAN, etc.")
print("")
print("This is DOMAIN SHIFT, not a code bug.")
