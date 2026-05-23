# 🔧 Hướng Dẫn Sửa Lỗi Model Dự Đoán Sai

## 🚨 **Vấn đề:** Model nhận ảnh thật nhưng dự đoán là giả

### ✅ **Đã khắc phục:**

#### 1. **🔍 Debug Information**
- Thêm debug output trong terminal khi phân tích
- Hiển thị chi tiết: `Real: X% | Fake: Y%`
- In ra console classification logic

#### 2. **📊 Cải thiện hiển thị kết quả**
- **Trước**: Chỉ hiện "Xác suất giả"
- **Sau**: Hiện đúng loại xác suất:
  - Nếu Real → "Xác suất thật: X%"
  - Nếu Uncertain → "Độ tin cậy: X%"
  - Nếu Fake → "Xác suất giả: X%"

#### 3. **🔄 Thêm tùy chọn đảo ngược**
- **Checkbox mới**: "🔄 Đảo ngược kết quả (nếu model dự đoán sai)"
- **Vị trí**: Trong sidebar, dưới thông tin model
- **Chức năng**: Đảo ngược output nếu model bị train ngược

### 🎯 **Cách sử dụng:**

#### **Bước 1: Kiểm tra kết quả**
1. Chạy giao diện: `python gui_dark_pro.py`
2. Chọn ảnh thật để test
3. Bấm "🔍 PHÂN TÍCH"
4. Xem **terminal output**:
   ```
   🔍 Model Output: 85.23% fake probability
   📊 Real: 14.8% | Fake: 85.2%
   🎯 Final: FAKE (85.2% confidence)
   ```

#### **Bước 2: Nếu kết quả sai**
1. ✅ **Tick vào checkbox**: "🔄 Đảo ngược kết quả"
2. Phân tích lại ảnh
3. Kiểm tra terminal:
   ```
   🔄 Inverted probability: 14.77%
   📊 Real: 85.2% | Fake: 14.8%
   🎯 Final: REAL (85.2% confidence)
   ```

#### **Bước 3: Xác minh**
- Test với nhiều ảnh thật/giả
- Bật/tắt checkbox để so sánh
- Chọn setting cho kết quả chính xác nhất

### 🧪 **Troubleshooting:**

#### **Nếu vẫn sai:**
1. **Kiểm tra model weights**: Có thể model bị train với label ngược
2. **Test các model khác**: ResNet50, Dual CNN, Dual ResNet
3. **Kiểm tra preprocessing**: Size, normalization có đúng không

#### **Debug thêm:**
- Mở **terminal/console** để xem detailed output
- So sánh kết quả giữa các model
- Test với dataset có label rõ ràng

### 📝 **Ghi chú:**
- Checkbox được lưu trong session
- Debug info luôn hiển thị trong terminal
- Có thể toggle real-time không cần restart

---
**✨ Bây giờ bạn có thể dễ dàng điều chỉnh để model dự đoán chính xác!**