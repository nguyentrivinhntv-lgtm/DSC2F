import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.models.base_db import create_page

pages = [
    {
        "slug": "chinh-sach-quyen-rieng-tu",
        "title": "Chính sách Quyền riêng tư",
        "content": "<h2>Chính sách Quyền riêng tư</h2><p>Nội dung đang được cập nhật. Vui lòng vào trang Admin để chỉnh sửa bài viết bằng trình soạn thảo.</p>",
    },
    {
        "slug": "dieu-khoan-su-dung",
        "title": "Điều khoản Sử dụng",
        "content": "<h2>Điều khoản Sử dụng</h2><p>Nội dung đang được cập nhật. Vui lòng vào trang Admin để chỉnh sửa bài viết bằng trình soạn thảo.</p>",
    },
    {
        "slug": "xoa-du-lieu",
        "title": "Xóa Dữ liệu",
        "content": "<h2>Xóa Dữ liệu</h2><p>Nội dung đang được cập nhật. Vui lòng vào trang Admin để chỉnh sửa bài viết bằng trình soạn thảo.</p>",
    },
    {
        "slug": "chinh-sach-ai",
        "title": "Chính sách AI",
        "content": "<h2>Chính sách AI</h2><p>Nội dung đang được cập nhật. Vui lòng vào trang Admin để chỉnh sửa bài viết bằng trình soạn thảo.</p>",
    },
    {
        "slug": "ho-tro-lien-he",
        "title": "Hỗ trợ & Liên hệ",
        "content": "<h2>Hỗ trợ & Liên hệ</h2><p>Nội dung đang được cập nhật. Vui lòng vào trang Admin để chỉnh sửa bài viết bằng trình soạn thảo.</p>",
    }
]

def add_pages():
    for p in pages:
        try:
            create_page(p['slug'], p['title'], p['content'], is_active=1)
            print("Created:", p['slug'])
        except Exception as e:
            print("Failed:", p['slug'], str(e))

if __name__ == "__main__":
    add_pages()
