"""Check image sizes in different datasets."""
from PIL import Image
import os

datasets = [
    ("ForenSynths test (0_real)", "dataset/test/0_real"),
    ("ForenSynths test (1_fake)", "dataset/test/1_fake"),
    ("CIFAKE-raw train (REAL)", "dataset/cifake-raw/train/REAL"),
    ("CIFAKE-raw train (FAKE)", "dataset/cifake-raw/train/FAKE"),
]

for name, path in datasets:
    if not os.path.exists(path):
        print(f"{name}: NOT FOUND")
        continue
    files = [f for f in os.listdir(path) if f.lower().endswith(('.jpg','.png','.jpeg'))]
    count = len(files)
    sizes = set()
    for f in files[:10]:
        img = Image.open(os.path.join(path, f))
        sizes.add(img.size)
    print(f"{name}: {count} images, sizes={sizes}")
