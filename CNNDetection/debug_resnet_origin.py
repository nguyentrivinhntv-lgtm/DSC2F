"""Check ResNet-50 checkpoint origin."""
import torch
import os

path = 'weights/blur_jpg_prob0.5.pth'
print(f"File: {path}")
print(f"Size: {os.path.getsize(path) / 1024 / 1024:.1f} MB")

ckpt = torch.load(path, map_location='cpu', weights_only=False)

print(f"\nCheckpoint type: {type(ckpt)}")
if isinstance(ckpt, dict):
    print(f"Keys: {list(ckpt.keys())}")
    if 'args' in ckpt:
        print(f"Args: {ckpt['args']}")
    if 'epoch' in ckpt:
        print(f"Epoch: {ckpt['epoch']}")
    if 'model' in ckpt:
        print(f"Model keys count: {len(ckpt['model'])}")
        sample_keys = list(ckpt['model'].keys())[:5]
        print(f"Sample keys: {sample_keys}")
    # Check if it's just a raw state_dict
    first_key = list(ckpt.keys())[0]
    if 'weight' in first_key or 'bias' in first_key:
        print("\n>>> This is a RAW state_dict (no training metadata)")
        print(">>> Likely DOWNLOADED from CNNDetection paper, NOT trained locally")
    else:
        print(f"\nFirst key: {first_key}")
else:
    print("Checkpoint is not a dict - likely raw state_dict")

# Also check download script
print("\n" + "="*60)
dl_script = 'weights/download_weights.sh'
if os.path.exists(dl_script):
    print(f"Download script exists: {dl_script}")
    with open(dl_script, 'r') as f:
        print(f.read())
