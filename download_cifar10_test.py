"""
Download CIFAR-10 test set va luu thanh folder 0_real/
de dung cho evaluation pipeline.

CIFAR-10 test set = 10,000 anh that (32x32)
"""
import os
import torchvision
from PIL import Image
from tqdm import tqdm

# Output directory
output_dir = "dataset/cifar10_test/0_real"
os.makedirs(output_dir, exist_ok=True)

print("Downloading CIFAR-10 test set...")
cifar10_test = torchvision.datasets.CIFAR10(
    root="dataset/cifar10_download",
    train=False,
    download=True
)

print(f"CIFAR-10 test set: {len(cifar10_test)} images")

# Class names
classes = cifar10_test.classes
print(f"Classes: {classes}")

# Save all test images as 0_real (real images)
print(f"\nSaving images to {output_dir}...")
for i, (img, label) in enumerate(tqdm(cifar10_test, desc="Saving")):
    class_name = classes[label]
    filename = f"cifar10_{class_name}_{i:05d}.png"
    img.save(os.path.join(output_dir, filename))

count = len(os.listdir(output_dir))
print(f"\nDone! Saved {count} CIFAR-10 test images to: {output_dir}")
print(f"Image size: 32x32")
print(f"\nNote: These are REAL images only (0_real/).")
print(f"To run eval, pair with fake images in dataset/cifar10_test/1_fake/")
