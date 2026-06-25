# Hướng dẫn Cài đặt & Chạy Môi trường Web (CNN Detection)

Tài liệu này hướng dẫn chi tiết cách cài đặt môi trường, cấu hình và chạy hệ thống Web **CNN Detection**. Hệ thống web bao gồm 2 phần: **Backend** (API xử lý dữ liệu và AI) và **Frontend** (Giao diện người dùng).

---

## 1. Cài đặt Môi trường Backend (API & AI)

Backend chịu trách nhiệm nhận ảnh, chạy các mô hình AI nhận diện Deepfake (CNN) và giao tiếp với cơ sở dữ liệu.

### 1.1. Yêu cầu hệ thống
- **Python:** Phiên bản 3.9 hoặc 3.10 (Khuyến nghị 3.10).
- **Trình quản lý package:** `pip`.
- **Cơ sở dữ liệu:** MySQL (Sử dụng **Laragon** để chạy máy chủ MySQL cục bộ).

### 1.2. Các bước cài đặt

**Bước 1: Khởi động MySQL qua Laragon**
1. Mở phần mềm **Laragon**.
2. Nhấn nút **Start All** (Đảm bảo dòng chữ báo hiệu MySQL đang chạy ở cổng 3306).
3. Mở trình duyệt, truy cập vào `http://localhost/phpmyadmin` (hoặc nhấn nút **Database** trên giao diện Laragon để mở HeidiSQL/phpMyAdmin tùy cấu hình).
4. Tạo một cơ sở dữ liệu (database) mới có tên là: `cnn_detection`.
*(Hoặc bạn có thể để Backend tự động tạo nếu chạy đúng cấu hình).*

**Bước 2: Di chuyển vào thư mục Backend**
Mở Terminal / Command Prompt và gõ:
```bash
cd d:\khoaluanthuctap\DSC2F\CNNDetection\api_base
```

**Bước 3: Tạo môi trường ảo (Khuyến nghị)**
```bash
python -m venv venv
venv\Scripts\activate   # (Trên Windows)
# source venv/bin/activate  (Trên Mac/Linux)
```

**Bước 4: Cài đặt các thư viện (Dependencies)**
```bash
pip install -r requirements.txt
```
*(Lưu ý: Quá trình cài đặt TensorFlow và PyTorch có thể mất vài phút).*

**Bước 5: Cấu hình File `.env`**
Trong thư mục `api_base`, tạo file `.env` (hoặc sửa file hiện có) với nội dung:
```env
# URL Kết nối Database MySQL
DATABASE_URL=mysql+pymysql://root:@127.0.0.1:3306/cnn_detection

# Secret Key (dùng để mã hóa Token bảo mật)
SECRET_KEY=mot_chuoi_bi_mat_bat_ky_cua_ban
```

### 1.3. Khởi chạy Backend

Sau khi cài đặt xong, gõ lệnh sau để khởi chạy máy chủ:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Nếu thấy dòng `Application startup complete.`, Backend đã chạy thành công.
- Các API sẽ hoạt động tại địa chỉ: **http://localhost:8000**
- Trang tài liệu API (Swagger UI): **http://localhost:8000/docs**

---

## 2. Cài đặt Môi trường Frontend (Giao diện Web)

Phần giao diện Web sử dụng kiến trúc thuần (Vanilla JS, HTML, CSS), không cần build (như React/Vue) nên việc chạy rất nhẹ nhàng và đơn giản.

### 2.1. Yêu cầu hệ thống
- Bạn chỉ cần một công cụ để chạy Live Server (máy chủ tĩnh cục bộ).
- Khuyến nghị sử dụng **VS Code** với Extension **Live Server** hoặc dùng Python Server.

### 2.2. Các bước cấu hình & chạy

**Bước 1: Di chuyển vào thư mục Frontend**
Mở một cửa sổ Terminal khác và gõ:
```bash
cd d:\khoaluanthuctap\DSC2F\CNNDetection\frontend
```

**Bước 2: Cấu hình kết nối tới Backend (Nếu cần)**
- Hệ thống Frontend mặc định đọc cấu hình từ file `config-loader.js`.
- File này sẽ tự động gọi tới `http://localhost:8000`. Nếu bạn chạy Backend ở cổng khác, hãy mở file `config-loader.js` và cập nhật lại biến `window.API_BASE_URL`.

**Bước 3: Khởi chạy Web**
Bạn có thể chọn 1 trong 2 cách sau:

*Cách 1: Dùng tiện ích Live Server của VS Code (Khuyến nghị nhất)*
1. Mở thư mục `frontend` bằng phần mềm VS Code.
2. Tìm file `index.html`.
3. Click chuột phải vào file `index.html` -> Chọn **"Open with Live Server"**.
4. Trình duyệt sẽ tự động bật và trang web sẽ load ở địa chỉ: `http://127.0.0.1:5500`.

*Cách 2: Dùng Python HTTP Server*
Nếu bạn đã cài sẵn Python, trong thư mục `frontend`, gõ lệnh:
```bash
python -m http.server 8080
```
Sau đó tự mở trình duyệt và truy cập: **http://localhost:8080**

---

## 3. Cách sử dụng tính năng cơ bản sau khi cài đặt

1. **Truy cập Web:** Mở `http://localhost:8080` (hoặc `5500`), bạn sẽ thấy Trang chủ Giới thiệu.
2. **Đăng nhập:** Bấm vào "User Dashboard" để vào màn hình chính. Có thể đăng ký tài khoản mới hoặc đăng nhập bằng Google.
3. **Admin Panel:**
   - Hệ thống tự tạo tài khoản admin mặc định: Username: `admin`, Password: `admin_password`.
   - Bấm vào "Admin Dashboard" từ trang chủ hoặc vào thẳng file `admin.html` và đăng nhập bằng tài khoản admin để quản trị hệ thống, thêm sửa các trang (CMS), duyệt yêu cầu nạp tiền, xóa tài khoản...
4. **Quét ảnh (Scan):** Tải lên các file ảnh chân dung để AI phân tích. Quá trình phân tích sẽ gửi ảnh về Backend `http://localhost:8000` để chạy model CNN và trả về kết quả Deepfake/Real.

Chúc bạn cài đặt thành công!
