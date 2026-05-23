import os
import pandas as pd
import io
from PIL import Image
import shutil

def extract_parquets(parquet_paths, output_dir, max_per_class=10000):
    # Clean previous extraction
    if os.path.exists(output_dir):
        print(f"Cleaning existing directory {output_dir}...")
        shutil.rmtree(output_dir)
        
    os.makedirs(os.path.join(output_dir, "REAL"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "FAKE"), exist_ok=True)
    
    count_real = 0
    count_fake = 0
    
    for parquet_path in parquet_paths:
        if count_real >= max_per_class and count_fake >= max_per_class:
            break
            
        print(f"Reading {parquet_path}...")
        try:
            df = pd.read_parquet(parquet_path)
        except Exception as e:
            print(f"Error reading {parquet_path}: {e}")
            continue
            
        print(f"Rows in file: {len(df)}")
        
        for i, row in df.iterrows():
            if count_real >= max_per_class and count_fake >= max_per_class:
                break
                
            label = row['label'] if 'label' in df.columns else row['target']
            
            # FIXED LOGIC for mvkvc/artifact-100k:
            # 0 is AI (FAKE), 1 is REAL
            if label == 1: # REAL
                if count_real >= max_per_class: continue
                count_real += 1
                idx = count_real
                folder = "REAL"
            else: # FAKE
                if count_fake >= max_per_class: continue
                count_fake += 1
                idx = count_fake
                folder = "FAKE"
            
            img_data = row['image']
            img_bytes = img_data['bytes'] if isinstance(img_data, dict) and 'bytes' in img_data else img_data
            
            try:
                img = Image.open(io.BytesIO(img_bytes))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                img_name = f"{folder}_{idx:05d}.jpg"
                img.save(os.path.join(output_dir, folder, img_name), "JPEG", quality=90)
                
                if (count_real + count_fake) % 1000 == 0:
                    print(f"Extracted: REAL={count_real}, FAKE={count_fake} (Total: {count_real+count_fake})")
                    
            except Exception as e:
                if folder == "REAL": count_real -= 1
                else: count_fake -= 1
                
    print(f"\nFinal Count: {count_real} REAL and {count_fake} FAKE images saved to {output_dir}")

if __name__ == "__main__":
    import sys
    # Usage: python extract_images.py <output_dir> <max_per_class> <file1> <file2> ...
    if len(sys.argv) < 4:
        print("Usage: python extract_images.py <output_dir> <max_per_class> <parquet_file1> ...")
    else:
        o_dir = sys.argv[1]
        m_pc = int(sys.argv[2])
        p_files = sys.argv[3:]
        extract_parquets(p_files, o_dir, m_pc)
