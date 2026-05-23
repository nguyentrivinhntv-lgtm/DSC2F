"""
Advanced ResNet Training với các kỹ thuật tối ưu
- Larger image size (64, 128, hoặc 224)
- MixUp & CutMix augmentation
- Label Smoothing
- OneCycleLR / Warmup + Cosine
- EMA (Exponential Moving Average)
- Stochastic Depth
- Stronger augmentation với RandAugment
"""

import os
import sys
import argparse
import time
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, roc_auc_score, average_precision_score
import numpy as np
from tqdm import tqdm
import copy

from networks.dual_stream_resnet_advanced import DualStreamResNetAdvanced, compute_fft_spectrum
from data.dual_stream_dataset import DualStreamDataset
import torchvision.transforms as transforms


class RandAugment:
    """RandAugment cho stronger augmentation"""
    def __init__(self, n=2, m=9):
        self.n = n  # Số augmentations
        self.m = m  # Magnitude (1-10)
        
    def __call__(self, img):
        ops = [
            self._autocontrast,
            self._equalize,
            self._rotate,
            self._shearX,
            self._shearY,
            self._translateX,
            self._translateY,
            self._brightness,
            self._contrast,
            self._sharpness,
        ]
        
        for _ in range(self.n):
            op = random.choice(ops)
            img = op(img)
        
        return img
    
    def _autocontrast(self, img):
        from PIL import ImageOps
        return ImageOps.autocontrast(img)
    
    def _equalize(self, img):
        from PIL import ImageOps
        return ImageOps.equalize(img)
    
    def _rotate(self, img):
        degrees = (self.m / 10) * 30
        return img.rotate(random.uniform(-degrees, degrees))
    
    def _shearX(self, img):
        from PIL import Image
        shear = (self.m / 10) * 0.3
        return img.transform(img.size, Image.AFFINE, 
                           (1, random.uniform(-shear, shear), 0, 0, 1, 0))
    
    def _shearY(self, img):
        from PIL import Image
        shear = (self.m / 10) * 0.3
        return img.transform(img.size, Image.AFFINE,
                           (1, 0, 0, random.uniform(-shear, shear), 1, 0))
    
    def _translateX(self, img):
        pixels = int((self.m / 10) * img.size[0] * 0.3)
        return img.transform(img.size, img.AFFINE, (1, 0, random.randint(-pixels, pixels), 0, 1, 0))
    
    def _translateY(self, img):
        pixels = int((self.m / 10) * img.size[1] * 0.3)
        return img.transform(img.size, img.AFFINE, (1, 0, 0, 0, 1, random.randint(-pixels, pixels)))
    
    def _brightness(self, img):
        from PIL import ImageEnhance
        factor = 1 + (self.m / 10) * random.uniform(-0.5, 0.5)
        return ImageEnhance.Brightness(img).enhance(factor)
    
    def _contrast(self, img):
        from PIL import ImageEnhance
        factor = 1 + (self.m / 10) * random.uniform(-0.5, 0.5)
        return ImageEnhance.Contrast(img).enhance(factor)
    
    def _sharpness(self, img):
        from PIL import ImageEnhance
        factor = 1 + (self.m / 10) * random.uniform(-0.5, 0.5)
        return ImageEnhance.Sharpness(img).enhance(factor)


class AdvancedAugmentation:
    """Strong augmentation với RandAugment"""
    def __init__(self, image_size=128, mode='train', use_randaugment=True):
        if mode == 'train':
            transforms_list = [
                transforms.Resize((image_size + 16, image_size + 16)),
                transforms.RandomCrop(image_size),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomVerticalFlip(p=0.2),
            ]
            
            if use_randaugment:
                transforms_list.append(RandAugment(n=2, m=7))
            
            transforms_list.extend([
                transforms.ColorJitter(brightness=0.3, contrast=0.3, 
                                      saturation=0.3, hue=0.15),
                transforms.RandomGrayscale(p=0.1),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225]),
                transforms.RandomErasing(p=0.2, scale=(0.02, 0.2)),  # Cutout
            ])
            
            self.transform = transforms.Compose(transforms_list)
        else:
            self.transform = transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
    
    def __call__(self, img):
        return self.transform(img)


class MixUp:
    """MixUp augmentation"""
    def __init__(self, alpha=0.4):
        self.alpha = alpha
    
    def __call__(self, rgb1, fft1, labels):
        if self.alpha > 0:
            lam = np.random.beta(self.alpha, self.alpha)
        else:
            lam = 1
        
        batch_size = rgb1.size(0)
        index = torch.randperm(batch_size).to(rgb1.device)
        
        mixed_rgb = lam * rgb1 + (1 - lam) * rgb1[index]
        mixed_fft = lam * fft1 + (1 - lam) * fft1[index]
        labels_a, labels_b = labels, labels[index]
        
        return mixed_rgb, mixed_fft, labels_a, labels_b, lam


class CutMix:
    """CutMix augmentation"""
    def __init__(self, alpha=1.0):
        self.alpha = alpha
    
    def __call__(self, rgb1, fft1, labels):
        if self.alpha > 0:
            lam = np.random.beta(self.alpha, self.alpha)
        else:
            lam = 1
        
        batch_size = rgb1.size(0)
        index = torch.randperm(batch_size).to(rgb1.device)
        
        # Random box
        W, H = rgb1.size(2), rgb1.size(3)
        cut_rat = np.sqrt(1 - lam)
        cut_w = int(W * cut_rat)
        cut_h = int(H * cut_rat)
        
        cx = np.random.randint(W)
        cy = np.random.randint(H)
        
        bbx1 = np.clip(cx - cut_w // 2, 0, W)
        bby1 = np.clip(cy - cut_h // 2, 0, H)
        bbx2 = np.clip(cx + cut_w // 2, 0, W)
        bby2 = np.clip(cy + cut_h // 2, 0, H)
        
        mixed_rgb = rgb1.clone()
        mixed_rgb[:, :, bbx1:bbx2, bby1:bby2] = rgb1[index, :, bbx1:bbx2, bby1:bby2]
        
        mixed_fft = fft1.clone()
        mixed_fft[:, :, bbx1:bbx2, bby1:bby2] = fft1[index, :, bbx1:bbx2, bby1:bby2]
        
        # Adjust lambda based on actual box area
        lam = 1 - ((bbx2 - bbx1) * (bby2 - bby1) / (W * H))
        
        labels_a, labels_b = labels, labels[index]
        
        return mixed_rgb, mixed_fft, labels_a, labels_b, lam


class LabelSmoothingBCELoss(nn.Module):
    """Binary Cross Entropy với Label Smoothing"""
    def __init__(self, smoothing=0.1):
        super().__init__()
        self.smoothing = smoothing
    
    def forward(self, pred, target):
        # Smooth labels: 0 -> smoothing/2, 1 -> 1 - smoothing/2
        target_smooth = target * (1 - self.smoothing) + 0.5 * self.smoothing
        return F.binary_cross_entropy_with_logits(pred, target_smooth)


class EMA:
    """Exponential Moving Average for model weights"""
    def __init__(self, model, decay=0.999):
        self.model = model
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        
        self._register()
    
    def _register(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()
    
    def update(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                new_average = (1.0 - self.decay) * param.data + self.decay * self.shadow[name]
                self.shadow[name] = new_average.clone()
    
    def apply_shadow(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data
                param.data = self.shadow[name]
    
    def restore(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                param.data = self.backup[name]
        self.backup = {}


class AdvancedResNetTrainer:
    def __init__(self, args):
        self.args = args
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        print("="*60)
        print("  ADVANCED DUAL-STREAM RESNET TRAINING")
        print("="*60)
        print(f"Device: {self.device}")
        print(f"Image Size: {args.image_size}")
        print(f"Model: ResNet{args.resnet_depth}")
        print(f"Use SE Block: {args.use_se}")
        print(f"MixUp Alpha: {args.mixup_alpha}")
        print(f"CutMix Alpha: {args.cutmix_alpha}")
        print(f"Label Smoothing: {args.label_smoothing}")
        print(f"Use EMA: {args.use_ema}")
        
        if self.device.type == 'cpu':
            torch.set_num_threads(os.cpu_count())
            print(f"CPU threads: {torch.get_num_threads()}")
        
        os.makedirs(args.save_dir, exist_ok=True)
        
        self._build_model()
        self._build_dataloaders()
        
        # Loss với Label Smoothing
        if args.label_smoothing > 0:
            self.criterion = LabelSmoothingBCELoss(args.label_smoothing)
        else:
            self.criterion = nn.BCEWithLogitsLoss()
        
        # MixUp / CutMix
        self.mixup = MixUp(args.mixup_alpha) if args.mixup_alpha > 0 else None
        self.cutmix = CutMix(args.cutmix_alpha) if args.cutmix_alpha > 0 else None
        
        # Optimizer với layer-wise learning rates
        pretrained_params = []
        new_params = []
        
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                if 'spatial_stream' in name and 'se_module' not in name:
                    pretrained_params.append(param)
                else:
                    new_params.append(param)
        
        self.optimizer = optim.AdamW([
            {'params': pretrained_params, 'lr': args.lr * 0.1},  # Lower LR for pretrained
            {'params': new_params, 'lr': args.lr}
        ], weight_decay=args.weight_decay)
        
        # Learning rate scheduler
        if args.scheduler == 'onecycle':
            self.scheduler = optim.lr_scheduler.OneCycleLR(
                self.optimizer,
                max_lr=[args.lr * 0.1, args.lr],
                epochs=args.epochs,
                steps_per_epoch=len(self.train_loader),
                pct_start=0.1,
                anneal_strategy='cos'
            )
            self.step_scheduler_per_batch = True
        elif args.scheduler == 'cosine_warmup':
            from torch.optim.lr_scheduler import LambdaLR
            warmup_epochs = 5
            
            def lr_lambda(epoch):
                if epoch < warmup_epochs:
                    return epoch / warmup_epochs
                return 0.5 * (1 + np.cos(np.pi * (epoch - warmup_epochs) / (args.epochs - warmup_epochs)))
            
            self.scheduler = LambdaLR(self.optimizer, lr_lambda)
            self.step_scheduler_per_batch = False
        else:
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer, T_max=args.epochs, eta_min=1e-6
            )
            self.step_scheduler_per_batch = False
        
        # EMA
        self.ema = EMA(self.model, decay=0.999) if args.use_ema else None
        
        self.best_auc = 0
        self.patience_counter = 0
        self.history = {
            'train_loss': [], 'train_acc': [],
            'val_loss': [], 'val_acc': [], 'val_auc': []
        }
    
    def _build_model(self):
        self.model = DualStreamResNetAdvanced(
            num_classes=1,
            dropout=self.args.dropout,
            pretrained=True,
            resnet_depth=self.args.resnet_depth,
            use_se=self.args.use_se,
            drop_path_rate=self.args.drop_path
        )
        self.model = self.model.to(self.device)
        
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"Total parameters: {total_params:,}")
        print(f"Trainable parameters: {trainable:,}")
    
    def _build_dataloaders(self):
        train_transform = AdvancedAugmentation(
            self.args.image_size, 
            mode='train',
            use_randaugment=self.args.use_randaugment
        )
        val_transform = AdvancedAugmentation(self.args.image_size, mode='val')
        
        train_dataset = DualStreamDataset(
            self.args.train_dir, 
            transform=train_transform,
            image_size=self.args.image_size,
            fft_channels=3
        )
        
        val_dataset = DualStreamDataset(
            self.args.val_dir,
            transform=val_transform,
            image_size=self.args.image_size,
            fft_channels=3
        )
        
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=self.args.batch_size,
            shuffle=True,
            num_workers=self.args.num_workers,
            pin_memory=(self.device.type == 'cuda'),
            drop_last=True  # Quan trọng cho MixUp/CutMix
        )
        
        self.val_loader = DataLoader(
            val_dataset,
            batch_size=self.args.batch_size,
            shuffle=False,
            num_workers=self.args.num_workers,
            pin_memory=(self.device.type == 'cuda')
        )
        
        print(f"Train: {len(train_dataset)} samples")
        print(f"Val: {len(val_dataset)} samples")
    
    def unfreeze_layer(self, layer_name):
        """Unfreeze specific layer"""
        for name, param in self.model.named_parameters():
            if layer_name in name:
                param.requires_grad = True
        print(f"  Unfroze {layer_name}")
    
    def progressive_unfreeze(self, epoch):
        """Dần dần unfreeze từ layers cuối lên"""
        if epoch == 3:
            self.unfreeze_layer('layer4')
        elif epoch == 6:
            self.unfreeze_layer('layer3')
        elif epoch == 9:
            self.unfreeze_layer('layer2')
        elif epoch == 12:
            self.unfreeze_layer('layer1')
            self.unfreeze_layer('conv1')
            self.unfreeze_layer('bn1')
    
    def train_epoch(self, epoch):
        self.model.train()
        total_loss = 0
        all_preds, all_labels = [], []
        
        # Progressive unfreezing
        self.progressive_unfreeze(epoch)
        
        pbar = tqdm(self.train_loader, desc=f'Epoch {epoch+1}/{self.args.epochs}')
        
        for rgb, fft, labels in pbar:
            rgb = rgb.to(self.device)
            fft = fft.to(self.device)
            labels = labels.to(self.device).float()
            
            # Random choice: MixUp, CutMix, or normal
            use_mix = random.random()
            if self.mixup and use_mix < 0.33:
                rgb, fft, labels_a, labels_b, lam = self.mixup(rgb, fft, labels)
                mixed = True
            elif self.cutmix and use_mix < 0.66:
                rgb, fft, labels_a, labels_b, lam = self.cutmix(rgb, fft, labels)
                mixed = True
            else:
                mixed = False
            
            self.optimizer.zero_grad()
            outputs = self.model(rgb, fft)
            
            if mixed:
                loss = lam * self.criterion(outputs.squeeze(), labels_a) + \
                       (1 - lam) * self.criterion(outputs.squeeze(), labels_b)
            else:
                loss = self.criterion(outputs.squeeze(), labels)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            # Update EMA
            if self.ema:
                self.ema.update()
            
            # Step scheduler if OneCycleLR
            if self.step_scheduler_per_batch:
                self.scheduler.step()
            
            total_loss += loss.item()
            
            with torch.no_grad():
                preds = torch.sigmoid(outputs).squeeze().cpu().numpy()
                all_preds.extend(preds.flatten().tolist() if preds.ndim > 0 else [preds.item()])
                if not mixed:
                    all_labels.extend(labels.cpu().numpy().flatten().tolist())
                else:
                    # Use dominant label for tracking
                    dominant_labels = (lam * labels_a + (1-lam) * labels_b).round()
                    all_labels.extend(dominant_labels.cpu().numpy().flatten().tolist())
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        avg_loss = total_loss / len(self.train_loader)
        accuracy = accuracy_score(all_labels, (np.array(all_preds) > 0.5).astype(int))
        
        return avg_loss, accuracy
    
    @torch.no_grad()
    def validate(self, use_ema=True):
        # Apply EMA weights for validation
        if self.ema and use_ema:
            self.ema.apply_shadow()
        
        self.model.eval()
        total_loss = 0
        all_preds, all_labels = [], []
        
        for rgb, fft, labels in tqdm(self.val_loader, desc='Validation'):
            rgb = rgb.to(self.device)
            fft = fft.to(self.device)
            labels = labels.to(self.device).float()
            
            outputs = self.model(rgb, fft)
            loss = F.binary_cross_entropy_with_logits(outputs.squeeze(), labels)
            
            total_loss += loss.item()
            preds = torch.sigmoid(outputs).squeeze().cpu().numpy()
            all_preds.extend(preds.flatten().tolist() if preds.ndim > 0 else [preds.item()])
            all_labels.extend(labels.cpu().numpy().flatten().tolist())
        
        # Restore original weights
        if self.ema and use_ema:
            self.ema.restore()
        
        avg_loss = total_loss / len(self.val_loader)
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)
        
        accuracy = accuracy_score(all_labels, (all_preds > 0.5).astype(int))
        
        try:
            auc = roc_auc_score(all_labels, all_preds)
            ap = average_precision_score(all_labels, all_preds)
        except:
            auc, ap = 0.5, 0.5
        
        return avg_loss, accuracy, auc, ap
    
    def save_checkpoint(self, epoch, is_best=False):
        # Save with EMA weights if available
        if self.ema:
            self.ema.apply_shadow()
        
        checkpoint = {
            'epoch': epoch,
            'model': self.model.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'best_auc': self.best_auc,
            'args': self.args,
            'history': self.history
        }
        
        torch.save(checkpoint, os.path.join(self.args.save_dir, 'latest.pth'))
        
        if is_best:
            torch.save(checkpoint, os.path.join(self.args.save_dir, 'best_model.pth'))
            print(f"  ✓ Saved best model (AUC: {self.best_auc:.4f})")
        
        if self.ema:
            self.ema.restore()
    
    def train(self):
        print(f"\nStarting training for {self.args.epochs} epochs...")
        print("="*60)
        
        for epoch in range(self.args.epochs):
            epoch_start = time.time()
            
            train_loss, train_acc = self.train_epoch(epoch)
            val_loss, val_acc, val_auc, val_ap = self.validate()
            
            # Step scheduler if not OneCycleLR
            if not self.step_scheduler_per_batch:
                self.scheduler.step()
            
            current_lr = self.optimizer.param_groups[0]['lr']
            
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)
            self.history['val_auc'].append(val_auc)
            
            epoch_time = time.time() - epoch_start
            
            print(f"\nEpoch {epoch+1}/{self.args.epochs} ({epoch_time:.1f}s) | LR: {current_lr:.2e}")
            print(f"  Train - Loss: {train_loss:.4f}, Acc: {train_acc:.4f}")
            print(f"  Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.4f}, AUC: {val_auc:.4f}, AP: {val_ap:.4f}")
            
            is_best = val_auc > self.best_auc
            if is_best:
                self.best_auc = val_auc
                self.patience_counter = 0
            else:
                self.patience_counter += 1
            
            self.save_checkpoint(epoch, is_best)
            
            if self.patience_counter >= self.args.patience:
                print(f"\n⚠️ Early stopping at epoch {epoch+1}")
                break
        
        print("\n" + "="*60)
        print("TRAINING COMPLETE!")
        print(f"Best Validation AUC: {self.best_auc:.4f}")
        print(f"Model saved to: {self.args.save_dir}")
        print("="*60)
        
        return self.history


def parse_args():
    parser = argparse.ArgumentParser()
    
    # Data
    parser.add_argument('--train_dir', type=str, default='dataset/train')
    parser.add_argument('--val_dir', type=str, default='dataset/val')
    parser.add_argument('--image_size', type=int, default=128,
                       help='Larger size helps ResNet (64, 128, 224)')
    
    # Model
    parser.add_argument('--resnet_depth', type=int, default=34, choices=[18, 34, 50],
                       help='ResNet depth (34 or 50 better than 18)')
    parser.add_argument('--use_se', action='store_true', default=True,
                       help='Use Squeeze-Excitation blocks')
    parser.add_argument('--dropout', type=float, default=0.4)
    parser.add_argument('--drop_path', type=float, default=0.1,
                       help='Stochastic depth rate')
    
    # Training
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=0.0005)
    parser.add_argument('--weight_decay', type=float, default=0.05)
    parser.add_argument('--patience', type=int, default=15)
    
    # Scheduler
    parser.add_argument('--scheduler', type=str, default='onecycle',
                       choices=['cosine', 'onecycle', 'cosine_warmup'])
    
    # Regularization
    parser.add_argument('--label_smoothing', type=float, default=0.1)
    parser.add_argument('--mixup_alpha', type=float, default=0.4)
    parser.add_argument('--cutmix_alpha', type=float, default=1.0)
    parser.add_argument('--use_randaugment', action='store_true', default=True)
    parser.add_argument('--use_ema', action='store_true', default=True)
    
    # System
    parser.add_argument('--num_workers', type=int, default=0)
    parser.add_argument('--save_dir', type=str, default='weights/dual_stream_resnet_advanced')
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("\n" + "="*60)
    print("  ADVANCED RESNET TRAINING")
    print("="*60)
    print("Improvements:")
    print("  - ResNet34/50 thay vì 18")
    print("  - Larger image size (128 thay vì 32)")
    print("  - MixUp + CutMix augmentation")
    print("  - Label Smoothing")
    print("  - Squeeze-Excitation blocks")
    print("  - Stochastic Depth")
    print("  - EMA (Exponential Moving Average)")
    print("  - OneCycleLR scheduler")
    print("  - RandAugment")
    print("="*60)
    
    trainer = AdvancedResNetTrainer(args)
    history = trainer.train()


if __name__ == "__main__":
    main()
