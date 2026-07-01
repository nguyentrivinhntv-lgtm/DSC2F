import os
import sys

# Ensure we can import app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.models.base_db import create_page

pages = [
    {
        "slug": "huong-dan-su-dung",
        "title": "Hướng dẫn sử dụng",
        "content": "<h2>Hướng dẫn sử dụng hệ thống</h2><p>Hệ thống nhận diện deepfake qua các bước đơn giản sau:</p><ol><li>Đăng nhập vào hệ thống.</li><li>Tải ảnh cần kiểm tra lên.</li><li>Bấm nút <strong>Phân tích</strong> để xem kết quả.</li></ol>",
    },
    {
        "slug": "chinh-sach-bao-mat",
        "title": "Chính sách bảo mật",
        "content": "<h2>Chính sách bảo mật</h2><p>Chúng tôi cam kết bảo mật thông tin cá nhân của người dùng. Hình ảnh được tải lên chỉ được sử dụng cho mục đích phân tích và không được lưu trữ vĩnh viễn hoặc chia sẻ với bất kỳ bên thứ ba nào.</p>",
    },
    {
        "slug": "dieu-khoan-dich-vu",
        "title": "Điều khoản dịch vụ",
        "content": "<h2>Điều khoản dịch vụ</h2><p>Người dùng cam kết sử dụng hệ thống vào mục đích hợp pháp. Chúng tôi không chịu trách nhiệm với bất kỳ hậu quả nào phát sinh từ việc lạm dụng kết quả nhận diện của hệ thống.</p>",
    }
]

def add_pages():
    print("Starting adding default pages...")
    for p in pages:
        try:
            create_page(p['slug'], p['title'], p['content'], is_active=1)
            print(f"Created page: {p['slug']}")
        except ValueError as e:
            print(f"Skipped page (already exists): {p['slug']}")
        except Exception as e:
            print(f"Error creating {p['slug']}: {e}")
    print("Done!")

if __name__ == "__main__":
    add_pages()
