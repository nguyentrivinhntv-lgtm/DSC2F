# Thông tin chi tiết về mô hình Dual-Stream ResNet

## 1. Tổng quan về Dual-Stream CNN
**Dual-Stream ResNet** là một mô hình mạng nơ-ron đa luồng (multi-stream), được thiết kế để phân tích ảnh dựa trên **Nhiều miền dữ liệu (Multi-Domain)**. Thay vì chỉ phân tích điểm ảnh (pixel) thông thường, mô hình tận dụng cả khía cạnh Không gian (Spatial) và Tần số (Frequency/FFT) của ảnh để nâng cao hiệu quả phân loại, đặc biệt là trong các bài toán phát hiện ảnh giả mạo (Deepfake Detection) hoặc phát hiện chi tiết bất thường ẩn sâu trong ảnh.

Ý tưởng cốt lõi là các thao tác sinh ảnh giả mạo (GANs, Diffusion Models) thường để lại các dấu vết bất thường ở miền tần số cao (artifacts dải tần), thứ khó có thể nhận ra bằng luồng Spatial RGB thông thường.

---

## 2. Thuật toán và Kiến trúc tổng quan

Mô hình lấy ý tưởng chia luồng làm 2 bộ phân tách đặc trưng độc lập (Feature Extractors), sau đó kết hợp đặc trưng lại ở các lớp học sâu cuối (Late-Fusion). Tổng quan chi tiết 3 thành phần chính của `DualStreamResNet`:

### A. Luồng Không gian (Spatial Stream - ResNet-18)
- **Đầu vào:** Hình ảnh tĩnh định dạng RGB.
- **Backbone sử dụng:** Mô hình **ResNet-18 được Pretrain trên ImageNet**.
- **Thuật toán:** Luồng này tập trung vào các đặc trưng trừu tượng như màu sắc, hình khối, bố cục không gian, texture từ ảnh gốc. Transfer learning giúp mô hình kế thừa khả năng nhận dạng mạnh mẽ.
- **Công thức Toán học (Khối Residual):** Trọng tâm của ResNet là việc học hàm thặng dư thông qua kết nối tắt (Skip Connection):
  $$ H(x) = F(x, \{W_i\}) + x $$
  Trong đó $x$ là input, $F(x, \{W_i\})$ là output của các lớp tích chập nội bộ, và $H(x)$ là kết quả nội suy thu được.
- **Chi tiết kỹ thuật (Đóng băng trọng số):** Các layer ban đầu bao gồm `conv1`, `bn1`, và khối `layer1` được đóng băng (`freeze_early=True`). Bước đi này tránh hiện tượng phá vỡ các bộ lọc trích xuất đặc trưng cơ bản (cạnh, góc, kết cấu sáng tối) đã được ImageNet tối ưu, chỉ cho phép các khối layer sâu (`layer2`, `layer3`, `layer4`) Fine-tuning cho bài toán cụ thể.
- **Đầu ra luồng:** Sau khi đi qua Global Average Pooling, luồng Spatial cung cấp một vector đặc trưng có số chiều là **512**. Ký hiệu là $V_{spatial}$.

### B. Luồng Tần số (Frequency Stream - Phổ FFT)
- **Đầu vào:** Phổ tần số 2D (Frequency Spectrum) thông qua biến đổi Fast Fourier Transform (FFT).
- **Thuật toán (Tiền xử lý & Công thức Toán học):** 
  Thay vì để nguyên RGB, luồng này chiết xuất đặc trưng tần số theo các bước tính toán sau:
  1. **Grayscale Conversion:** Chuyển ảnh màu sang xám để tính toán phổ 2D:
     $$ Y(x,y) = 0.299 \cdot R(x,y) + 0.587 \cdot G(x,y) + 0.114 \cdot B(x,y) $$
  2. **Fast Fourier Transform (FFT2):** Biến đổi ảnh tĩnh xám $Y$ có kích thước $M \times N$ sang miền tần số $\mathcal{F}$:
     $$ \mathcal{F}(u, v) = \sum_{m=0}^{M-1} \sum_{n=0}^{N-1} Y(m, n) \cdot e^{-j2\pi \left(\frac{u \cdot m}{M} + \frac{v \cdot n}{N} \right)} $$
  3. **Magnitude & Gifting Logarit:** Tính toán biên độ (Magnitude) và làm mượt nó bằng hàm Logarit do cường độ phổ FFT chênh lệch rất lớn. Hàm được cộng thêm `1p` để tránh $\log(0)$ (theo `torch.log1p`):
     $$ S(u,v) = \ln(1 + |\mathcal{F}_{shift}(u,v)|) $$
  4. **Chuẩn hóa (Min-Max Scaling):** Đưa dữ liệu mượt mà vùng $[0, 1]$ cho mạng Mạng nơ rôn, với $eps = 10^{-8}$ để tránh chia nhầm cho $0$:
     $$ S_{norm} = \frac{S(u,v) - S_{min}}{S_{max} - S_{min} + \epsilon} $$
- **Backbone sử dụng:** Bộ trích xuất dạng Lightweight CNN gồm 4 khối thuần tự (Không sử dụng kết nối tắt ResNet):
  - **Block 1, 2, 3:** Mỗi block chứa 2 lớp Tích chập 3x3 (kết hợp Batch Norm, ReLU) rèn luyện để tìm các nhiễu sóng (frequency artifacts), theo sau là hàm Pooling giảm số chiều. Kích thước số kênh trải qua: `3 -> 64 -> 128 -> 256`.
  - **Block 4:** Cuối cùng một lớp Conv tăng kênh lên `512` kết hợp `AdaptiveAvgPool2d((1,1))`.
- **Đầu ra luồng:** Vector đặc trưng thứ hai về sóng và tần số, số chiều là **512**. Ký hiệu là $V_{freq}$.

### C. Khối kết hợp và Phân loại (Fusion Layer & Classifier)
Thuật toán Fusion được thiết kế dạng Linear Block học sự đối chiếu song song.

1. **Khối nối (Concatenation):**
   Gộp (Nối) kết quả hai luồng 512 + 512 lại thành tensor có số chiều **1024**. Lúc này Model đang nắm giữ cả kiến thức bề nổi (pixel) và kiến thức cấu trúc vô hình (spectrum).
   $$ V_{combined} = [V_{spatial} \oplus V_{freq}] \quad (Dim: 1 \times 1024)$$
   
2. **Khối Fusion Layer:**
   Cho tensor $V_{combined}$ đi ngang qua Mạng Feed-Forward (Multilayer Perceptron - MLP) có hàm kích hoạt ReLU $(\max(0, x))$ và Dropout $\sim \text{Bernoulli}(p=0.5)$ giảm thiểu Overfitting:
   - Linear Transformation (1024 $\to$ 512): $Z_1 = \text{Drop}(\text{ReLU}(\text{BN}(W_1 \cdot V_{combined} + b_1)))$
   - Linear Transformation (512 $\to$ 256): $Z_2 = \text{Drop}(\text{ReLU}(\text{BN}(W_2 \cdot Z_1 + b_2)))$

3. **Lớp Classifier:**
   Đảm đương một lớp Linear đơn (256 $\to$ `num_classes`). Output dạng mảng thô (Logits).
   $$ \hat{y} = W_3 \cdot Z_2 + b_3 $$
   Sử dụng để tính lỗi bằng hàm Binary Cross Entropy (Trong mô hình số lớp đầu ra là 1):
   $$ \mathcal{L}_{BCE} = -[y \cdot \log(\sigma(\hat{y})) + (1 - y) \cdot \log(1 - \sigma(\hat{y}))] $$
   *(với $\sigma$ là hàm Sigmoid).*

---

## 3. Tóm lược cơ chế sức mạnh
Sự giao thoa trong Dual-Stream ResNet tạo nên "sự thông thái mảng miếng". Trong trường hợp ảnh Deepfake cực kỹ lưỡng, màu sắc & mặt mài hoàn toàn lọt lỗ kim Spatial của ResNet. Tuy nhiên, luồng biến đổi Fourier sẽ soi ra ngay lập tức cái gọi là "tần số nhiễu dị biến" (grid artifacts) trong quá trình máy móc Deconvolution hay Upsampling hình ảnh tạo ra. Cân bằng cả hai đại lượng, Dual-Stream đưa ra kết luận cực kỳ chính xác.