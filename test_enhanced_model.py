"""Test Enhanced Model Loading and Prediction"""
import torch
from networks.enhanced_dual_stream import EnhancedDualStreamCNN
import os

# Load model
model_path = 'weights/enhanced/best_model.pth'
print(f'Loading model from: {model_path}')
print(f'File exists: {os.path.exists(model_path)}')

model = EnhancedDualStreamCNN(num_classes=1)

if os.path.exists(model_path):
    state_dict = torch.load(model_path, map_location='cpu', weights_only=False)
    print(f'State dict keys: {list(state_dict.keys()) if isinstance(state_dict, dict) else "direct weights"}')
    
    if 'model' in state_dict:
        model.load_state_dict(state_dict['model'])
        if 'best_acc' in state_dict:
            print(f'Best accuracy during training: {state_dict["best_acc"]:.2f}%')
        if 'epoch' in state_dict:
            print(f'Trained for epochs: {state_dict["epoch"]}')
    else:
        model.load_state_dict(state_dict)
    
    model.eval()
    print('Model loaded successfully!')
    
    # Test với dummy input
    rgb = torch.randn(1, 3, 224, 224)
    fft = torch.randn(1, 1, 224, 224)
    
    with torch.no_grad():
        output = model(rgb, fft)
        prob = torch.sigmoid(output).item() * 100
        print(f'Test output (random input): {prob:.2f}% fake probability')
else:
    print('Model file not found!')
