"""
Training với ResNet Pretrained + Advanced Techniques
- Transfer Learning từ ImageNet
- Progressive training (unfreeze dần)
- Test-Time Augmentation (TTA)
- Gradient Accumulation
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

from networks.dual_stream_resnet import DualStreamResNet, compute_fft_spectrum
from data.dual_stream_dataset import DualStreamDataset
import torchvision.transforms as transforms


class AdvancedAugmentation:
    """Advanced augmentation pipeline"""
    def __init__(self, image_size=32, mode='train'):
        if mode == 'train':
            self.transform = transforms.Compose([
                transforms.Resize((image_size + 8, image_size + 8)),
                transforms.RandomCrop(image_size),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomRotation(15),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, 
                                       saturation=0.2, hue=0.1),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
        else:
            self.transform = transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
    
    def __call__(self, img):
        return self.transform(img)


class TTAAugmentation:
    """Test-Time Augmentation"""
    def __init__(self, image_size=32):
        self.image_size = image_size
        self.base_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        self.tta_transforms = [
            # Original
            transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ]),
            # Horizontal flip
            transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.RandomHorizontalFlip(p=1.0),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ]),
            # Vertical flip
            transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.RandomVerticalFlip(p=1.0),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ]),
            # Rotation
            transforms.Compose([
                transforms.Resize((image_size, image_size)),
                transforms.RandomRotation((90, 90)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ]),
        ]
    
    def __call__(self, img):
        return self.base_transform(img)
    
    def get_tta_batch(self, img):
        """Trả về batch của các augmented versions"""
        return [t(img) for t in self.tta_transforms]


class ResNetTrainer:
    def __init__(self, args):
        self.args = args
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        print("="*60)
        print("  DUAL-STREAM RESNET PRETRAINED TRAINING")
        print("="*60)
        print(f"Device: {self.device}")
        
        if self.device.type == 'cpu':
            torch.set_num_threads(os.cpu_count())
            print(f"CPU threads: {torch.get_num_threads()}")
        
        os.makedirs(args.save_dir, exist_ok=True)
        
        self._build_model()
        self._build_dataloaders()
        
        # Loss
        self.criterion = nn.BCEWithLogitsLoss()
        
        # Optimizer - lower LR cho pretrained layers
        pretrained_params = []
        new_params = []
        
        for name, param in self.model.named_parameters():
            if 'spatial_stream' in name and param.requires_grad:
                pretrained_params.append(param)
            else:
                new_params.append(param)
        
        self.optimizer = optim.AdamW([
            {'params': pretrained_params, 'lr': args.lr * 0.1},  # Lower LR
            {'params': new_params, 'lr': args.lr}
        ], weight_decay=args.weight_decay)
        
        # Scheduler
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=args.epochs, eta_min=1e-6
        )
        
        self.best_auc = 0
        self.patience_counter = 0
        self.history = {
            'train_loss': [], 'train_acc': [],
            'val_loss': [], 'val_acc': [], 'val_auc': []
        }
    
    def _build_model(self):
        self.model = DualStreamResNet(
            num_classes=1,
            dropout=self.args.dropout,
            pretrained=True
        )
        self.model = self.model.to(self.device)
        
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"Model: Dual-Stream ResNet18 Pretrained")
        print(f"Total parameters: {total_params:,}")
        print(f"Trainable parameters: {trainable:,}")
    
    def _build_dataloaders(self):
        train_transform = AdvancedAugmentation(self.args.image_size, mode='train')
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
    
    def unfreeze_all(self):
        """Unfreeze all layers cho fine-tuning"""
        for param in self.model.parameters():
            param.requires_grad = True
        
        # Giảm learning rate khi fine-tune toàn bộ mạng (tránh phá móp pretrained weight ImageNet)
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = 1e-4
        print("Unfroze all layers for fine-tuning")
    
    def train_epoch(self, epoch):
        self.model.train()
        total_loss = 0
        all_preds, all_labels = [], []
        
        # Progressive unfreezing
        if epoch == self.args.unfreeze_epoch:
            self.unfreeze_all()
        
        pbar = tqdm(self.train_loader, desc=f'Epoch {epoch+1}/{self.args.epochs}')
        
        for rgb, fft, labels in pbar:
            rgb = rgb.to(self.device)
            fft = fft.to(self.device)
            labels = labels.to(self.device)
            
            self.optimizer.zero_grad()
            outputs = self.model(rgb, fft)
            loss = self.criterion(outputs.squeeze(), labels)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            
            with torch.no_grad():
                preds = torch.sigmoid(outputs).squeeze().cpu().numpy()
                all_preds.extend(preds.flatten().tolist() if preds.ndim > 0 else [preds.item()])
                all_labels.extend(labels.cpu().numpy().flatten().tolist())
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
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
        
        torch.save(checkpoint, os.path.join(self.args.save_dir, 'latest.pth'))
        
        if is_best:
            torch.save(checkpoint, os.path.join(self.args.save_dir, 'best_model.pth'))
            print(f"  ✓ Saved best model (AUC: {self.best_auc:.4f})")
    
    def train(self):
        print(f"\nStarting training for {self.args.epochs} epochs...")
        print(f"Unfreeze all at epoch: {self.args.unfreeze_epoch}")
        print("="*60)
        
        for epoch in range(self.args.epochs):
            epoch_start = time.time()
            
            train_loss, train_acc = self.train_epoch(epoch)
            val_loss, val_acc, val_auc, val_ap = self.validate()
            
            self.scheduler.step()
            current_lr = self.optimizer.param_groups[0]['lr']
            
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)
            self.history['val_auc'].append(val_auc)
            
            epoch_time = time.time() - epoch_start
            
            print(f"\nEpoch {epoch+1}/{self.args.epochs} ({epoch_time:.1f}s)")
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
    
    parser.add_argument('--train_dir', type=str, default='dataset/train')
    parser.add_argument('--val_dir', type=str, default='dataset/val')
    parser.add_argument('--image_size', type=int, default=32)
    
    parser.add_argument('--dropout', type=float, default=0.5)
    
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--lr', type=float, default=0.001)
    parser.add_argument('--weight_decay', type=float, default=0.01)
    parser.add_argument('--patience', type=int, default=10)
    parser.add_argument('--unfreeze_epoch', type=int, default=5, 
                       help='Epoch to unfreeze all layers')
    
    parser.add_argument('--num_workers', type=int, default=0)
    parser.add_argument('--save_dir', type=str, default='weights/dual_stream_resnet')
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("\n" + "="*60)
    print("  RESNET PRETRAINED TRANSFER LEARNING")
    print("="*60)
    print(f"Using pretrained ResNet18 from ImageNet")
    print(f"Progressive unfreezing at epoch {args.unfreeze_epoch}")
    print("="*60)
    
    trainer = ResNetTrainer(args)
    history = trainer.train()


if __name__ == "__main__":
    main()
