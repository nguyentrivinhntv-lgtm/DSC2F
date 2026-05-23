"""
=============================================================================
ForenSynths-style Evaluation Pipeline
=============================================================================
Quy trình kiểm tra theo đúng paper CNNDetection:

  - Ảnh được center-crop xuống 224×224 pixel (KHÔNG resize)
  - Không áp dụng augmentation trong lúc test
  - Normalize theo ImageNet mean/std
  - Metric chính: Average Precision (AP)
  - Ngoài ra: accuracy (uncalibrated), oracle accuracy, two-shot calibration

Hỗ trợ 2 mô hình:
  1. ResNet-50   (blur_jpg_prob0.5.pth  hoặc  blur_jpg_prob0.1.pth)
  2. DualStreamResNetAdvanced  (weights/dual_stream_resnet/best_model.pth)

Dataset format được hỗ trợ:
  - ForenSynths style: dataroot/<generator_name>/{0_real/, 1_fake/}
  - Flat style:        dataroot/{0_real/, 1_fake/}
=============================================================================
"""

import os
import sys
import csv
import json
import time
import argparse
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image
import io
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import average_precision_score, accuracy_score

# Ensure unbuffered output on Windows
import functools
_orig_print = print
print = functools.partial(_orig_print, flush=True)

# ---------------------------------------------------------------------------
# 1.  Transform — center-crop 224 (paper-exact, NO resize)
# ---------------------------------------------------------------------------
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

def get_test_transform():
    """Paper-exact test transform: CenterCrop(224) only, no resize."""
    return transforms.Compose([
        transforms.Resize((224, 224)), # Ép buộc chuyển tất cả thành 224x224 chuẩn xác (tránh bị lệch aspect ratio)
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

def get_test_transform_with_resize(size=224):
    """
    Alternative: resize first then center-crop.
    Dùng khi ảnh nhỏ hơn 224×224.
    """
    return transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

# ---------------------------------------------------------------------------
# 2.  Dataset
# ---------------------------------------------------------------------------
VALID_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

def collect_images(root, label):
    """Thu thập (path, label) dưới root."""
    items = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if os.path.splitext(fn.lower())[1] in VALID_EXTS:
                items.append((os.path.join(dirpath, fn), label))
    return items


class ArrowBinaryDataset(Dataset):
    """
    Dataset using an .arrow file loaded via HuggingFace datasets library.
    It expects 'image_path' and 'image' (bytes) columns.
    Label is inferred from 'image_path' containing '1_fake' or '0_real'.
    """
    def __init__(self, arrow_paths, transform=None, resize_fallback=True,
                 return_fft=False, fft_size=224):
        from datasets import Dataset as HFDataset, concatenate_datasets
        self.transform = transform
        self.resize_fallback = resize_fallback
        self.return_fft = return_fft
        self.fft_size = fft_size
        
        if isinstance(arrow_paths, str):
            arrow_paths = [arrow_paths]
            
        print(f"Loading Arrow dataset from {len(arrow_paths)} files...")
        datasets = [HFDataset.from_file(p) for p in arrow_paths if os.path.exists(p)]
        if not datasets:
            raise ValueError(f"No valid arrow files found!")
            
        self.ds = concatenate_datasets(datasets) if len(datasets) > 1 else datasets[0]
        
        # Calculate stats for info
        self.reals = sum(1 for p in self.ds['image_path'] if '0_real' in p)
        self.fakes = sum(1 for p in self.ds['image_path'] if '1_fake' in p)
        print(f"  Dataset loaded: {len(self.ds)} images ({self.reals} real, {self.fakes} fake)")
        
    def __len__(self):
        return len(self.ds)

    def __getitem__(self, idx):
        item = self.ds[idx]
        
        path = item['image_path']
        img_bytes = item['image']
        
        # Infer true label
        label = 1 if '1_fake' in path else 0
        
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        if self.resize_fallback and (img.width < 224 or img.height < 224):
            img = transforms.Resize((224, 224))(img)

        # Tính FFT từ ảnh PIL gốc (TRƯỚC khi transform) — giống hệt lúc training
        if self.return_fft:
            from data.dual_stream_dataset import compute_fft_from_pil
            fft = compute_fft_from_pil(img, size=self.fft_size)

        if self.transform:
            img = self.transform(img)

        if self.return_fft:
            return img, fft, label
        return img, label

class BinaryImageDataset(Dataset):
    """
    Hỗ trợ hai cấu trúc thư mục:
    
    A) ForenSynths (multi-generator):
       root/
         progan/
           0_real/  ...
           1_fake/  ...
         stylegan/
           0_real/  ...
           1_fake/  ...
         ...
    
    B) Flat (single set):
       root/
         0_real/  ...
         1_fake/  ...
    """

    def __init__(self, root, transform=None, resize_fallback=True,
                 return_fft=False, fft_size=224):
        self.transform = transform
        self.resize_fallback = resize_fallback
        self.return_fft = return_fft
        self.fft_size = fft_size
        self.samples = []

        real_dir = os.path.join(root, '0_real')
        fake_dir = os.path.join(root, '1_fake')

        if os.path.isdir(real_dir) and os.path.isdir(fake_dir):
            # Flat layout
            self.samples  = collect_images(real_dir, 0)
            self.samples += collect_images(fake_dir, 1)
        else:
            # ForenSynths multi-class layout
            for sub in sorted(os.listdir(root)):
                sub_path = os.path.join(root, sub)
                if not os.path.isdir(sub_path):
                    continue
                r = os.path.join(sub_path, '0_real')
                f = os.path.join(sub_path, '1_fake')
                if os.path.isdir(r):
                    self.samples += collect_images(r, 0)
                if os.path.isdir(f):
                    self.samples += collect_images(f, 1)

        if len(self.samples) == 0:
            raise ValueError(f"Không tìm thấy ảnh nào trong: {root}")

        print(f"  Dataset found: {len(self.samples)} images "
              f"({sum(1 for _,l in self.samples if l==0)} real, "
              f"{sum(1 for _,l in self.samples if l==1)} fake)")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert('RGB')

        # Nếu ảnh nhỏ hơn 224, fallback sang resize
        if self.resize_fallback and (img.width < 224 or img.height < 224):
            img = transforms.Resize((224, 224))(img)

        # Tính FFT từ ảnh PIL gốc (TRƯỚC khi transform) — giống hệt lúc training
        if self.return_fft:
            from data.dual_stream_dataset import compute_fft_from_pil
            fft = compute_fft_from_pil(img, size=self.fft_size)

        if self.transform:
            img = self.transform(img)

        if self.return_fft:
            return img, fft, label
        return img, label


def create_per_generator_datasets(root, transform, return_fft=False, fft_size=224):
    """
    Trả về dict {generator_name: BinaryImageDataset}
    Dùng cho ForenSynths multi-generator evaluation.
    """
    real_dir = os.path.join(root, '0_real')
    fake_dir = os.path.join(root, '1_fake')

    if os.path.isdir(real_dir) and os.path.isdir(fake_dir):
        # Flat: treat as single "dataset" named "overall"
        return {'overall': BinaryImageDataset(root, transform,
                                              return_fft=return_fft, fft_size=fft_size)}

    datasets = {}
    for sub in sorted(os.listdir(root)):
        sub_path = os.path.join(root, sub)
        if not os.path.isdir(sub_path):
            continue
        r = os.path.join(sub_path, '0_real')
        f = os.path.join(sub_path, '1_fake')
        if os.path.isdir(r) or os.path.isdir(f):
            try:
                datasets[sub] = BinaryImageDataset(sub_path, transform,
                                                   return_fft=return_fft, fft_size=fft_size)
            except ValueError:
                pass  # empty subset
    return datasets


# ---------------------------------------------------------------------------
# 3.  Metrics
# ---------------------------------------------------------------------------

def compute_metrics(y_true, y_prob, threshold=0.5):
    """
    Trả về dict với các metric theo paper:
      - ap           : Average Precision (metric chính, threshold-free)
      - acc          : Accuracy tại threshold=0.5 (uncalibrated)
      - acc_real     : Accuracy trên ảnh real
      - acc_fake     : Accuracy trên ảnh fake
      - oracle_acc   : Oracle accuracy — tìm threshold tốt nhất trên chính tập test
      - oracle_thresh: Threshold tốt nhất
      - two_shot_acc : Two-shot calibration accuracy
      - two_shot_thresh: Threshold sau two-shot calibration
    """
    y_true = np.array(y_true)
    y_prob = np.array(y_prob)
    y_pred = (y_prob >= threshold).astype(int)

    # AP
    ap = average_precision_score(y_true, y_prob)

    # Uncalibrated accuracy
    acc      = accuracy_score(y_true, y_pred)
    real_idx = y_true == 0
    fake_idx = y_true == 1
    acc_real = accuracy_score(y_true[real_idx], y_pred[real_idx]) if real_idx.sum() > 0 else float('nan')
    acc_fake = accuracy_score(y_true[fake_idx], y_pred[fake_idx]) if fake_idx.sum() > 0 else float('nan')

    # Oracle accuracy (best threshold on this test set)
    thresholds = np.linspace(0, 1, 201)
    oracle_acc, oracle_thresh = max(
        ((accuracy_score(y_true, (y_prob >= t).astype(int)), t) for t in thresholds),
        key=lambda x: x[0]
    )

    # Two-shot calibration:
    # Lấy 1 ảnh real + 1 ảnh fake làm "support", threshold = mean của 2 prob
    np.random.seed(42)
    real_probs = y_prob[real_idx]
    fake_probs = y_prob[fake_idx]
    if len(real_probs) > 0 and len(fake_probs) > 0:
        two_shot_thresh = (real_probs.mean() + fake_probs.mean()) / 2.0
    else:
        two_shot_thresh = 0.5
    two_shot_pred = (y_prob >= two_shot_thresh).astype(int)
    two_shot_acc  = accuracy_score(y_true, two_shot_pred)

    return {
        'ap':            ap,
        'acc':           acc,
        'acc_real':      acc_real,
        'acc_fake':      acc_fake,
        'oracle_acc':    oracle_acc,
        'oracle_thresh': oracle_thresh,
        'two_shot_acc':  two_shot_acc,
        'two_shot_thresh': two_shot_thresh,
        'n_total':       len(y_true),
        'n_real':        int(real_idx.sum()),
        'n_fake':        int(fake_idx.sum()),
    }


# ---------------------------------------------------------------------------
# 4.  Model loaders
# ---------------------------------------------------------------------------

def load_resnet50(model_path, device):
    """Load ResNet-50 từ checkpoint paper (single-output, sigmoid)."""
    from networks.resnet import resnet50
    model = resnet50(num_classes=1)
    state_dict = torch.load(model_path, map_location='cpu', weights_only=False)
    if 'model' in state_dict:
        model.load_state_dict(state_dict['model'])
    else:
        model.load_state_dict(state_dict)
    model = model.to(device)
    model.eval()
    print(f"  [OK] Loaded ResNet-50 from: {model_path}")
    return model, 'resnet50'


def load_dual_stream(model_path, device, resnet_depth=34):
    """Load DualStreamResNetAdvanced."""
    from networks.dual_stream_resnet import (
        DualStreamResNet, compute_fft_spectrum
    )
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    args_ = checkpoint.get('args', None)
    if args_ is not None and hasattr(args_, 'resnet_depth'):
        resnet_depth = args_.resnet_depth

    model = DualStreamResNet(
        num_classes=1,
        pretrained=False
    )
    if 'model' in checkpoint:
        model.load_state_dict(checkpoint['model'])
    else:
        model.load_state_dict(checkpoint)
    model = model.to(device)
    model.eval()
    print(f"  [OK] Loaded DualStream (ResNet{resnet_depth}) from: {model_path}")
    return model, 'dual_stream', compute_fft_spectrum

def load_fft_only_enhanced(model_path, device):
    """Load FFTOnlyCNNEnhanced."""
    from networks.dual_stream_enhanced import FFTOnlyCNNEnhanced, compute_fft_spectrum
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    
    # Đọc fft_size từ checkpoint args (nếu có)
    args_ = checkpoint.get('args', None)
    fft_size = getattr(args_, 'image_size', 224) if args_ else 224
    
    model = FFTOnlyCNNEnhanced(num_classes=1)
    if 'model' in checkpoint:
        model.load_state_dict(checkpoint['model'])
    elif 'state_dict' in checkpoint:
        model.load_state_dict(checkpoint['state_dict'])
    else:
        model.load_state_dict(checkpoint)
        
    model = model.to(device)
    model.eval()
    print(f"  [OK] Loaded FFT-Only Enhanced from: {model_path}")
    print(f"  [OK] FFT size from checkpoint: {fft_size}")
    return model, 'dual_stream_enhanced', compute_fft_spectrum, fft_size

def load_dual_stream_enhanced(model_path, device):
    """Load EnhancedDualStreamCNN."""
    from networks.enhanced_dual_stream import EnhancedDualStreamCNN
    from networks.dual_stream_enhanced import compute_fft_spectrum
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    
    # Đọc fft_size từ checkpoint args (nếu có)
    args_ = checkpoint.get('args', None)
    fft_size = getattr(args_, 'image_size', 224) if args_ else 224
    
    model = EnhancedDualStreamCNN(num_classes=1)
    if 'model' in checkpoint:
        model.load_state_dict(checkpoint['model'])
    elif 'state_dict' in checkpoint:
        model.load_state_dict(checkpoint['state_dict'])
    else:
        model.load_state_dict(checkpoint)
        
    model = model.to(device)
    model.eval()
    print(f"  [OK] Loaded DualStream Enhanced from: {model_path}")
    print(f"  [OK] FFT size from checkpoint: {fft_size}")
    return model, 'dual_stream_enhanced', compute_fft_spectrum, fft_size


# ---------------------------------------------------------------------------
# 5.  Inference
# ---------------------------------------------------------------------------

@torch.no_grad()
def run_inference_resnet(model, loader, device):
    """Forward pass cho ResNet-50 (single-stream)."""
    y_true_all, y_prob_all = [], []
    total = len(loader)
    for i, (imgs, labels) in enumerate(loader):
        if i % 10 == 0:
            print(f"    Batch {i+1}/{total}...", end='\r')
        imgs = imgs.to(device)
        logits = model(imgs)
        probs  = torch.sigmoid(logits).squeeze(-1).cpu().numpy()
        y_prob_all.extend(probs.flatten().tolist())
        y_true_all.extend(labels.numpy().tolist())
    print()  # newline after \r
    return np.array(y_true_all), np.array(y_prob_all)


@torch.no_grad()
def run_inference_dual(model, loader, device, compute_fft_fn):
    """Forward pass cho DualStream (dual-input: rgb + fft).
    
    Dataset phải trả về 3-tuple (img, fft, label) — FFT đã được tính
    từ ảnh PIL gốc trong dataset, giống hệt lúc training.
    """
    y_true_all, y_prob_all = [], []
    total = len(loader)
    
    for i, batch in enumerate(loader):
        if i % 10 == 0:
            print(f"    Batch {i+1}/{total}...", end='\r')
        
        # Dataset trả về 3-tuple: (rgb, fft, label)
        imgs, fft, labels = batch
        imgs = imgs.to(device)
        fft = fft.to(device)
        
        # Đảm bảo kích thước FFT khớp với RGB (nếu cần)
        if fft.shape[-2:] != imgs.shape[-2:]:
            fft = F.interpolate(fft, size=imgs.shape[-2:], mode='bilinear', align_corners=False)
            
        logits = model(imgs, fft)
        probs  = torch.sigmoid(logits).squeeze(-1).cpu().numpy()
        y_prob_all.extend(probs.flatten().tolist())
        y_true_all.extend(labels.numpy().tolist())
    print()  # newline after \r
    return np.array(y_true_all), np.array(y_prob_all)


# ---------------------------------------------------------------------------
# 6.  Evaluation runner
# ---------------------------------------------------------------------------

def evaluate_model(model_info, dataroot, device, batch_size=32, num_workers=0, max_images=0, arrow_paths=None):
    """
    Chạy evaluation trên toàn bộ dataset (hoặc từng generator nếu ForenSynths).
    
    model_info: dict với keys:
      - 'type': 'resnet50' hoặc 'dual_stream_enhanced'
      - 'model': nn.Module
      - 'compute_fft_fn' (optional): hàm tính FFT
      - 'fft_size' (optional): kích thước FFT cho dual-stream (mặc định 224)
    """
    transform = get_test_transform()
    
    # Determine if FFT is needed and the FFT size
    need_fft = model_info['type'] != 'resnet50'
    fft_size = model_info.get('fft_size', 224)
    if need_fft:
        print(f"  [INFO] Dual-stream mode: FFT computed from original PIL, fft_size={fft_size}")

    print("  Checking sample image size...")
    if arrow_paths is not None and len(arrow_paths) > 0 and any(os.path.exists(p) for p in arrow_paths):
        datasets_map = {'arrow_overall': ArrowBinaryDataset(
            arrow_paths, transform, return_fft=need_fft, fft_size=fft_size)}
    else:
        datasets_map = create_per_generator_datasets(
            dataroot, transform, return_fft=need_fft, fft_size=fft_size)

    if max_images > 0:
        for gen_name, dataset in datasets_map.items():
            if hasattr(dataset, 'samples'):
                import random
                all_idx = list(range(len(dataset.samples)))
                random.seed(42)
                random.shuffle(all_idx)
                selected_idx = all_idx[:max_images]
                dataset.samples = [dataset.samples[i] for i in selected_idx]
            else:
                # Arrow dataset
                import random
                all_idx = list(range(len(dataset.ds)))
                random.seed(42)
                random.shuffle(all_idx)
                selected_idx = all_idx[:max_images]
                dataset.ds = dataset.ds.select(selected_idx)
            print(f"  [QUICK TEST] Truncated {gen_name} to {max_images} images (shuffled).")

    results_per_split = {}
    all_y_true, all_y_prob = [], []

    for gen_name, dataset in datasets_map.items():
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=(device.type == 'cuda')
        )

        print(f"  Evaluating [{gen_name}]  ({len(dataset)} images)...")
        t0 = time.time()

        if model_info['type'] == 'resnet50':
            y_true, y_prob = run_inference_resnet(model_info['model'], loader, device)
        else:
            y_true, y_prob = run_inference_dual(
                model_info['model'], loader, device, model_info['compute_fft_fn']
            )

        elapsed = time.time() - t0
        metrics = compute_metrics(y_true, y_prob)
        metrics['time_sec'] = round(elapsed, 2)
        results_per_split[gen_name] = metrics

        all_y_true.append(y_true)
        all_y_prob.append(y_prob)

        print(f"    AP={metrics['ap']:.4f}  acc={metrics['acc']:.4f}  "
              f"oracle={metrics['oracle_acc']:.4f}  "
              f"2shot={metrics['two_shot_acc']:.4f}  [{elapsed:.1f}s]")

    # Overall metrics (concatenate all splits)
    all_y_true = np.concatenate(all_y_true)
    all_y_prob = np.concatenate(all_y_prob)
    results_overall = compute_metrics(all_y_true, all_y_prob)

    return results_per_split, results_overall


# ---------------------------------------------------------------------------
# 7.  Report (CSV + console table + JSON)
# ---------------------------------------------------------------------------

def print_table(title, results_per_split, results_overall, model_name):
    """In bảng kết quả đẹp ra console."""
    SEP = "=" * 90
    print(f"\n{SEP}")
    print(f"  {title}  |  Model: {model_name}")
    print(SEP)
    header = f"{'Generator':<20} {'N':>6} {'AP':>8} {'Acc':>8} {'Acc_R':>7} {'Acc_F':>7} {'Oracle':>8} {'2-Shot':>8}"
    print(header)
    print("-" * 90)

    for gen, m in results_per_split.items():
        row = (f"{gen:<20} {m['n_total']:>6} "
               f"{m['ap']:>8.4f} {m['acc']:>8.4f} "
               f"{m['acc_real']:>7.4f} {m['acc_fake']:>7.4f} "
               f"{m['oracle_acc']:>8.4f} {m['two_shot_acc']:>8.4f}")
        print(row)

    print("-" * 90)
    m = results_overall
    row = (f"{'OVERALL':<20} {m['n_total']:>6} "
           f"{m['ap']:>8.4f} {m['acc']:>8.4f} "
           f"{m['acc_real']:>7.4f} {m['acc_fake']:>7.4f} "
           f"{m['oracle_acc']:>8.4f} {m['two_shot_acc']:>8.4f}")
    print(row)
    print(SEP)


def save_csv(results_per_split, results_overall, model_name, output_path):
    """Lưu kết quả ra CSV."""
    rows = [
        [f"Model: {model_name}"],
        ["generator", "n_total", "n_real", "n_fake",
         "AP", "acc", "acc_real", "acc_fake",
         "oracle_acc", "oracle_thresh",
         "two_shot_acc", "two_shot_thresh",
         "time_sec"]
    ]
    for gen, m in results_per_split.items():
        rows.append([
            gen, m['n_total'], m['n_real'], m['n_fake'],
            f"{m['ap']:.6f}", f"{m['acc']:.6f}",
            f"{m['acc_real']:.6f}", f"{m['acc_fake']:.6f}",
            f"{m['oracle_acc']:.6f}", f"{m['oracle_thresh']:.4f}",
            f"{m['two_shot_acc']:.6f}", f"{m['two_shot_thresh']:.4f}",
            m.get('time_sec', 'N/A')
        ])
    m = results_overall
    rows.append([
        'OVERALL', m['n_total'], m['n_real'], m['n_fake'],
        f"{m['ap']:.6f}", f"{m['acc']:.6f}",
        f"{m['acc_real']:.6f}", f"{m['acc_fake']:.6f}",
        f"{m['oracle_acc']:.6f}", f"{m['oracle_thresh']:.4f}",
        f"{m['two_shot_acc']:.6f}", f"{m['two_shot_thresh']:.4f}",
        'N/A'
    ])
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(rows)
    print(f"  [SAVED] CSV: {output_path}")


def save_json(results_per_split, results_overall, model_name, output_path):
    """Lưu kết quả ra JSON."""
    data = {
        'model': model_name,
        'per_generator': results_per_split,
        'overall': results_overall
    }
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=float)
    print(f"  [SAVED] JSON: {output_path}")


# ---------------------------------------------------------------------------
# 8.  Comparison report
# ---------------------------------------------------------------------------

def print_comparison(results_map):
    """
    In bảng so sánh nhiều mô hình.
    results_map: dict { model_name: (results_per_split, results_overall) }
    """
    SEP = "=" * 110
    print(f"\n\n{SEP}")
    print("  COMPARISON TABLE - ForenSynths Evaluation")
    print(SEP)

    model_names = list(results_map.keys())
    # Get all generators
    all_gens = set()
    for _, (per_split, _) in results_map.items():
        all_gens.update(per_split.keys())
    all_gens = sorted(all_gens)

    # Header
    col_w = 22
    hdr = f"{'Generator':<20}"
    for mn in model_names:
        short = mn[:18]
        hdr += f"  {short:>18}(AP)"
    print(hdr)
    print("-" * 110)

    for gen in all_gens:
        row = f"{gen:<20}"
        for mn in model_names:
            per_split, _ = results_map[mn]
            if gen in per_split:
                row += f"  {per_split[gen]['ap']:>22.4f}"
            else:
                row += f"  {'N/A':>22}"
        print(row)

    print("-" * 110)
    row = f"{'OVERALL':<20}"
    for mn in model_names:
        _, overall = results_map[mn]
        row += f"  {overall['ap']:>22.4f}"
    print(row)
    print(SEP)

    # Detailed comparison
    print(f"\n{'Generator':<20}", end="")
    for mn in model_names:
        short = mn[:10]
        print(f"  {short:>10}_AP  {short:>10}_acc  {short:>10}_orc", end="")
    print()
    print("-" * 90)

    for gen in list(all_gens) + ['OVERALL']:
        print(f"{gen:<20}", end="")
        for mn in model_names:
            per_split, overall = results_map[mn]
            if gen == 'OVERALL':
                m = overall
            else:
                m = per_split.get(gen, None)
            if m:
                print(f"  {m['ap']:>12.4f}  {m['acc']:>12.4f}  {m['oracle_acc']:>12.4f}", end="")
            else:
                print(f"  {'N/A':>12}  {'N/A':>12}  {'N/A':>12}", end="")
        print()
    print("=" * 90)


def save_comparison_csv(results_map, output_path):
    """Lưu bảng so sánh ra CSV để báo cáo."""
    model_names = list(results_map.keys())
    all_gens = set()
    for _, (per_split, _) in results_map.items():
        all_gens.update(per_split.keys())
    all_gens = sorted(all_gens)

    header = ['Generator']
    for mn in model_names:
        header += [f'{mn}_AP', f'{mn}_acc', f'{mn}_acc_real', f'{mn}_acc_fake',
                   f'{mn}_oracle_acc', f'{mn}_two_shot_acc']

    rows = [header]
    for gen in list(all_gens) + ['OVERALL']:
        row = [gen]
        for mn in model_names:
            per_split, overall = results_map[mn]
            m = overall if gen == 'OVERALL' else per_split.get(gen)
            if m:
                row += [
                    f"{m['ap']:.6f}", f"{m['acc']:.6f}",
                    f"{m['acc_real']:.6f}", f"{m['acc_fake']:.6f}",
                    f"{m['oracle_acc']:.6f}", f"{m['two_shot_acc']:.6f}"
                ]
            else:
                row += ['N/A'] * 6
        rows.append(row)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(rows)
    print(f"\n  [SAVED] Comparison CSV: {output_path}")


# ---------------------------------------------------------------------------
# 9.  Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description='ForenSynths-style evaluation pipeline for CNNDetection models'
    )
    # Data
    p.add_argument('--dataroot', type=str, default='dataset/test',
                   help='Path to dataset root (e.g. dataset/test)')
    p.add_argument('--arrow_paths', nargs='+', default=[
        'C:/Users/84328/Downloads/data-00000-of-00192.arrow',
        'C:/Users/84328/Downloads/data-00001-of-00192.arrow',
        'C:/Users/84328/Downloads/data-00002-of-00192.arrow',
        'C:/Users/84328/Downloads/data-00003-of-00192.arrow',
        'C:/Users/84328/Downloads/data-00004-of-00192.arrow'
    ], help='Danh sách các file .arrow dataset (Sử dụng thay cho dataroot)')
    # Models
    p.add_argument('--resnet50_path', type=str,
                   default='weights/blur_jpg_prob0.5.pth',
                   help='Path tới ResNet-50 checkpoint (blur_jpg_prob0.5.pth)')
    p.add_argument('--dual_stream_path', type=str,
                   default='weights/dual_stream_resnet/best_model.pth',
                   help='Path tới DualStream checkpoint')
    p.add_argument('--dual_stream_enhanced_path', type=str,
                   default='weights/enhanced/best_model.pth',
                   help='Path tới DualStream Enhanced checkpoint')
    p.add_argument('--fft_only_enhanced_path', type=str,
                   default='weights/fft_only_enhanced/best_model.pth',
                   help='Path tới mô hình FFT-Only Enhanced checkpoint')
    p.add_argument('--dual_resnet_depth', type=int, default=34,
                   choices=[18, 34, 50],
                   help='ResNet depth của DualStream model')

    # Which models to run
    p.add_argument('--eval_resnet50', action='store_true', default=True,
                   help='Evaluate ResNet-50')
    p.add_argument('--no_resnet50', action='store_true',
                   help='Bỏ qua ResNet-50')
    p.add_argument('--eval_dual', action='store_true', default=False,
                   help='Evaluate DualStream')
    p.add_argument('--no_dual', action='store_true',
                   help='Bỏ qua DualStream')
    p.add_argument('--eval_enhanced', action='store_true', default=True,
                   help='Evaluate DualStream Enhanced')
    p.add_argument('--eval_fft_only', action='store_true', default=True,
                   help='Evaluate FFT-Only Enhanced')
    # Output
    p.add_argument('--results_dir', type=str, default='results/forensynths_eval',
                   help='Thư mục lưu kết quả')

    # Runtime
    p.add_argument('--batch_size', type=int, default=32)
    p.add_argument('--num_workers', type=int, default=0)
    p.add_argument('--max_images', type=int, default=0,
                   help='Max images per split (0=all). Use small number for quick test, e.g. 200')
    p.add_argument('--device', type=str, default='auto',
                   choices=['auto', 'cuda', 'cpu'],
                   help='Device to run inference on')

    return p.parse_args()


def main():
    args = parse_args()

    # Device
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)
    print(f"\n{'='*70}")
    print(f"  ForenSynths Evaluation Pipeline")
    print(f"  Device : {device}")
    print(f"  Dataset: {args.dataroot}")
    print(f"{'='*70}\n")

    os.makedirs(args.results_dir, exist_ok=True)
    results_map = {}

    # -----------------------------------------------------------------------
    # A) ResNet-50 (paper baseline)
    # -----------------------------------------------------------------------
    run_resnet = args.eval_resnet50 and not args.no_resnet50
    if run_resnet:
        if not os.path.isfile(args.resnet50_path):
            print(f"[WARNING] ResNet-50 weights not found: {args.resnet50_path}")
            run_resnet = False

    if run_resnet:
        print(f"\n" + "-"*70)
        print("  [1/2]  ResNet-50  (CNNDetection paper baseline)")
        print("-"*70)
        model, model_type = load_resnet50(args.resnet50_path, device)
        model_info = {'type': 'resnet50', 'model': model}

        per_split, overall = evaluate_model(
            model_info, args.dataroot, device,
            batch_size=args.batch_size, num_workers=args.num_workers, max_images=args.max_images, arrow_paths=args.arrow_paths
        )

        model_name = f"ResNet50_{os.path.basename(args.resnet50_path).replace('.pth','')}"
        print_table("ResNet-50 Results", per_split, overall, model_name)

        csv_path  = os.path.join(args.results_dir, f'{model_name}.csv')
        json_path = os.path.join(args.results_dir, f'{model_name}.json')
        save_csv(per_split, overall, model_name, csv_path)
        save_json(per_split, overall, model_name, json_path)

        results_map[model_name] = (per_split, overall)
        del model

    # -----------------------------------------------------------------------
    # B) DualStream (your model)
    # -----------------------------------------------------------------------
    run_dual = args.eval_dual and not args.no_dual
    if run_dual:
        if not os.path.isfile(args.dual_stream_path):
            print(f"[WARNING] DualStream weights not found: {args.dual_stream_path}")
            run_dual = False

    if run_dual:
        print(f"\n" + "-"*70)
        print("  [2/2]  DualStreamResNet  (your model)")
        print("-"*70)
        model, model_type, compute_fft_fn = load_dual_stream(
            args.dual_stream_path, device, args.dual_resnet_depth
        )
        model_info = {
            'type': 'dual_stream',
            'model': model,
            'compute_fft_fn': compute_fft_fn,
            'fft_size': 224
        }

        per_split, overall = evaluate_model(
            model_info, args.dataroot, device,
            batch_size=args.batch_size, num_workers=args.num_workers, max_images=args.max_images, arrow_paths=args.arrow_paths
        )

        model_name = f"DualStream_ResNet{args.dual_resnet_depth}"
        print_table("DualStream Results", per_split, overall, model_name)

        csv_path  = os.path.join(args.results_dir, f'{model_name}.csv')
        json_path = os.path.join(args.results_dir, f'{model_name}.json')
        save_csv(per_split, overall, model_name, csv_path)
        save_json(per_split, overall, model_name, json_path)

        results_map[model_name] = (per_split, overall)
        del model

    # -----------------------------------------------------------------------
    # C) DualStream Enhanced (your enhanced model)
    # -----------------------------------------------------------------------
    run_enhanced = args.eval_enhanced
    if run_enhanced:
        if not os.path.isfile(args.dual_stream_enhanced_path):
            print(f"[WARNING] DualStream Enhanced weights not found: {args.dual_stream_enhanced_path}")
            run_enhanced = False

    if run_enhanced:
        print(f"\n" + "-"*70)
        print("  [3/3]  DualStream Enhanced")
        print("-"*70)
        model, model_type, compute_fft_fn, fft_size = load_dual_stream_enhanced(
            args.dual_stream_enhanced_path, device
        )
        model_info = {
            'type': model_type,
            'model': model,
            'compute_fft_fn': compute_fft_fn,
            'fft_size': fft_size
        }

        per_split, overall = evaluate_model(
            model_info, args.dataroot, device,
            batch_size=args.batch_size, num_workers=args.num_workers, max_images=args.max_images, arrow_paths=args.arrow_paths
        )

        model_name = f"DualStream_Enhanced"
        print_table("DualStream Enhanced Results", per_split, overall, model_name)

        csv_path  = os.path.join(args.results_dir, f'{model_name}.csv')
        json_path = os.path.join(args.results_dir, f'{model_name}.json')
        save_csv(per_split, overall, model_name, csv_path)
        save_json(per_split, overall, model_name, json_path)

        results_map[model_name] = (per_split, overall)
        del model

    # -----------------------------------------------------------------------
    # D) FFT-Only Enhanced
    # -----------------------------------------------------------------------
    run_fft_only = args.eval_fft_only
    if run_fft_only:
        if not os.path.isfile(args.fft_only_enhanced_path):
            print(f"[WARNING] FFT-Only Enhanced weights not found: {args.fft_only_enhanced_path}")
            run_fft_only = False

    if run_fft_only:
        print(f"\n" + "-"*70)
        print("  [4/4]  FFT-Only Enhanced")
        print("-"*70)
        model, model_type, compute_fft_fn, fft_size = load_fft_only_enhanced(
            args.fft_only_enhanced_path, device
        )
        model_info = {
            'type': model_type,
            'model': model,
            'compute_fft_fn': compute_fft_fn,
            'fft_size': fft_size
        }

        per_split, overall = evaluate_model(
            model_info, args.dataroot, device,
            batch_size=args.batch_size, num_workers=args.num_workers, max_images=args.max_images, arrow_paths=args.arrow_paths
        )

        model_name = f"FFT_Only_Enhanced"
        print_table("FFT-Only Enhanced Results", per_split, overall, model_name)

        csv_path  = os.path.join(args.results_dir, f'{model_name}.csv')
        json_path = os.path.join(args.results_dir, f'{model_name}.json')
        save_csv(per_split, overall, model_name, csv_path)
        save_json(per_split, overall, model_name, json_path)

        results_map[model_name] = (per_split, overall)
        del model

    # -----------------------------------------------------------------------
    # E) Comparison
    # -----------------------------------------------------------------------
    if len(results_map) >= 2:
        print_comparison(results_map)
        comp_csv = os.path.join(args.results_dir, 'comparison_table.csv')
        save_comparison_csv(results_map, comp_csv)
    elif len(results_map) == 1:
        print("\n[INFO] Chỉ có 1 model được evaluate. Thêm model thứ 2 để so sánh.")

    print(f"\n[DONE] Evaluation complete!")
    print(f"   Results saved to: {os.path.abspath(args.results_dir)}\n")


if __name__ == '__main__':
    main()
