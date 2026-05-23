# -*- coding: utf-8 -*-
"""
Evaluate Dual-Stream CNN models on CIFAR-10 (Real) and CIFAKE (Fake)
===================================================================

This script evaluates binary classification performance (Real vs Fake).
- REAL images are loaded directly from torchvision CIFAR-10 test set.
- FAKE images are loaded from a local directory (e.g. CIFAKE dataset).

Features:
- Automatic CIFAR-10 download via torchvision.
- Per-class breakdown for CIFAR-10 real images.
- Standard binary classification metrics (Accuracy, AUC, AP, F1).
"""

import os
import sys
import time
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, datasets
from PIL import Image
from sklearn.metrics import (
    accuracy_score, roc_auc_score, average_precision_score,
    confusion_matrix, classification_report
)

# ─── Paths ──────────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_20K_DIR = os.path.join(BASE_DIR, "dataset", "artifact-20k")
CIFAKE_DIR = os.path.join(BASE_DIR, "dataset", "cifake-raw", "test")
CIFAR10_DOWNLOAD_DIR = os.path.join(BASE_DIR, "dataset", "cifar10_torchvision")

MODELS = {
    "DualStreamCNNEnhanced": {
        "weight": os.path.join(BASE_DIR, "weights", "enhanced", "best_model.pth"),
        "module": "networks.dual_stream_enhanced",
        "class":  "DualStreamCNNEnhanced",
        "fft_channels": 1,
    },
    "DualStreamResNet": {
        "weight": os.path.join(BASE_DIR, "weights", "dual_stream_resnet", "best_model.pth"),
        "module": "networks.dual_stream_resnet",
        "class":  "DualStreamResNet",
        "fft_channels": 3,
        "image_size": 224,  # Model được train với ảnh 224x224
    },
    "FFTOnlyCNNEnhanced": {
        "weight": os.path.join(BASE_DIR, "weights", "fft_only_enhanced", "best_model.pth"),
        "module": "networks.dual_stream_enhanced",
        "class":  "FFTOnlyCNNEnhanced",
        "fft_channels": 1,
    },
    "ResNet50": {
        "weight": os.path.join(BASE_DIR, "weights", "blur_jpg_prob0.1.pth"),
        "module": "networks.resnet",
        "class":  "resnet50",
        "fft_channels": 0,
    },
}

CIFAR10_CLASSES = [
    "airplane", "automobile", "bird", "cat", "deer",
    "dog", "frog", "horse", "ship", "truck"
]

# ─── FFT helper ─────────────────────────────────────────────────────────────

def compute_fft_from_pil(image, size=224, output_channels=1):
    """
    Tính FFT spectrum từ PIL Image. Khớp hoàn toàn với data/dual_stream_dataset.py
    """
    # Resize và chuyển về grayscale
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    gray = image.convert('L')
    gray_array = np.array(gray, dtype=np.float32) / 255.0
    
    # Compute FFT
    fft = np.fft.fft2(gray_array)
    fft_shift = np.fft.fftshift(fft)
    
    # Magnitude spectrum (log1p scale)
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


# ─── Dataset ────────────────────────────────────────────────────────────────

class CIFAKETestDataset(Dataset):
    """
    Kết hợp CIFAR-10 (Real) từ torchvision và ảnh FAKE từ thư mục cục bộ.
    label: 0 = REAL, 1 = FAKE
    """

    def __init__(self, root_dir=CIFAKE_DIR, image_size=224, fft_channels=1, use_torchvision=True, max_samples=0):
        self.image_size = image_size
        self.fft_channels = fft_channels
        self.use_torchvision = use_torchvision
        self.max_samples = max_samples
        
        self.rgb_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        self.samples = []

        # 1. Load REAL images
        if use_torchvision:
            print(f"Loading CIFAR-10 REAL images from torchvision...")
            self.cifar10_real = datasets.CIFAR10(root=CIFAR10_DOWNLOAD_DIR, train=False, download=True)
            real_count = 0
            for i in range(len(self.cifar10_real)):
                if self.max_samples > 0 and real_count >= self.max_samples:
                    break
                _, cid = self.cifar10_real[i]
                self.samples.append({
                    'type': 'torchvision',
                    'index': i,
                    'label': 0.0,
                    'class_id': cid
                })
                real_count += 1
        else:
            real_dir = os.path.join(root_dir, "REAL")
            if os.path.isdir(real_dir):
                real_count = 0
                for fname in sorted(os.listdir(real_dir)):
                    if self.max_samples > 0 and real_count >= self.max_samples:
                        break
                    if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        self.samples.append({
                            'type': 'file',
                            'path': os.path.join(real_dir, fname),
                            'label': 0.0,
                            'class_id': -1
                        })
                        real_count += 1

        # 2. Load FAKE images
        fake_dir = os.path.join(root_dir, "FAKE")
        if os.path.isdir(fake_dir):
            fake_count = 0
            for fname in sorted(os.listdir(fake_dir)):
                if self.max_samples > 0 and fake_count >= self.max_samples:
                    break
                if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    self.samples.append({
                        'type': 'file',
                        'path': os.path.join(fake_dir, fname),
                        'label': 1.0,
                        'class_id': -1
                    })
                    fake_count += 1
        else:
            print(f"[WARN] Fake directory not found: {fake_dir}")

        real_n = sum(1 for s in self.samples if s['label'] == 0)
        fake_n = sum(1 for s in self.samples if s['label'] == 1)
        print(f"Dataset summary:")
        print(f"  REAL: {real_n:,} (source: {'torchvision' if use_torchvision else 'local folder'})")
        print(f"  FAKE: {fake_n:,}")
        print(f"  Total: {len(self.samples):,}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        
        if item['type'] == 'torchvision':
            image, _ = self.cifar10_real[item['index']]
        else:
            image = Image.open(item['path']).convert('RGB')

        rgb = self.rgb_transform(image)
        fft = compute_fft_from_pil(image, self.image_size, output_channels=self.fft_channels)

        return rgb, fft, torch.tensor(item['label'], dtype=torch.float32), torch.tensor(item['class_id'], dtype=torch.long)


# ─── Model loader ────────────────────────────────────────────────────────────

def load_model(name, cfg, device):
    """Import class, buid model, load weights, set eval mode.
    
    Returns:
        (model, detected_image_size) hoặc (None, None) nếu không tìm thấy weights.
    """
    import importlib
    mod   = importlib.import_module(cfg["module"])
    cls   = getattr(mod, cfg["class"])
    model = cls(num_classes=1)

    weight_path = cfg["weight"]
    if not os.path.isfile(weight_path):
        print(f"  [SKIP] Weight file not found: {weight_path}")
        return None, None

    checkpoint = torch.load(weight_path, map_location="cpu", weights_only=False)
    state = checkpoint.get("model", checkpoint)
    
    # Load weights
    strict_load = False if "FFTOnly" in name else True
    model.load_state_dict(state, strict=strict_load)

    # Tự động phát hiện image_size từ checkpoint args
    detected_size = None
    if isinstance(checkpoint, dict) and 'args' in checkpoint:
        ckpt_args = checkpoint['args']
        if hasattr(ckpt_args, 'image_size'):
            detected_size = ckpt_args.image_size
            print(f"  [INFO] Phát hiện image_size={detected_size} từ checkpoint")

    # Then wrap for FFT compatibility if needed
    if cfg.get("fft_channels") == 0:
        class ModelWrapper(nn.Module):
            def __init__(self, base_model):
                super().__init__()
                self.base_model = base_model
            def forward(self, rgb, fft=None):
                return self.base_model(rgb)
        model = ModelWrapper(model)

    model.to(device)
    model.eval()
    print(f"  [OK] Loaded weights: {weight_path}")
    return model, detected_size


# ─── Evaluation ──────────────────────────────────────────────────────────────

@torch.no_grad()
def evaluate(model, loader, device, model_name=""):
    all_labels  = []
    all_probs   = []
    all_preds   = []
    
    class_stats = {i: {"total": 0, "correct_real": 0} for i in range(10)}

    t0 = time.time()
    print(f"  [INFO] Đang bắt đầu xử lý các batch... (Tổng số batch: {len(loader)})")
    for batch_idx, (rgb, fft, labels, class_ids) in enumerate(loader):
        rgb    = rgb.to(device)
        fft    = fft.to(device)
        labels = labels.to(device)

        logits = model(rgb, fft)
        logits = logits.squeeze(1) if logits.dim() == 2 else logits
        probs  = torch.sigmoid(logits).cpu().numpy()
        preds  = (probs >= 0.5).astype(int)

        all_probs.extend(probs.tolist())
        all_preds.extend(preds.tolist())
        all_labels.extend(labels.cpu().numpy().astype(int).tolist())
        
        for cid, label, pred in zip(class_ids.numpy(), labels.cpu().numpy(), preds):
            if label == 0 and cid != -1:
                class_stats[cid]["total"] += 1
                if pred == 0:
                    class_stats[cid]["correct_real"] += 1

        if (batch_idx + 1) % 5 == 0:
            elapsed = time.time() - t0
            print(f"    Batch {batch_idx+1}/{len(loader)}  ({elapsed:.1f}s)")

    elapsed = time.time() - t0

    all_labels = np.array(all_labels)
    all_probs  = np.array(all_probs)
    all_preds  = np.array(all_preds)

    acc  = accuracy_score(all_labels, all_preds)
    auc  = roc_auc_score(all_labels, all_probs)
    ap   = average_precision_score(all_labels, all_probs)
    cm   = confusion_matrix(all_labels, all_preds)
    
    unique_labels = np.unique(all_labels)
    target_names = ["REAL", "FAKE"] if len(unique_labels) == 2 else (["REAL"] if unique_labels[0] == 0 else ["FAKE"])
    cr = classification_report(all_labels, all_preds, target_names=target_names, digits=4)

    if 1 in all_labels:
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0,0,0,0)
        precision_fake = tp / (tp + fp + 1e-8)
        recall_fake    = tp / (tp + fn + 1e-8)
        f1_fake        = 2 * precision_fake * recall_fake / (precision_fake + recall_fake + 1e-8)
    else:
        precision_fake = recall_fake = f1_fake = 0.0

    return {
        "model_name":     model_name,
        "accuracy":       acc,
        "auc":            auc,
        "avg_precision":  ap,
        "f1_fake":        f1_fake,
        "precision_fake": precision_fake,
        "recall_fake":    recall_fake,
        "confusion_matrix": cm,
        "classification_report": cr,
        "elapsed_s":      elapsed,
        "n_samples":      len(all_labels),
        "class_stats":    class_stats,
    }


# ─── Print helpers ────────────────────────────────────────────────────────────

def print_result(r):
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  Model : {r['model_name']}")
    print(f"{sep}")
    print(f"  Samples     : {r['n_samples']:,}")
    print(f"  Time        : {r['elapsed_s']:.1f}s")
    print(f"  Accuracy    : {r['accuracy']*100:.2f}%")
    print(f"  ROC-AUC     : {r['auc']:.4f}")
    print(f"  Avg Prec AP : {r['avg_precision']:.4f}")
    
    if r['f1_fake'] > 0:
        print(f"  F1  (FAKE)  : {r['f1_fake']:.4f}")
        print(f"  Prec(FAKE)  : {r['precision_fake']:.4f}")
        print(f"  Rec (FAKE)  : {r['recall_fake']:.4f}")
    
    print(f"\n  Confusion Matrix (rows=true, cols=pred):")
    cm = r['confusion_matrix']
    if cm.size == 4:
        print(f"          REAL   FAKE")
        print(f"  REAL  {cm[0,0]:6d} {cm[0,1]:6d}")
        print(f"  FAKE  {cm[1,0]:6d} {cm[1,1]:6d}")

    has_class_data = any(v["total"] > 0 for v in r["class_stats"].values())
    if has_class_data:
        print(f"\n  Per-class breakdown (CIFAR-10 Real Images):")
        print(f"    {'Class':<14} {'Total':>6} {'Correct':>10} {'Accuracy%':>10}")
        print(f"    {'-'*44}")
        for i, name in enumerate(CIFAR10_CLASSES):
            s = r["class_stats"][i]
            if s["total"] > 0:
                pct = s["correct_real"] / s["total"] * 100
                print(f"    {name:<14} {s['total']:>6} {s['correct_real']:>10} {pct:>9.1f}%")

    print(f"\n  Classification Report:")
    for line in r['classification_report'].split('\n'):
        print(f"    {line}")


def print_summary(results):
    print("\n" + "=" * 70)
    print("  SUMMARY TABLE (CIFAR-10 / CIFAKE)")
    print("=" * 70)
    header = f"  {'Model':<30} {'Acc%':>7} {'AUC':>7} {'AP':>7} {'F1':>7}"
    print(header)
    print("-" * 70)
    for r in results:
        print(f"  {r['model_name']:<30} "
              f"{r['accuracy']*100:>7.2f} "
              f"{r['auc']:>7.4f} "
              f"{r['avg_precision']:>7.4f} "
              f"{r['f1_fake']:>7.4f}")
    print("=" * 70)


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate Dual-Stream CNN models on Artifact-20k (Real vs Fake) or CIFAKE")
    parser.add_argument("--data_dir",   default=ARTIFACT_20K_DIR,
                        help="Directory containing test/FAKE and test/REAL (default: artifact-20k)")
    parser.add_argument("--image_size", type=int, default=224,
                        help="Resize images (default: 224 for Dual-Stream Enhanced)")
    parser.add_argument("--batch_size", type=int, default=64,
                        help="Batch size (default: 64)")
    parser.add_argument("--workers",    type=int, default=0,
                        help="DataLoader workers (default: 0)")
    parser.add_argument("--device",     default="auto",
                        choices=["auto", "cpu", "cuda"])
    parser.add_argument("--models",     nargs="+",
                        choices=list(MODELS.keys()) + ["all"],
                        default=["all"])
    parser.add_argument("--local_real", action="store_true", default=True,
                        help="Use local folder for REAL images instead of torchvision CIFAR-10")
    parser.add_argument("--max_samples", type=int, default=0,
                        help="Max samples per class (0 = all)")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    print(f"\nDevice   : {device}")
    if device.type == "cuda":
        print(f"GPU      : {torch.cuda.get_device_name(0)}")

    selected = list(MODELS.keys()) if "all" in args.models else args.models
    results = []

    for name in selected:
        cfg = MODELS[name]
        fft_ch = cfg.get("fft_channels", 1)
        print(f"\n{'='*60}")
        print(f"Loading model: {name}  (FFT channels: {fft_ch})")
        model, detected_size = load_model(name, cfg, device)
        if model is None:
            continue

        # Xác định image_size: ưu tiên config > checkpoint > args mặc định
        model_image_size = cfg.get("image_size") or detected_size or args.image_size
        if model_image_size != args.image_size:
            print(f"  [INFO] Sử dụng image_size={model_image_size} (thay vì mặc định {args.image_size})")

        model_dataset = CIFAKETestDataset(root_dir=args.data_dir,
                                          image_size=model_image_size,
                                          fft_channels=fft_ch,
                                          use_torchvision=not args.local_real,
                                          max_samples=args.max_samples)
        
        model_loader = DataLoader(model_dataset,
                                  batch_size=args.batch_size,
                                  shuffle=False,
                                  num_workers=args.workers,
                                  pin_memory=(device.type == "cuda"))

        print(f"Evaluating {name} on {len(model_dataset):,} samples...")
        r = evaluate(model, model_loader, device, model_name=name)
        print_result(r)
        results.append(r)

        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    if not results:
        print("\nNo models evaluated.")
        sys.exit(1)

    if len(results) > 1:
        print_summary(results)

    print("\nDone!")


if __name__ == "__main__":
    main()
