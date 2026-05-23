# Hướng Dẫn Sử Dụng Ứng Dụng CNN Detection

## Giới Thiệu
Ứng dụng CNN Detection được sử dụng để phát hiện ảnh được tạo bởi các mạng neural tích chập (CNN) như StyleGAN, ProGAN, BigGAN, v.v. Ứng dụng có thể phân biệt ảnh thật và ảnh giả với độ chính xác cao.

## Cài Đặt Môi Trường

### 1. Cài đặt các gói phụ thuộc
```bash
pip install scipy scikit-learn numpy opencv-python Pillow torch>=1.2.0 torchvision
```

### 2. Tải trọng số mô hình (Model Weights)
Các file trọng số đã được tải về và lưu trong thư mục `weights/`:
- `blur_jpg_prob0.5.pth` (model chính)
- `blur_jpg_prob0.1.pth` (model phụ)

## Cách Sử Dụng

### 1. Phân Tích Một Ảnh Đơn Lẻ

Để kiểm tra một ảnh có phải ảnh giả hay không:

```bash
# Kiểm tra ảnh thật
python demo.py -f examples/real.png -m weights/blur_jpg_prob0.5.pth --use_cpu

# Kiểm tra ảnh giả  
python demo.py -f examples/fake.png -m weights/blur_jpg_prob0.5.pth --use_cpu
```

**Kết quả:**
- `probability of being synthetic: 0.00%` → Ảnh thật
- `probability of being synthetic: 99.86%` → Ảnh giả

### 2. Phân Tích Một Thư Mục Ảnh

Để đánh giá hiệu suất trên một dataset:

```bash
python demo_dir.py -d examples/realfakedir -m weights/blur_jpg_prob0.5.pth --use_cpu
```

**Kết quả hiển thị:**
- `AP`: Average Precision 
- `Acc`: Độ chính xác tổng thể
- `Acc (real)`: Độ chính xác với ảnh thật
- `Acc (fake)`: Độ chính xác với ảnh giả

### 3. Các Tùy Chọn Khác

#### Cắt ảnh (Cropping):
```bash
# Cắt ảnh về kích thước 224x224 pixel
python demo.py -f your_image.jpg -m weights/blur_jpg_prob0.5.pth --use_cpu -c 224
```

#### Sử dụng model khác:
```bash
# Sử dụng model blur_jpg_prob0.1
python demo.py -f your_image.jpg -m weights/blur_jpg_prob0.1.pth --use_cpu
```

## Cấu Trúc Thư Mục Dataset

Nếu bạn muốn tạo dataset riêng để test, cần tổ chức theo cấu trúc:

```
your_dataset/
├── 0_real/          # Thư mục chứa ảnh thật
│   ├── real1.jpg
│   ├── real2.jpg
│   └── ...
└── 1_fake/          # Thư mục chứa ảnh giả
    ├── fake1.jpg
    ├── fake2.jpg
    └── ...
```

Sau đó chạy:
```bash
python demo_dir.py -d your_dataset -m weights/blur_jpg_prob0.5.pth --use_cpu
```

## Lưu Ý Quan Trọng

1. **Luôn sử dụng flag `--use_cpu`** vì hệ thống không có GPU CUDA.

2. **Kích thước ảnh đầu vào**: Ảnh sẽ được tự động resize, nhưng nên sử dụng ảnh có độ phân giải tốt.

3. **Hiệu suất tốt nhất**: Model hoạt động tốt nhất với ảnh không bị cắt (no crop).

4. **Các định dạng ảnh hỗ trợ**: JPG, PNG, và các định dạng ảnh phổ biến khác.

## Hiệu Suất Model

Model `blur_jpg_prob0.5` có hiệu suất cao trên các loại ảnh giả:
- ProGAN: 100% AP
- StyleGAN: 99.3% AP  
- CycleGAN: 97.9% AP
- BigGAN: 90.4% AP
- Và nhiều loại khác...

## Xử Lý Sự Cố

### Lỗi CUDA:
- Luôn thêm `--use_cpu` vào lệnh

### Lỗi Multiprocessing (Windows):
- File `demo_dir.py` đã được sửa để tương thích với Windows

### Lỗi Module không tìm thấy:
- Kiểm tra lại việc cài đặt packages bằng pip

## Ví Dụ Sử Dụng Thực Tế

```bash
# Kiểm tra ảnh từ internet
python demo.py -f downloaded_image.jpg -m weights/blur_jpg_prob0.5.pth --use_cpu

# Đánh giá toàn bộ thư mục ảnh của bạn
python demo_dir.py -d my_images_folder -m weights/blur_jpg_prob0.5.pth --use_cpu
```

---

**Liên hệ hỗ trợ:** Nếu có thắc mắc, hãy tham khảo file README.md gốc hoặc trang web chính thức của dự án.