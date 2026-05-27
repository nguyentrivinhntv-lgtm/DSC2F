# Thông tin chi tiết về mô hình ResNet-18

## 1. Tổng quan về ResNet
**ResNet (Residual Network)** là một mạng nơ-ron tích chập (CNN) được nhóm nghiên cứu của Microsoft (Kaiming He và cộng sự) giới thiệu vào năm 2015. Đây là một bước đột phá lớn trong lĩnh vực Computer Vision vì nó giải quyết được vấn đề "suy thoái" (degradation problem) khi mạng trở nên quá sâu. Trước ResNet, khi số lượng lớp (layers) tăng lên, độ chính xác của mạng ban đầu tăng nhưng sau đó bị bão hòa và thậm chí giảm dần (không phải do overfitting mà do khó tối ưu hóa/gradient vanishing).

**ResNet-18** là một biến thể của ResNet với độ sâu là 18 lớp có trọng số (bao gồm các lớp Convolution và Fully Connected). Nó nhỏ gọn và rất phù hợp để làm mạng phân loại hình ảnh cơ bản hoặc trích xuất đặc trưng (feature extractor).

---

## 2. Thuật toán cốt lõi (Residual Learning / Skip Connection)

Ý tưởng cốt lõi của ResNet là sử dụng các kết nối tắt (**Skip Connections** hay **Shortcut Connections**).

Trong một mạng thông thường, mỗi layer cố gắng học một hàm ánh xạ $H(x)$ trực tiếp. Trong ResNet, thay vì học trực tiếp $H(x)$, mạng được thiết kế để học một hàm thặng dư (residual function) $F(x) = H(x) - x$. 
Do đó, ánh xạ thực tế mạng cần nội suy trở thành:
$$ H(x) = F(x) + x $$

**Cách hoạt động của Skip Connection:**
- Đầu vào $x$ của khối (block) được bỏ qua một vài lớp biến đổi (thường là 2 lớp tích chập với ResNet-18) và cộng trực tiếp vào đầu ra của các lớp đó.
- Nếu các lớp ẩn bên trong không học được đặc trưng nào hữu ích (tức $F(x) \approx 0$), mạng vẫn giữ được thông tin nguyên bản từ $x$ nhờ phép cộng $H(x) = x$.
- Điều này giúp luồng gradient truyền ngược (backpropagation) qua các lớp dễ dàng hơn rất nhiều, làm giảm thiểu hiện tượng Vanishing Gradient, cho phép đào tạo các mạng rất sâu lên tới hàng trăm hoặc hàng ngàn lớp.

---

## 3. Kiến trúc tổng quan của ResNet-18

Mô hình ResNet-18 bao gồm 5 phần chính (gọi là conv1 đến conv5) và kết thúc bằng lớp Average Pooling và Fully Connected layer. Nó sử dụng khối xây dựng cơ bản là **BasicBlock** (chứa 2 lớp chập 3x3).

**Cấu trúc chi tiết của ResNet-18 cho ảnh đầu vào kích thước (224x224x3):**

1. **Lớp chập đầu tiên (conv1):**
   - 1 lớp Convolution 7x7, 64 filters, độ sải (stride) = 2. Phép padding này giảm kích thước ảnh xuống còn 112x112.
   - Tiếp sau là lớp Batch Normalization và hàm kích hoạt ReLU.
   - 1 lớp Max Pooling 3x3 với stride = 2. Kích thước Feature Map giảm xuống còn 56x56.

2. **Các khối tàn dư (Residual Blocks):**
   Sau conv1, mạng đi qua 4 giai đoạn, mỗi giai đoạn chứa các BasicBlock. Mỗi BasicBlock gồm 2 lớp tích chập 3x3. Cụ thể cho ResNet-18:
   - **Giai đoạn 1 (conv2_x):** Gồm 2 BasicBlock. Kích thước output: 56x56, số kênh: 64.
   - **Giai đoạn 2 (conv3_x):** Gồm 2 BasicBlock. Kênh tăng từ 64 lên 128, kích thước giảm xuống 28x28 (do stride=2 ở khối đầu tiên).
   - **Giai đoạn 3 (conv4_x):** Gồm 2 BasicBlock. Kênh tăng từ 128 lên 256, kích thước giảm xuống 14x14.
   - **Giai đoạn 4 (conv5_x):** Gồm 2 BasicBlock. Kênh tăng từ 256 lên 512, kích thước giảm xuống 7x7.

   *(Tổng cộng có: $2$ khối/giai đoạn $\times 4$ giai đoạn $\times 2$ lớp chập/khối = 16 lớp chập trong các khối residual).*

3. **Phân loại cuối (Classification):**
   - **Global Average Pooling:** Tính trung bình của từng kênh 7x7 để chuyển từ tensor kích thước $7 \times 7 \times 512$ thành một vector 1D có kích thước $512$.
   - **Lớp Fully Connected (FC):** Số lượng nơ-ron bằng số lượng class cần phân loại (trong bài toán ImageNet là 1000).

*Lưu ý: $1$ (conv đầu) + $16$ (trong các khối res) + $1$ (fully connected) = 18 lớp (Nên được gọi là ResNet-18).*

---

## 4. Đặc điểm nổi bật của cấu trúc theo implementation (Ví dụ: `resnet.py`)

Dựa vào mã nguồn mạng ResNet phổ biến mà bạn đang sử dụng:
- Các lớp Convolution `conv3x3` đều sử dụng tính năng bỏ qua độ lệch (`bias=False`), vì tác dụng của bias đã được thay thế bởi lớp **Batch Normalization** ngay phía sau.
- Hàm kích hoạt sử dụng là **ReLU**.
- Lớp **Downsample**: Tại phần đầu của các khối `conv3_x`, `conv4_x`, `conv5_x` khi số lượng kênh (chanel) tăng lên và chiều không gian (giảm d) bị thay đổi (stride=2), đầu vào $x$ từ nhánh skip connection phải đi qua một lớp tích chập `1x1` (kết hợp với Batch Norm) với stride = 2. Điều này để đảm bảo cùng kích thước và số kênh trước khi thực hiện phép cộng lại ($F(x) + x$).
