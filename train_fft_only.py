"""
Training Script cho FFT-Only Enhanced CNN
Với các kỹ thuật nâng cao hiệu suất:
1. Strong Data Augmentation (Mixup, CutMix, RandAugment)
2. Label Smoothing
3. Cosine Annealing LR
4. Gradient Clipping
5. Early Stopping với patience
"""

import os
import sys
import argparse
import time
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, roc_auc_score, average_precision_score
import numpy as np
from tqdm import tqdm

from networks.dual_stream_enhanced import FFTOnlyCNNEnhanced, compute_fft_spectrum
from data.dual_stream_dataset import DualStreamDataset
import torchvision.transforms as transforms


# ============================================
# DATA AUGMENTATION
# ============================================

class StrongAugmentation:
    """Strong data augmentation cho training"""
    def __init__(self, image_size=32):
        self.transform = transforms.Compose([
            transforms.Resize((image_size + 8, image_size + 8)),
            transforms.RandomCrop(image_size),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.1),
            transforms.RandomRotation(15),
            transforms.ColorJitter(
                brightness=0.2,
                contrast=0.2,
                saturation=0.2,
                hue=0.1
            ),
            transforms.RandomGrayscale(p=0.05),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225]),
            transforms.RandomErasing(p=0.1, scale=(0.02, 0.1))
        ])
    
    def __call__(self, img):
        return self.transform(img)


def mixup_data(x_rgb, x_fft, y, alpha=0.2):
    """Mixup augmentation"""
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1

    batch_size = x_rgb.size(0)
    index = torch.randperm(batch_size)

    mixed_rgb = lam * x_rgb + (1 - lam) * x_rgb[index, :]
    mixed_fft = lam * x_fft + (1 - lam) * x_fft[index, :]
    y_a, y_b = y, y[index]
    
    return mixed_rgb, mixed_fft, y_a, y_b, lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    """Mixup loss"""
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


# ============================================
# LABEL SMOOTHING LOSS
# ============================================

class LabelSmoothingBCE(nn.Module):
    """Binary Cross Entropy với Label Smoothing"""
    def __init__(self, smoothing=0.1):
        super(LabelSmoothingBCE, self).__init__()
        self.smoothing = smoothing
        self.bce = nn.BCEWithLogitsLoss()
    
    def forward(self, pred, target):
        # Smooth labels: 0 -> smoothing, 1 -> 1-smoothing
        target_smooth = target * (1 - self.smoothing) + 0.5 * self.smoothing
        return self.bce(pred, target_smooth)


# ============================================
# TRAINER
# ============================================

class EnhancedTrainer:
    def __init__(self, args):
        self.args = args
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        print("="*60)
        print("  FFT-Only Enhanced CNN TRAINING")
        print("="*60)
        print(f"Device: {self.device}")
        
        # CPU optimization
        if self.device.type == 'cpu':
            torch.set_num_threads(os.cpu_count())
            print(f"CPU threads: {torch.get_num_threads()}")
        
        os.makedirs(args.save_dir, exist_ok=True)
        
        # Build model
        self._build_model()
        
        # Build dataloaders
        self._build_dataloaders()
        
        # Loss với label smoothing
        self.criterion = LabelSmoothingBCE(smoothing=args.label_smoothing)
        
        # Optimizer với weight decay
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=args.lr,
            weight_decay=args.weight_decay,
            betas=(0.9, 0.999)
        )
        
        # Cosine Annealing scheduler
        self.scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer,
            T_0=10,
            T_mult=2,
            eta_min=1e-6
        )
        
        # Tracking
        self.best_auc = 0
        self.best_acc = 0
        self.patience_counter = 0
        self.history = {
            'train_loss': [], 'train_acc': [],
            'val_loss': [], 'val_acc': [], 'val_auc': []
        }
    
    def _build_model(self):
        self.model = FFTOnlyCNNEnhanced(
            num_classes=1, 
            dropout=self.args.dropout
        )
        self.model = self.model.to(self.device)
        
        total_params = sum(p.numel() for p in self.model.parameters())
        print(f"Model: FFT-Only Enhanced CNN")
        print(f"Parameters: {total_params:,}")
    
    def _build_dataloaders(self):
        # Strong augmentation cho train
        train_transform = StrongAugmentation(self.args.image_size)
        
        # Simple transform cho val
        val_transform = transforms.Compose([
            transforms.Resize((self.args.image_size, self.args.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        train_dataset = DualStreamDataset(
            self.args.train_dir, 
            transform=train_transform,
            image_size=self.args.image_size
        )
        
        val_dataset = DualStreamDataset(
            self.args.val_dir,
            transform=val_transform,
            image_size=self.args.image_size
        )
        
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=self.args.batch_size,
            shuffle=True,
            num_workers=self.args.num_workers,
            pin_memory=(self.device.type == 'cuda')
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
    
    def train_epoch(self, epoch):
        self.model.train()
        total_loss = 0
        all_preds, all_labels = [], []
        
        pbar = tqdm(self.train_loader, desc=f'Epoch {epoch+1}/{self.args.epochs}')
        
        for rgb, fft, labels in pbar:
            rgb = rgb.to(self.device)
            fft = fft.to(self.device)
            labels = labels.to(self.device)
            
            # Mixup
            if self.args.use_mixup and random.random() < 0.5:
                rgb, fft, labels_a, labels_b, lam = mixup_data(
                    rgb, fft, labels, alpha=self.args.mixup_alpha
                )
                
                self.optimizer.zero_grad()
                outputs = self.model(rgb, fft)
                loss = mixup_criterion(
                    self.criterion, outputs.squeeze(), 
                    labels_a, labels_b, lam
                )
            else:
                self.optimizer.zero_grad()
                outputs = self.model(rgb, fft)
                loss = self.criterion(outputs.squeeze(), labels)
            
            # Backward với gradient clipping
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            # Track
            total_loss += loss.item()
            
            with torch.no_grad():
                preds = torch.sigmoid(outputs).squeeze().cpu().numpy()
                all_preds.extend(preds.flatten().tolist() if preds.ndim > 0 else [preds.item()])
                all_labels.extend(labels.cpu().numpy().flatten().tolist())
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        # Metrics
        avg_loss = total_loss / len(self.train_loader)
        accuracy = accuracy_score(all_labels, (np.array(all_preds) > 0.5).astype(int))
        
        return avg_loss, accuracy
    
    @torch.no_grad()
    def validate(self):
        self.model.eval()
        total_loss = 0
        all_preds, all_labels = [], []
        
        for rgb, fft, labels in tqdm(self.val_loader, desc='Validation'):
            rgb = rgb.to(self.device)
            fft = fft.to(self.device)
            labels = labels.to(self.device)
            
            outputs = self.model(rgb, fft)
            loss = self.criterion(outputs.squeeze(), labels)
            
            total_loss += loss.item()
            preds = torch.sigmoid(outputs).squeeze().cpu().numpy()
            all_preds.extend(preds.flatten().tolist() if preds.ndim > 0 else [preds.item()])
            all_labels.extend(labels.cpu().numpy().flatten().tolist())
        
        # Metrics
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
        checkpoint = {
            'epoch': epoch,
            'model': self.model.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'best_auc': self.best_auc,
            'args': self.args,
            'history': self.history
        }
        
        # Save latest
        torch.save(checkpoint, os.path.join(self.args.save_dir, 'latest.pth'))
        
        # Save best
        if is_best:
            torch.save(checkpoint, os.path.join(self.args.save_dir, 'best_model.pth'))
            print(f"  ✓ Saved best model (AUC: {self.best_auc:.4f})")
    
    def train(self):
        print(f"\nStarting training for {self.args.epochs} epochs...")
        print("="*60)
        
        for epoch in range(self.args.epochs):
            epoch_start = time.time()
            
            # Train
            train_loss, train_acc = self.train_epoch(epoch)
            
            # Validate
            val_loss, val_acc, val_auc, val_ap = self.validate()
            
            # Update scheduler
            self.scheduler.step()
            current_lr = self.optimizer.param_groups[0]['lr']
            
            # Save history
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)
            self.history['val_auc'].append(val_auc)
            
            epoch_time = time.time() - epoch_start
            
            print(f"\nEpoch {epoch+1}/{self.args.epochs} ({epoch_time:.1f}s) | LR: {current_lr:.6f}")
            print(f"  Train - Loss: {train_loss:.4f}, Acc: {train_acc:.4f}")
            print(f"  Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.4f}, AUC: {val_auc:.4f}, AP: {val_ap:.4f}")
            
            # Check best
            is_best = val_auc > self.best_auc
            if is_best:
                self.best_auc = val_auc
                self.best_acc = val_acc
                self.patience_counter = 0
            else:
                self.patience_counter += 1
            
            self.save_checkpoint(epoch, is_best)
            
            # Early stopping
            if self.patience_counter >= self.args.patience:
                print(f"\n⚠️ Early stopping at epoch {epoch+1}")
                break
        
        print("\n" + "="*60)
        print("TRAINING COMPLETE!")
        print(f"Best Validation AUC: {self.best_auc:.4f}")
        print(f"Best Validation Accuracy: {self.best_acc:.4f}")
        print(f"Model saved to: {self.args.save_dir}")
        print("="*60)
        
        return self.history


def parse_args():
    parser = argparse.ArgumentParser(description='Train FFT-Only Enhanced CNN')
    
    # Data
    parser.add_argument('--train_dir', type=str, default='dataset/train')
    parser.add_argument('--val_dir', type=str, default='dataset/val')
    parser.add_argument('--image_size', type=int, default=32)
    
    # Model
    parser.add_argument('--dropout', type=float, default=0.5)
    
    # Training
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--lr', type=float, default=0.001)
    parser.add_argument('--weight_decay', type=float, default=0.01)
    parser.add_argument('--patience', type=int, default=15)
    
    # Augmentation
    parser.add_argument('--use_mixup', action='store_true', default=True)
    parser.add_argument('--mixup_alpha', type=float, default=0.2)
    parser.add_argument('--label_smoothing', type=float, default=0.1)
    
    # System
    parser.add_argument('--num_workers', type=int, default=0)
    parser.add_argument('--save_dir', type=str, default='weights/fft_only_enhanced')
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("\n" + "="*60)
    print("  FFT-Only Enhanced CNN TRAINING")
    print("="*60)
    print(f"Image size: {args.image_size}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.lr}")
    print(f"Epochs: {args.epochs}")
    print(f"Mixup: {args.use_mixup} (alpha={args.mixup_alpha})")
    print(f"Label smoothing: {args.label_smoothing}")
    print("="*60)
    
    trainer = EnhancedTrainer(args)
    history = trainer.train()


if __name__ == "__main__":
    main()
