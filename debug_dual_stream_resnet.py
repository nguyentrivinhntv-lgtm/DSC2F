"""Debug DualStreamResNet checkpoint to find training config mismatch."""
import torch

path = "weights/dual_stream_resnet/best_model.pth"
print(f"Loading: {path}")
ckpt = torch.load(path, map_location='cpu', weights_only=False)

# 1. Check top-level keys
print(f"\nTop-level keys: {list(ckpt.keys())}")

# 2. Check training args
args = ckpt.get('args', None)
if args is not None:
    print(f"\n=== Training Args ===")
    if hasattr(args, '__dict__'):
        for k, v in vars(args).items():
            print(f"  {k}: {v}")
    else:
        print(f"  args = {args}")

# 3. Check model weight shapes (especially first conv layers)
state = ckpt.get('model', ckpt)
print(f"\n=== Key weight shapes ===")
for key in sorted(state.keys()):
    shape = state[key].shape
    if 'conv1' in key or 'features.0' in key or 'classifier' in key or 'fusion' in key or key.endswith('.weight'):
        print(f"  {key}: {shape}")

# 4. Check frequency stream first conv input channels
freq_conv_keys = [k for k in state.keys() if 'frequency' in k and 'conv' in k and 'weight' in k]
print(f"\n=== Frequency stream conv weights ===")
for k in freq_conv_keys[:5]:
    print(f"  {k}: {state[k].shape}")

# 5. Check spatial stream first conv
spatial_conv_keys = [k for k in state.keys() if 'spatial' in k and 'conv1' in k and 'weight' in k]
print(f"\n=== Spatial stream conv1 ===")
for k in spatial_conv_keys:
    print(f"  {k}: {state[k].shape}")

# 6. Training history
history = ckpt.get('history', None)
if history:
    print(f"\n=== Training History ===")
    for metric, values in history.items():
        if values:
            print(f"  {metric}: last={values[-1]:.4f}, best={'max' if 'acc' in metric or 'auc' in metric else 'min'}={max(values) if 'acc' in metric or 'auc' in metric else min(values):.4f}, epochs={len(values)}")

print(f"\nBest AUC from checkpoint: {ckpt.get('best_auc', 'N/A')}")
print(f"Epoch: {ckpt.get('epoch', 'N/A')}")
