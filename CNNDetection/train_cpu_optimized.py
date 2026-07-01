"""
Training tối ưu cho CPU (Intel)
Sử dụng các kỹ thuật tối ưu để training nhanh hơn
"""

import os
import sys
import argparse
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, roc_auc_score
import numpy as np
from tqdm import tqdm

from networks.dual_stream_cnn import DualStreamCNN
from data.dual_stream_dataset import DualStreamDataset


def parse_args():
    parser = argparse.ArgumentParser(description='Train Dual-Stream CNN (CPU Optimized)')
    
    parser.add_argument('--train_dir', type=str, default='dataset/train')
    parser.add_argument('--val_dir', type=str, default='dataset/val')
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--lr', type=float, default=0.001)
    parser.add_argument('--image_size', type=int, default=32)
    parser.add_argument('--save_dir', type=str, default='weights/dual_stream')
    parser.add_argument('--num_workers', type=int, default=0)
    
    return parser.parse_args()


def train():
    args = parse_args()
    
    print("="*60)
    print("  DUAL-STREAM CNN TRAINING (CPU OPTIMIZED)")
    print("="*60)
    
    # Tạo thư mục lưu
    os.makedirs(args.save_dir, exist_ok=True)
    
    # CPU optimizations
    torch.set_num_threads(os.cpu_count())
    print(f"Using {torch.get_num_threads()} CPU threads")
    
    # Model
    model = DualStreamCNN(num_classes=1, dropout=0.5)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {total_params:,}")
    
    # Data
    print(f"\nLoading data...")
    
    import torchvision.transforms as transforms
    
    train_transform = transforms.Compose([
        transforms.Resize((args.image_size, args.image_size)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((args.image_size, args.image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    train_dataset = DualStreamDataset(args.train_dir, transform=train_transform, image_size=args.image_size)
    val_dataset = DualStreamDataset(args.val_dir, transform=val_transform, image_size=args.image_size)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, 
                              num_workers=args.num_workers, pin_memory=False)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False,
                            num_workers=args.num_workers, pin_memory=False)
    
    print(f"Train: {len(train_dataset)} samples, Val: {len(val_dataset)} samples")
    
    # Loss and optimizer
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)
    
    # Training
    best_auc = 0
    
    print(f"\nStarting training for {args.epochs} epochs...")
    print("="*60)
    
    for epoch in range(args.epochs):
        epoch_start = time.time()
        
        # Train
        model.train()
        train_loss = 0
        train_preds, train_labels = [], []
        
        pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{args.epochs}')
        for rgb, fft, labels in pbar:
            optimizer.zero_grad()
            outputs = model(rgb, fft)
            loss = criterion(outputs.squeeze(), labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            preds = torch.sigmoid(outputs).squeeze().detach().numpy()
            train_preds.extend(preds.flatten().tolist() if preds.ndim > 0 else [preds.item()])
            train_labels.extend(labels.numpy().flatten().tolist())
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        train_loss /= len(train_loader)
        train_acc = accuracy_score(train_labels, (np.array(train_preds) > 0.5).astype(int))
        
        # Validate
        model.eval()
        val_loss = 0
        val_preds, val_labels = [], []
        
        with torch.no_grad():
            for rgb, fft, labels in val_loader:
                outputs = model(rgb, fft)
                loss = criterion(outputs.squeeze(), labels)
                val_loss += loss.item()
                
                preds = torch.sigmoid(outputs).squeeze().numpy()
                val_preds.extend(preds.flatten().tolist() if preds.ndim > 0 else [preds.item()])
                val_labels.extend(labels.numpy().flatten().tolist())
        
        val_loss /= len(val_loader)
        val_acc = accuracy_score(val_labels, (np.array(val_preds) > 0.5).astype(int))
        
        try:
            val_auc = roc_auc_score(val_labels, val_preds)
        except:
            val_auc = 0.5
        
        scheduler.step(val_loss)
        
        epoch_time = time.time() - epoch_start
        
        print(f"\nEpoch {epoch+1}/{args.epochs} ({epoch_time:.1f}s)")
        print(f"  Train - Loss: {train_loss:.4f}, Acc: {train_acc:.4f}")
        print(f"  Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.4f}, AUC: {val_auc:.4f}")
        
        # Save best
        if val_auc > best_auc:
            best_auc = val_auc
            torch.save({
                'epoch': epoch,
                'model': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'best_auc': best_auc,
            }, os.path.join(args.save_dir, 'best_model.pth'))
            print(f"  ✓ Saved best model (AUC: {best_auc:.4f})")
        
        # Save latest
        torch.save({
            'epoch': epoch,
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
        }, os.path.join(args.save_dir, 'latest.pth'))
    
    print("\n" + "="*60)
    print("TRAINING COMPLETE!")
    print(f"Best Validation AUC: {best_auc:.4f}")
    print(f"Model saved to: {args.save_dir}")
    print("="*60)


if __name__ == "__main__":
    train()
