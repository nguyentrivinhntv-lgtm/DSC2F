# Phân tích mô hình Enhanced Dual-Stream

Tài liệu tóm tắt và phân tích kiến trúc của mô hình Enhanced Dual-Stream trong repository.

**Files referenced**
- **Mã nguồn chính (SRM + CBAM)**: [networks/enhanced_dual_stream.py](networks/enhanced_dual_stream.py#L1)
- **Mã nguồn thay thế / biến thể (Res-like + SE)**: [networks/dual_stream_enhanced.py](networks/dual_stream_enhanced.py#L1)

**Tổng Quan**
- **Mục tiêu**: Phát hiện ảnh AI-generated bằng cách kết hợp thông tin không gian (RGB) và tần số (FFT/magnitude).
- **Ý tưởng chính**: Hai luồng (spatial, frequency) tách rời để trích xuất đặc trưng chuyên biệt, sau đó dùng cơ chế attention (CBAM / cross-modal) để tương tác và hợp nhất.

**Thành phần chính**
- **SRMFilterLayer**: (chỉ có trong `enhanced_dual_stream.py`) một lớp convolution không trainable với 30 bộ lọc high-pass 5x5 (shape weight: (30, 3, 5, 5)). Dùng để bắt các artifact vi mô do quá trình tổng hợp ảnh tạo ra.
- **CBAM (Channel + Spatial Attention)**: module attention tuần tự áp dụng attention theo channel rồi spatial, dùng trong cả hai file để tăng trọng số cho những vùng/kênh quan trọng.
- **EnhancedSpatialStream / EnhancedResidualBlock**:
  - `enhanced_dual_stream.py`: kết hợp `conv1_rgb (3->32)` + `conv1_srm (30->32)`, ghép 2 luồng ban đầu → BN → block convolution sâu hơn (out_features = 512). Trả về vector đặc trưng dạng [B, 512].
  - `dual_stream_enhanced.py`: thiết kế kiểu Res-like với `EnhancedResidualBlock`, SE blocks và CBAM; đầu vào RGB, kết thúc bằng AdaptiveAvgPool → vector [B, 512].
- **EnhancedFrequencyStream / Multi-scale FFT**:
  - `enhanced_dual_stream.py`: dùng conv xử lý trực tiếp magnitude FFT (1 channel) với multiple kernel sizes và branch fusion → out_features = 512.
  - `dual_stream_enhanced.py`: tách low/mid/high frequency paths (kích thước kernel khác nhau), ghép lại rồi nhiều tầng conv+CBAM → out_features = 512.
- **CrossModalAttention**:
  - `enhanced_dual_stream.py`: thực hiện attention bằng phép chiếu tuyến tính (`query/key/value`) và softmax, áp dụng luồng frequency vào spatial (trong code hiện tại spatial được thêm phần output attention).
  - `dual_stream_enhanced.py`: phiên bản đơn giản hóa với các phép chiếu hai chiều và sigmoid-based attention, tạo cả `spatial_enhanced` và `freq_enhanced`.
- **Classifier / Fusion**: cả hai model nối 2 vector (512 + 512 = 1024) và đưa vào MLP/sequence các Linear + BN + ReLU + Dropout để phân loại (num_classes mặc định = 1).

**Dữ liệu đầu vào & tiền xử lý**
- **RGB input**: tensor dạng `[B, 3, H, W]` (ví dụ thử nghiệm dùng 32x32 trong script test). Cần normalize theo pipeline training dự định của bạn.
- **FFT / frequency input**: tensor dạng `[B, 1, H, W]` — magnitude của FFT (log1p + chuẩn hóa). Sử dụng `compute_multiscale_fft` trong [networks/dual_stream_enhanced.py](networks/dual_stream_enhanced.py#L240) nếu muốn tương thích.

**Một số chi tiết quan trọng**
- **SRM là không trainable**: trong `SRMFilterLayer`, các trọng số SRM được gán và `requires_grad=False` — đây là thiết kế cố ý để duy trì bộ lọc high-pass cố định.
- **Kích thước feature**: mỗi luồng trả về vector 512 chiều; sau khi cross-attention và concat, classifier nhận 1024 chiều.
- **Attention khác nhau giữa hai file**: hai file cung cấp hai cách cài đặt attention khác nhau — hãy chọn phiên bản phù hợp với mục tiêu (chú trọng artifact vi mô → dùng SRM; chú trọng backbone mạnh hơn → dùng Res-like + SE).

**Ví dụ sử dụng nhanh**
```python
from networks.enhanced_dual_stream import EnhancedDualStreamCNN
model = EnhancedDualStreamCNN(num_classes=1)

# rgb_tensor: [B, 3, H, W]
# fft_tensor: [B, 1, H, W] — tạo bằng compute_multiscale_fft hoặc pipeline của bạn
out = model(rgb_tensor, fft_tensor)
```

**Gợi ý & đề xuất tiếp theo**
- Thêm hàm visualize attention / attention maps để debug (cả code đã có placeholder `get_attention_maps`).
- Kiểm tra chuẩn hóa đầu vào (mean/std) và consistency giữa training/inference cho FFT/magnitude.
- Nếu muốn học bộ lọc SRM, có thể thay `requires_grad=False` thành `True` và khởi tạo từ bộ lọc SRM như warm-start.
- Cân nhắc export một phiên bản ONNX/ONNX-RT cho inference nhẹ trên server.

---

File này được sinh tự động — sửa nhanh nếu bạn muốn bổ sung hình minh họa, biểu đồ luồng dữ liệu, hoặc số liệu tham chiếu (parameter counts, FLOPs).
