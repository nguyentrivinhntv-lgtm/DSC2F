# Hướng Dẫn Chạy Ứng Dụng CNN Detection (Web App)

Để chạy ứng dụng CNN Detection hoàn chỉnh bao gồm cả Frontend và Backend, bạn hãy làm theo các bước dưới đây.

## 1. Khởi động Cơ Sở Dữ Liệu (MySQL)

Ứng dụng yêu cầu MySQL để lưu trữ thông tin người dùng và lịch sử nhận diện.

- Mở phần mềm quản lý MySQL của bạn (VD: XAMPP, MySQL Workbench, hoặc Docker).
- Khởi động MySQL Server.
- **Lưu ý:** Theo cấu hình hiện tại trong file `api_base/.env`, database đang được cấu hình kết nối tới port `3307`: `mysql://root:@127.0.0.1:3307/cnn_detection`. Hãy đảm bảo MySQL của bạn đang chạy ở port này hoặc sửa lại file `.env` cho phù hợp với port thực tế của bạn (thường là `3306`).

---

## 2. Khởi động Backend (API Server)

API Server xử lý logic nhận diện ảnh và tương tác với Database.

1. Mở một cửa sổ Terminal (hoặc Command Prompt / PowerShell) mới.
2. Di chuyển vào thư mục `api_base`:
   ```bash
   cd d:\khoaluanthuctap\CNN\CNNDetection\api_base
   ```
3. Chạy lệnh khởi động server:
   ```bash
   python run_api.py --reload
   ```
4. Nếu thành công, Terminal sẽ hiển thị server đang chạy ở địa chỉ `http://0.0.0.0:8000`.

---

## 3. Khởi động Frontend (Giao Diện Web)

Frontend là giao diện để bạn thao tác trực tiếp trên trình duyệt.

1. Mở một cửa sổ Terminal thứ hai.
2. Di chuyển vào thư mục `frontend`:
   ```bash
   cd d:\khoaluanthuctap\CNN\CNNDetection\frontend
   ```
3. Chạy lệnh khởi động Web Server:
   ```bash
   python -m http.server 8080
   ```
4. Mở trình duyệt web của bạn (Chrome, Edge, Firefox, ...) và truy cập vào đường dẫn sau:
   👉 **[http://localhost:8080/](http://localhost:8080/)**

---

## Các Lỗi Thường Gặp

- **Backend bị tắt đột ngột (Crash):** Nếu chạy `run_api.py` mà báo lỗi `pymysql.err.OperationalError` (hoặc actively refused), nguyên nhân là do MySQL chưa được bật hoặc cấu hình port chưa đúng. Hãy kiểm tra lại Bước 1.
- **Frontend gọi API thất bại:** Nếu trang web hiện lỗi Network Error hoặc không đăng nhập được, hãy chắc chắn rằng Backend đang mở và không có lỗi nào hiển thị ở màn hình Terminal chạy Backend.
