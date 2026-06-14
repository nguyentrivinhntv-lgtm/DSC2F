# Hệ Thống CNN Detection (Web, Android, iOS)

Tài liệu này cung cấp toàn bộ thông tin về kiến trúc, chức năng và cách cài đặt/khởi chạy cho nền tảng ứng dụng **CNN Detection**, bao gồm 3 phần chính: **Giao diện Web**, **Ứng dụng Android**, và **Ứng dụng iOS**.

---

## 1. Giao Diện Web (Frontend)

Phần giao diện Web là nơi cung cấp trải nghiệm thao tác trên trình duyệt, có thiết kế đáp ứng (responsive) thích hợp cho cả PC và Mobile.

### Thông tin chung
- **Thư mục:** `frontend/`
- **Công nghệ sử dụng:** HTML5, CSS3, JavaScript (Vanilla JS), không sử dụng Framework phức tạp để tối ưu tốc độ.
- **Các thành phần chính:**
  - `index.html`: Trang đích, giới thiệu và đăng nhập.
  - `app.html` & `app.js`: Màn hình chính xử lý logic nhận diện ảnh CNN (Deepfake/Real).
  - `admin.html` & `admin.js`: Bảng điều khiển dành cho Quản trị viên quản lý lịch sử nhận diện và người dùng.
  - `mobile_login.html`: Trang hỗ trợ callback khi đăng nhập Google trên Mobile.
  - `i18n.js`: Hỗ trợ đa ngôn ngữ.

### Cách chạy môi trường Web
Để chạy Web, bạn cần chạy một local server để phục vụ các file tĩnh.
1. Mở Terminal và di chuyển vào thư mục `frontend`:
   ```bash
   cd d:\khoaluanthuctap\DSC2F\CNNDetection\frontend
   ```
2. Khởi động Web Server (sử dụng Python):
   ```bash
   python -m http.server 8080
   ```
3. Truy cập vào đường dẫn: **http://localhost:8080**

---

## 2. Ứng Dụng Di Động (Android & iOS)

Ứng dụng di động của dự án được phát triển bằng **Flutter**, sử dụng cơ chế nhúng giao diện Web (WebView) kết hợp với các tính năng Native của thiết bị di động để mang lại trải nghiệm tối ưu.

### Thông tin chung
- **Thư mục:** `app_web_view/`
- **Ngôn ngữ/Framework:** Dart / Flutter
- **Cơ chế hoạt động:**
  - Ứng dụng khởi chạy một `WebViewController` tải toàn bộ giao diện từ thư mục `frontend` (được host trên server - theo cấu hình trong `AppConfig.webBaseUrl`).
  - Giao tiếp hai chiều với Web bằng `JavaScriptChannel` mang tên `FlutterBridge`.
  - Khi người dùng đăng nhập bằng Google, App không mở popup trong WebView (bị Google chặn vì lý do bảo mật), mà mở trình duyệt ngoài hệ thống (`Chrome Custom Tabs`) sử dụng `flutter_web_auth_2`. Sau khi xác thực, Token được gửi về App, lưu trữ an toàn bằng `shared_preferences` và đẩy vào WebView.
  - Có cơ chế chặn người dùng thoát nhầm ứng dụng bằng cách ưu tiên quay lại trang web (Go Back) thay vì thoát app hoàn toàn.

### Cách Build và Chạy ứng dụng

#### **Yêu cầu môi trường:**
- Cài đặt **Flutter SDK** (Version 3.10.x trở lên).
- **Android:** Cài đặt Android Studio.
- **iOS:** Cần thiết bị máy Mac cài đặt sẵn Xcode và CocoaPods.

#### **Cài đặt thư viện:**
Di chuyển vào thư mục dự án và tải thư viện:
```bash
cd app_web_view
flutter pub get
```

#### **Đối với Android:**
- Để chạy trực tiếp lên máy ảo/máy thật Android:
  ```bash
  flutter run
  ```
- Để xuất file cài đặt APK:
  ```bash
  flutter build apk
  ```
  *(Lưu ý: Bạn có thể tìm thấy file APK đã được build sẵn ở thư mục gốc với tên `CNN_Detection.apk`)*

#### **Đối với iOS:**
- Cài đặt Pods cho iOS:
  ```bash
  cd ios
  pod install
  cd ..
  ```
- Build và chạy ứng dụng lên máy ảo Simulator hoặc iPhone thật:
  ```bash
  flutter run -d ios
  ```
- Xuất file cài đặt IPA (yêu cầu cấu hình Provisioning Profile trong Xcode):
  ```bash
  flutter build ipa
  ```

---

## 3. Hệ Thống Backend (API Server)

Đây là máy chủ xử lý logic cốt lõi, tích hợp các model AI và tương tác với cơ sở dữ liệu. Backend phục vụ dữ liệu đồng nhất cho cả nền tảng Web, Android và iOS.

- **Thư mục:** `api_base/`
- **Công nghệ:** Python 3.10+, **FastAPI** (Uvicorn server)
- **Cơ sở dữ liệu:** **MySQL** (kết nối qua SQLAlchemy/PyMySQL)
- **Cách chạy:**
  1. Khởi động MySQL Server (Cấu hình mặc định trong `.env`: `mysql://root:@127.0.0.1:3307/cnn_detection`).
  2. Mở Terminal, di chuyển vào `api_base`.
  3. Cài đặt dependencies (nếu chưa có): `pip install -r requirements.txt`.
  4. Khởi động Server:
     ```bash
     python run_api.py --reload
     ```
  5. Server sẽ chạy mặc định tại: `http://0.0.0.0:8000`

---

## 4. Công Thức Chuyên Sâu: Cấu Trúc & Công Nghệ (Technical Stack)

Hệ thống được thiết kế theo mô hình **Client - Server** tách biệt (Decoupled Architecture), giao tiếp hoàn toàn qua **RESTful API** và bảo mật bằng **JWT Token**.

### 4.1. Cấu trúc Giao Diện (Frontend Architecture)
- **Mô hình kiến trúc:** Single-Page-Like Application sử dụng DOM Manipulation thuần túy.
- **Công nghệ lõi:**
  - **HTML5 & CSS3:** Xây dựng layout, UI/UX (File `style.css` và `admin.css`). Sử dụng biến CSS (CSS Variables) để quản lý màu sắc và light/dark theme.
  - **Vanilla JavaScript (ES6+):** Quản lý trạng thái, routing ảo và xử lý sự kiện (Event Listeners) trực tiếp (File `app.js` và `admin.js`). Không sử dụng Virtual DOM (như React/Vue) để giảm tải tài nguyên trình duyệt.
  - **Bảo mật trạng thái (State Security):** Token JWT được lưu trong `localStorage`. Tự động đính kèm vào HTTP Header `Authorization: Bearer <token>` bằng Fetch API khi gọi tới Backend.
  - **Đa ngôn ngữ (i18n):** Tự xây dựng cơ chế quản lý file ngôn ngữ dạng JSON trong `i18n.js` (hỗ trợ Tiếng Việt & Tiếng Anh).

### 4.2. Cấu trúc Máy Chủ (Backend Architecture & AI)
- **Mô hình kiến trúc:** **FastAPI** ASGI Framework. Cấu trúc Router-Controller-Service-Model:
  - `routers/`: Định nghĩa các API endpoints (Controllers).
  - `models/`: Định nghĩa Schema dữ liệu và tương tác cơ sở dữ liệu (ORM).
  - `services/`: Xử lý business logic, tích hợp AI.
  - `security/`: Phân tích và mã hóa token JWT (sử dụng thư viện `python-jose` và `passlib/bcrypt`).
- **Lõi AI & Machine Learning:**
  - Sử dụng **PyTorch** (`torch`, `torchvision`) để load các pre-trained models.
  - Hỗ trợ 4 kiến trúc Deep Learning chính để nhận diện ảnh: **ResNet50**, **DualStreamCNN**, **DualStreamCNNEnhanced**, **DualStreamResNet**.
  - Logic tải trọng lượng (weights) động: Nếu server chưa có file `.pth` hoặc `.bin`, hệ thống tự động tải từ Google Drive qua hàm khởi tạo `download_weights_if_needed()`.

### 4.3. Cấu trúc API Endpoints (RESTful API)
Các Endpoint chính giao tiếp giữa Frontend/Mobile và Backend (Xem chi tiết tại `http://localhost:8000/docs`):

**Nhóm Xác thực (Authentication) - `routers/auth.py`:**
- `POST /auth/register`: Đăng ký tài khoản (mã hóa mật khẩu bằng bcrypt).
- `POST /auth/login`: Đăng nhập cơ bản, trả về `access_token` JWT.
- `POST /auth/google`: Nhận Google Token ID từ trình duyệt/Mobile (qua OAuth2) để cấp phát JWT nội bộ.

**Nhóm Nhận diện AI (Prediction) - `routers/file_upload.py`:**
- `POST /predict`: Upload một ảnh dạng multipart/form-data. Trả về kết quả Real/Fake kèm phần trăm độ tin cậy. Yêu cầu Bearer Token.
- `POST /predict/batch`: Tải lên nhiều ảnh cùng lúc, sử dụng Batch Processing của PyTorch để tăng tốc độ phân tích.

**Nhóm Dữ liệu người dùng - `routers/history.py` & `routers/base.py`:**
- `GET /history`: Lấy lịch sử quét của người dùng.
- `GET /models`: Lấy danh sách các Model AI đang sẵn sàng hoạt động.

**Nhóm Thanh toán (Payment) - `routers/payment.py`:**
- `POST /payment/create`: Khởi tạo luồng thanh toán (Tích hợp cổng VNPAY/Momo).
- `GET /payment/return`: Xử lý Callback IPN từ cổng thanh toán.

---

## 5. Tổng kết Lồng Ghép (Tích Hợp Hệ Thống)
1. **Khởi động Database (MySQL port 3307)** $\rightarrow$ **Bật API Backend** (`python run_api.py`).
2. **Khởi động Giao diện Web** (`python -m http.server 8080` trong thư mục frontend).
3. Giao diện Frontend tự động mapping API call dựa trên config ở `config-loader.js` (mặc định gọi về `http://127.0.0.1:8000`).
4. Nếu sử dụng App di động (Flutter WebView), cấu hình IP host của Web & API trong file `app_web_view/lib/config.dart` trỏ về IP mạng LAN của máy tính bạn (ví dụ: `http://192.168.1.15:8080`) sau đó Build ra thiết bị thật Android/iOS.
