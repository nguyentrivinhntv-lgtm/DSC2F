"""
Training Script cho Dual-Stream CNN
Kết hợp Spatial (RGB) và Frequency (FFT) streams
"""

import os
import sys
import argparse
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, average_precision_score, roc_auc_score
import numpy as np
from tqdm import tqdm

from networks.dual_stream_cnn import DualStreamCNN, DualStreamResNet
from networks.enhanced_dual_stream import EnhancedDualStreamCNN
from data.dual_stream_dataset import DualStreamDataset, get_dual_stream_dataloader


def parse_args():
    parser = argparse.ArgumentParser(description='Train Dual-Stream CNN for Deepfake Detection')
    
    # Data
    parser.add_argument('--train_dir', type=str, required=True,
                        help='Thư mục chứa data training (có 0_real và 1_fake)')
    parser.add_argument('--val_dir', type=str, default=None,
                        help='Thư mục chứa data validation')
    
    # Model
    parser.add_argument('--model', type=str, default='dual_stream',
                        choices=['dual_stream', 'dual_stream_resnet', 'enhanced'],
                        help='Loại model (dual_stream, dual_stream_resnet, enhanced)')
    parser.add_argument('--image_size', type=int, default=224,
                        help='Kích thước ảnh input')
    parser.add_argument('--dropout', type=float, default=0.5,
                        help='Dropout rate')
    
    # Training
    parser.add_argument('--epochs', type=int, default=50,
                        help='Số epochs')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size')
    parser.add_argument('--lr', type=float, default=0.0001,
                        help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-4,
                        help='Weight decay')
    parser.add_argument('--patience', type=int, default=10,
                        help='Early stopping patience')
    
    # System
    parser.add_argument('--num_workers', type=int, default=4,
                        help='Số workers cho data loading')
    parser.add_argument('--save_dir', type=str, default='weights/dual_stream',
                        help='Thư mục lưu model')
    parser.add_argument('--resume', type=str, default=None,
                        help='Path đến checkpoint để resume training')
    parser.add_argument('--gpu', type=int, default=0,
                        help='GPU ID')
    
    return parser.parse_args()


class DualStreamTrainer:
    """Trainer cho Dual-Stream CNN"""
    
    def __init__(self, args):
        self.args = args
        self.device = torch.device(f'cuda:{args.gpu}' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        # Tạo thư mục lưu
        os.makedirs(args.save_dir, exist_ok=True)
        
        # Khởi tạo model
        self._build_model()
        
        # Khởi tạo data loaders
        self._build_dataloaders()
        
        # Loss và optimizer
        self.criterion = nn.BCEWithLogitsLoss()
        self.optimizer = optim.Adam(
            self.model.parameters(), 
            lr=args.lr, 
            weight_decay=args.weight_decay
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5
        )
        
        # Tracking
        self.best_val_acc = 0
        self.best_val_auc = 0
        self.patience_counter = 0
        self.start_epoch = 0
        
        # Resume nếu có
        if args.resume:
            self._load_checkpoint(args.resume)
    
    def _build_model(self):
        """Khởi tạo model"""
        if self.args.model == 'dual_stream':
            self.model = DualStreamCNN(num_classes=1, dropout=self.args.dropout)
        elif self.args.model == 'enhanced':
            self.model = EnhancedDualStreamCNN(num_classes=1, dropout=self.args.dropout)
        else:
            self.model = DualStreamResNet(num_classes=1, dropout=self.args.dropout)
        
        self.model = self.model.to(self.device)
        
        # Count parameters
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"Model: {self.args.model}")
        print(f"Total parameters: {total_params:,}")
        print(f"Trainable parameters: {trainable_params:,}")
    
    def _build_dataloaders(self):
        """Tạo data loaders"""
        print(f"\nLoading training data from: {self.args.train_dir}")
        self.train_loader = get_dual_stream_dataloader(
            self.args.train_dir,
            batch_size=self.args.batch_size,
            num_workers=self.args.num_workers,
            image_size=self.args.image_size,
            shuffle=True,
            is_train=True
        )
        
        if self.args.val_dir:
            print(f"Loading validation data from: {self.args.val_dir}")
            self.val_loader = get_dual_stream_dataloader(
                self.args.val_dir,
                batch_size=self.args.batch_size,
                num_workers=self.args.num_workers,
                image_size=self.args.image_size,
                shuffle=False,
                is_train=False
            )
        else:
            self.val_loader = None
    
    def _load_checkpoint(self, path):
        """Load checkpoint"""
        print(f"Loading checkpoint from: {path}")
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.start_epoch = checkpoint['epoch'] + 1
        self.best_val_acc = checkpoint.get('best_val_acc', 0)
        self.best_val_auc = checkpoint.get('best_val_auc', 0)
        print(f"Resumed from epoch {self.start_epoch}")
    
    def _save_checkpoint(self, epoch, is_best=False):
        """Lưu checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model': self.model.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'best_val_acc': self.best_val_acc,
            'best_val_auc': self.best_val_auc,
            'args': self.args
        }
        
        # Lưu checkpoint mới nhất
        path = os.path.join(self.args.save_dir, 'latest.pth')
        torch.save(checkpoint, path)
        
        # Lưu best model
        if is_best:
            best_path = os.path.join(self.args.save_dir, 'best_model.pth')
            torch.save(checkpoint, best_path)
            print(f"  ✓ Saved best model to {best_path}")
    
    def train_epoch(self, epoch):
        """Train một epoch"""
        self.model.train()
        
        total_loss = 0
        all_preds = []
        all_labels = []
        
        pbar = tqdm(self.train_loader, desc=f'Epoch {epoch+1}/{self.args.epochs} [Train]')
        
        for rgb, fft, labels in pbar:
            # Move to device
            rgb = rgb.to(self.device)
            fft = fft.to(self.device)
            labels = labels.to(self.device)
            
            # Forward
            self.optimizer.zero_grad()
            outputs = self.model(rgb, fft)
            loss = self.criterion(outputs.squeeze(), labels)
            
            # Backward
            loss.backward()
            self.optimizer.step()
            
            # Track
            total_loss += loss.item()
            preds = torch.sigmoid(outputs).squeeze().detach().cpu().numpy()
            all_preds.extend(preds.flatten().tolist() if preds.ndim > 0 else [preds.item()])
            all_labels.extend(labels.cpu().numpy().flatten().tolist())
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        # Metrics
        avg_loss = total_loss / len(self.train_loader)
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)
        
        accuracy = accuracy_score(all_labels, (all_preds > 0.5).astype(int))
        
        try:
            auc = roc_auc_score(all_labels, all_preds)
        except:
            auc = 0.5
        
        return avg_loss, accuracy, auc
    
    @torch.no_grad()
    def validate(self):
        """Validate model"""
        if self.val_loader is None:
            return 0, 0, 0
        
        self.model.eval()
        
        total_loss = 0
        all_preds = []
        all_labels = []
        
        pbar = tqdm(self.val_loader, desc='Validation')
        
        for rgb, fft, labels in pbar:
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
        except:
            auc = 0.5
        
        try:
            ap = average_precision_score(all_labels, all_preds)
        except:
            ap = 0
        
        return avg_loss, accuracy, auc, ap
    
    def train(self):
        """Training loop chính"""
        print("\n" + "="*60)
        print("BẮT ĐẦU TRAINING DUAL-STREAM CNN")
        print("="*60)
        
        for epoch in range(self.start_epoch, self.args.epochs):
            # Train
            train_loss, train_acc, train_auc = self.train_epoch(epoch)
            
            print(f"\nEpoch {epoch+1}/{self.args.epochs}")
            print(f"  Train - Loss: {train_loss:.4f}, Acc: {train_acc:.4f}, AUC: {train_auc:.4f}")
            
            # Validate
            if self.val_loader:
                val_loss, val_acc, val_auc, val_ap = self.validate()
                print(f"  Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.4f}, AUC: {val_auc:.4f}, AP: {val_ap:.4f}")
                
                # Update scheduler
                self.scheduler.step(val_loss)
                
                # Check for best model
                is_best = val_auc > self.best_val_auc
                if is_best:
                    self.best_val_auc = val_auc
                    self.best_val_acc = val_acc
                    self.patience_counter = 0
                else:
                    self.patience_counter += 1
                
                # Save checkpoint
                self._save_checkpoint(epoch, is_best)
                
                # Early stopping
                if self.patience_counter >= self.args.patience:
                    print(f"\n⚠️ Early stopping triggered after {epoch+1} epochs")
                    break
            else:
                # Không có validation, lưu theo train acc
                is_best = train_acc > self.best_val_acc
                if is_best:
                    self.best_val_acc = train_acc
                self._save_checkpoint(epoch, is_best)
            
            print()
        
        print("\n" + "="*60)
        print("TRAINING HOÀN TẤT!")
        print(f"Best Validation AUC: {self.best_val_auc:.4f}")
        print(f"Best Validation Accuracy: {self.best_val_acc:.4f}")
        print(f"Model saved to: {self.args.save_dir}")
        print("="*60)


def main():
    args = parse_args()
    
    # In thông tin
    print("\n" + "="*60)
    print("DUAL-STREAM CNN TRAINING")
    print("="*60)
    print(f"Model: {args.model}")
    print(f"Train data: {args.train_dir}")
    print(f"Val data: {args.val_dir}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.lr}")
    print(f"Image size: {args.image_size}")
    print("="*60)
    
    # Train
    trainer = DualStreamTrainer(args)
    trainer.train()


if __name__ == "__main__":
    main()
