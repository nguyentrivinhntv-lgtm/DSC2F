import re
import os

FRONTEND_DIR = r"d:\khoaluanthuctap\DSC2F\CNNDetection\frontend"

def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Bỏ Authorization header
    content = re.sub(r"['\"]?Authorization['\"]?\s*:\s*[`'\"]Bearer\s*[`'\"]\s*\+\s*\w+,?", "", content)
    content = re.sub(r"['\"]?Authorization['\"]?\s*:\s*`Bearer\s*\$\{[^}]+\}`,?", "", content)
    
    # Bỏ các dấu phẩy thừa do xoá
    content = re.sub(r",\s*}", " }", content)

    # 2. Thêm credentials: 'include' vào fetch
    # Thay 'fetch(url, {' thành 'fetch(url, { credentials: "include",'
    content = re.sub(r"(fetch\([^,]+,\s*\{)", r"\1 credentials: 'include', ", content)

    # 3. Thay localStorage token
    content = re.sub(r"localStorage\.setItem\('token',\s*[^)]+\);", "// Cookie HttpOnly set by backend", content)
    content = re.sub(r"localStorage\.setItem\('access_token',\s*[^)]+\);", "", content)
    
    content = re.sub(r"localStorage\.removeItem\('token'\);", "fetch(`${API_URL || 'http://localhost:8000'}/auth/logout`, {method: 'POST', credentials: 'include'}).catch(e=>console.log(e));\n    localStorage.removeItem('token');", content)
    
    # 4. Thay innerHTML thành textContent với các lỗi đơn giản
    content = content.replace(".innerHTML = `<tr><td colspan=\"6\" style=\"text-align:center;color:var(--danger)\">Lỗi: ${data.detail}</td></tr>`;", ".innerHTML = `<tr><td colspan=\"6\" style=\"text-align:center;color:var(--danger)\">Lỗi: ${data.detail.replace(/</g, '&lt;')}</td></tr>`;")
    
    content = content.replace("notifList.innerHTML = '<div style=\"text-align:center; padding: 10px; font-size: 13px; color: var(--danger);\">Không lấy được thông báo.</div>';", "notifList.innerHTML = '<div style=\"text-align:center; padding: 10px; font-size: 13px; color: var(--danger);\">Không lấy được thông báo.</div>';")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

process_file(os.path.join(FRONTEND_DIR, "app.js"))
process_file(os.path.join(FRONTEND_DIR, "admin.js"))
print("Done processing app.js and admin.js")
