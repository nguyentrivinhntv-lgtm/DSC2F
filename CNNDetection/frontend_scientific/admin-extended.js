// admin-extended.js - Phụ trách các tab Admin mở rộng

document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('admin.html')) return;
    
    // Navigation bindings
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    const tabPanes = document.querySelectorAll('.main-content .tab-pane');
    
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            item.classList.add('active');
            const targetId = `tab-${item.getAttribute('data-tab')}`;
            document.getElementById(targetId).classList.add('active');

            if (targetId === 'tab-admin-dashboard') fetchAdminStats();
            if (targetId === 'tab-admin-users') fetchAdminUsers();
            if (targetId === 'tab-admin-deletion') loadDeletionRequests();
            if (targetId === 'tab-admin-models') fetchAdminModels();
            if (targetId === 'tab-admin-history') fetchAdminHistory();
            if (targetId === 'tab-admin-payments') loadPaymentHistory();
            if (targetId === 'tab-admin-customize') loadSiteConfig();
            if (targetId === 'tab-admin-pages') loadPages();
            if (targetId === 'tab-admin-notifications') loadScheduledNotifs();
            if (targetId === 'tab-admin-api') loadApiConfig();
            if (targetId === 'tab-admin-ai') loadAiConfig();
        });
    });

    // Excel Export bindings
    document.getElementById('btn-export-dashboard-excel')?.addEventListener('click', exportDashboardExcel);
    document.getElementById('btn-export-history-excel')?.addEventListener('click', exportHistoryExcel);
    document.getElementById('btn-export-payments-excel')?.addEventListener('click', exportPaymentsExcel);

    // Gán sự kiện cho các nút save
    document.getElementById('btn-save-config')?.addEventListener('click', saveSiteConfig);
    document.getElementById('btn-reset-config')?.addEventListener('click', resetSiteConfig);
    document.getElementById('btn-save-payment-config')?.addEventListener('click', saveApiConfig);
    document.getElementById('btn-save-ai')?.addEventListener('click', saveAiConfigData);
    document.getElementById('btn-send-notif')?.addEventListener('click', sendNotification);
    document.getElementById('btn-save-page')?.addEventListener('click', savePage);
    document.getElementById('btn-add-page')?.addEventListener('click', () => openPageModal());
    document.getElementById('btn-add-package')?.addEventListener('click', addPricingPackage);
    document.getElementById('admin-topup-btn')?.addEventListener('click', topupUserTokens);
    document.getElementById('admin-hist-search')?.addEventListener('input', applyHistFilter);
    document.getElementById('admin-hist-model')?.addEventListener('change', applyHistFilter);
    document.getElementById('admin-hist-verdict')?.addEventListener('change', applyHistFilter);
    document.getElementById('admin-search-users')?.addEventListener('input', renderAdminUsers);
        
    // Logo upload
    document.getElementById('logo-file-input')?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await fetch(`${API_URL}/admin/upload-image`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${authToken}` },
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                await fetch(`${API_URL}/admin/site-config`, {
                    method: 'PUT',
                    headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ logo_url: data.url })
                });
                showMsg('config-save-message', `Logo đã được tải lên: ${data.url}`);
                setTimeout(() => hideMsg('config-save-message'), 3000);
            }
        } catch(err) {}
    });
        
    fetchAdminStats();
});

// --- Chart.js & Export helpers ---
function exportToExcel(data, fileName) {
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
    XLSX.writeFile(wb, `${fileName}.xlsx`);
}

// --- Yêu cầu xoá tài khoản ---
async function loadDeletionRequests() {
    try {
        const res = await fetch(`${API_URL}/auth/deletion-requests`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const data = await res.json();
            let tbody = '';
            data.forEach(req => {
                const statusCls = req.status === 'pending' ? 'text-warning' : (req.status === 'completed' ? 'text-success' : 'text-muted');
                const statusText = req.status === 'pending' ? 'Chờ duyệt' : (req.status === 'completed' ? 'Đã xử lý' : req.status);
                const actions = req.status === 'pending' 
                    ? `<button class="btn btn-outline text-danger btn-sm" onclick="processDeletion(${req.id})"><i class="fa-solid fa-check"></i> Chấp thuận</button>
                       <button class="btn btn-outline btn-sm" onclick="rejectDeletion(${req.id})"><i class="fa-solid fa-xmark"></i> Từ chối</button>`
                    : `<span class="text-muted">-</span>`;
                tbody += `<tr>
                    <td>${req.id}</td>
                    <td>${req.contact_info ? window.escapeHTML(req.contact_info) : '-'}</td>
                    <td>${req.reason ? window.escapeHTML(req.reason) : '-'}</td>
                    <td>${new Date(req.created_at).toLocaleString()}</td>
                    <td><span class="badge ${statusCls}">${statusText}</span></td>
                    <td>${actions}</td>
                </tr>`;
            });
            document.getElementById('admin-deletion-tbody').innerHTML = tbody || '<tr><td colspan="6" class="text-center text-muted">Không có yêu cầu nào</td></tr>';
        }
    } catch(e) { console.error('Error loading deletion requests', e); }
}

window.processDeletion = async function(id) {
    if(confirm('Chấp thuận yêu cầu xoá tài khoản này? Tài khoản liên quan sẽ bị vô hiệu hóa.')) {
        try {
            await fetch(`${API_URL}/auth/deletion-requests/${id}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'completed' })
            });
            loadDeletionRequests();
        } catch(e) { console.error(e); }
    }
}

window.rejectDeletion = async function(id) {
    if(confirm('Từ chối yêu cầu xoá tài khoản này?')) {
        try {
            await fetch(`${API_URL}/auth/deletion-requests/${id}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'rejected' })
            });
            loadDeletionRequests();
        } catch(e) { console.error(e); }
    }
}

// --- Lịch sử thanh toán ---
let rawPaymentItems = [];
async function loadPaymentHistory() {
    const tbody = document.getElementById('admin-payment-history-tbody');
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Đang tải...</td></tr>';
    try {
        const res = await fetch(`${API_URL}/payment-history/admin`, { headers: { Authorization: `Bearer ${authToken}` } });
        if(res.ok) {
            const data = await res.json();
            rawPaymentItems = data.items || [];
            let html = '';
            let totalRev = 0; let totalTok = 0; let trans = rawPaymentItems.length;
            
            rawPaymentItems.forEach(p => {
                totalRev += p.amount;
                totalTok += p.tokens;
                let cls = p.status === 'success' ? 'text-success' : 'text-danger';
                html += `<tr>
                    <td>${new Date(p.created_at).toLocaleString()}</td>
                    <td><strong>${window.escapeHTML(p.username)}</strong></td>
                    <td>${p.order_id}</td>
                    <td>${p.amount.toLocaleString()} đ</td>
                    <td>${p.tokens}</td>
                    <td class="${cls}">${p.status.toUpperCase()}</td>
                    <td>-</td>
                </tr>`;
            });
            
            document.getElementById('admin-total-revenue').innerText = totalRev.toLocaleString() + ' đ';
            document.getElementById('admin-total-tokens-granted').innerText = totalTok;
            document.getElementById('admin-total-transactions').innerText = trans;
            document.getElementById('admin-payment-history-tbody').innerHTML = html || '<tr><td colspan="7" class="text-center text-muted">Không có dữ liệu</td></tr>';
        }
    } catch(e) {}
}

function exportPaymentsExcel() {
    exportToExcel(rawPaymentItems, 'payment-history');
}

function exportDashboardExcel() {
    if (!window.adminDashboardItems || window.adminDashboardItems.length === 0) return alert("Không có dữ liệu thống kê để xuất!");
    exportToExcel(window.adminDashboardItems, 'admin-dashboard-stats');
}

function exportHistoryExcel() {
    if (!rawHistItems || rawHistItems.length === 0) return alert("Không có dữ liệu lịch sử để xuất!");
    exportToExcel(rawHistItems, 'admin-history');
}

// --- Tuỳ chỉnh giao diện (Site Config) ---
let currentConfig = {};
async function loadSiteConfig() {
    try {
        const res = await fetch(`${API_URL}/admin/site-config`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            currentConfig = await res.json();
            
            // Điền form Colors
            document.getElementById('cfg-color-primary').value = currentConfig.color_primary || '#0d6efd';
            document.getElementById('cfg-color-accent').value = currentConfig.color_accent || '#f59e0b';
            document.getElementById('cfg-color-bg').value = currentConfig.color_bg || '#f8f9fa';
            document.getElementById('cfg-color-text').value = currentConfig.color_text || '#212529';
            
            // Info
            document.getElementById('cfg-site-name').value = currentConfig.site_name || 'CNNDetection';
            document.getElementById('cfg-site-slogan').value = currentConfig.site_slogan || '';
            document.getElementById('cfg-contact-email').value = currentConfig.contact_email || '';
            document.getElementById('cfg-contact-phone').value = currentConfig.contact_phone || '';
            document.getElementById('cfg-footer-desc').value = currentConfig.footer_desc || '';
            document.getElementById('cfg-footer-text').value = currentConfig.footer_text || '';
            
            // Hero
            document.getElementById('cfg-hero-title1').value = currentConfig.hero_title1 || '';
            document.getElementById('cfg-hero-title2').value = currentConfig.hero_title2 || '';
            document.getElementById('cfg-hero-desc').value = currentConfig.hero_desc || '';
            document.getElementById('cfg-hero-cta').value = currentConfig.hero_cta || '';
            
            // Features
            document.getElementById('cfg-f1-title').value = currentConfig.f1_title || '';
            document.getElementById('cfg-f1-desc').value = currentConfig.f1_desc || '';
            document.getElementById('cfg-f2-title').value = currentConfig.f2_title || '';
            document.getElementById('cfg-f2-desc').value = currentConfig.f2_desc || '';
            document.getElementById('cfg-f3-title').value = currentConfig.f3_title || '';
            document.getElementById('cfg-f3-desc').value = currentConfig.f3_desc || '';
            
            // Steps
            document.getElementById('cfg-s1-title').value = currentConfig.s1_title || '';
            document.getElementById('cfg-s1-desc').value = currentConfig.s1_desc || '';
            document.getElementById('cfg-s2-title').value = currentConfig.s2_title || '';
            document.getElementById('cfg-s2-desc').value = currentConfig.s2_desc || '';
            document.getElementById('cfg-s3-title').value = currentConfig.s3_title || '';
            document.getElementById('cfg-s3-desc').value = currentConfig.s3_desc || '';
            
            // Toggles (luu trong db la "1" hoac "0")
            document.getElementById('cfg-show-stats').checked = currentConfig.show_stats !== "0";
            document.getElementById('cfg-show-marquee').checked = currentConfig.show_marquee !== "0";
            document.getElementById('cfg-show-features').checked = currentConfig.show_features !== "0";
            document.getElementById('cfg-show-howitworks').checked = currentConfig.show_howitworks !== "0";
            document.getElementById('cfg-show-cta').checked = currentConfig.show_cta !== "0";
            
            // Pricing Packages
            let pkgs = [];
            try {
                pkgs = JSON.parse(currentConfig.token_packages || '[]');
            } catch(e) {}
            renderPricingPackages(pkgs);
        }
    } catch(e) {}
}

function renderPricingPackages(packages) {
    const list = document.getElementById('pricing-packages-list');
    list.innerHTML = '';
    packages.forEach((pkg, i) => {
        list.innerHTML += `
            <div class="package-row" style="display:flex; gap:10px; margin-bottom:10px;" data-idx="${i}">
                <input type="text" class="form-control pkg-name" placeholder="Tên gói (Ví dụ: Cơ bản)" value="${pkg.name || ''}">
                <input type="number" class="form-control pkg-tokens" placeholder="Số token" value="${pkg.tokens || 0}">
                <input type="number" class="form-control pkg-price" placeholder="Giá (VND)" value="${pkg.price || 0}">
                <button class="btn btn-outline text-danger btn-sm" onclick="this.parentElement.remove()">X</button>
            </div>
        `;
    });
}

function addPricingPackage() {
    const list = document.getElementById('pricing-packages-list');
    list.insertAdjacentHTML('beforeend', `
        <div class="package-row" style="display:flex; gap:10px; margin-bottom:10px;">
            <input type="text" class="form-control pkg-name" placeholder="Tên gói">
            <input type="number" class="form-control pkg-tokens" placeholder="Số token">
            <input type="number" class="form-control pkg-price" placeholder="Giá (VND)">
            <button class="btn btn-outline text-danger btn-sm" onclick="this.parentElement.remove()">X</button>
        </div>
    `);
}

async function saveSiteConfig() {
    const cfg = {
        ...currentConfig,
        site_name: document.getElementById('cfg-site-name').value,
        site_slogan: document.getElementById('cfg-site-slogan').value,
        contact_email: document.getElementById('cfg-contact-email').value,
        contact_phone: document.getElementById('cfg-contact-phone').value,
        footer_desc: document.getElementById('cfg-footer-desc').value,
        footer_text: document.getElementById('cfg-footer-text').value,
        
        hero_title1: document.getElementById('cfg-hero-title1').value,
        hero_title2: document.getElementById('cfg-hero-title2').value,
        hero_desc: document.getElementById('cfg-hero-desc').value,
        hero_cta: document.getElementById('cfg-hero-cta').value,
        
        f1_title: document.getElementById('cfg-f1-title').value,
        f1_desc: document.getElementById('cfg-f1-desc').value,
        f2_title: document.getElementById('cfg-f2-title').value,
        f2_desc: document.getElementById('cfg-f2-desc').value,
        f3_title: document.getElementById('cfg-f3-title').value,
        f3_desc: document.getElementById('cfg-f3-desc').value,
        
        s1_title: document.getElementById('cfg-s1-title').value,
        s1_desc: document.getElementById('cfg-s1-desc').value,
        s2_title: document.getElementById('cfg-s2-title').value,
        s2_desc: document.getElementById('cfg-s2-desc').value,
        s3_title: document.getElementById('cfg-s3-title').value,
        s3_desc: document.getElementById('cfg-s3-desc').value,

        color_primary: document.getElementById('cfg-color-primary').value,
        color_accent: document.getElementById('cfg-color-accent').value,
        color_bg: document.getElementById('cfg-color-bg').value,
        color_text: document.getElementById('cfg-color-text').value,
        show_stats: document.getElementById('cfg-show-stats').checked ? "1" : "0",
        show_marquee: document.getElementById('cfg-show-marquee').checked ? "1" : "0",
        show_features: document.getElementById('cfg-show-features').checked ? "1" : "0",
        show_howitworks: document.getElementById('cfg-show-howitworks').checked ? "1" : "0",
        show_cta: document.getElementById('cfg-show-cta').checked ? "1" : "0"
    };
    
    // Thu thập pricing
    const packages = [];
    document.querySelectorAll('.package-row').forEach(row => {
        packages.push({
            name: row.querySelector('.pkg-name').value,
            tokens: parseInt(row.querySelector('.pkg-tokens').value) || 0,
            price: parseInt(row.querySelector('.pkg-price').value) || 0
        });
    });
    cfg.token_packages = JSON.stringify(packages);

    try {
        const res = await fetch(`${API_URL}/admin/site-config`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(cfg)
        });
        if (res.ok) {
            showMsg('config-save-message', 'Lưu cấu hình UI thành công.');
            setTimeout(() => hideMsg('config-save-message'), 3000);
        }
    } catch(e) {}
}

async function resetSiteConfig() {
    if (!confirm('Khôi phục toàn bộ cấu hình giao diện về mặc định?')) return;
    try {
        const res = await fetch(`${API_URL}/admin/site-config/reset`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            showMsg('config-save-message', 'Đã khôi phục cấu hình mặc định.');
            setTimeout(() => hideMsg('config-save-message'), 3000);
            loadSiteConfig();
        }
    } catch(e) {}
}

// --- CMS Pages ---
async function loadPages() {
    try {
        const res = await fetch(`${API_URL}/pages?is_admin=true`);
        if (res.ok) {
            const data = await res.json();
            let tbody = '';
            data.forEach(p => {
                tbody += `<tr>
                    <td>${p.title}</td>
                    <td>/${p.slug}</td>
                    <td>${p.is_active ? '<span class="text-success">Published</span>' : '<span class="text-danger">Draft</span>'}</td>
                    <td>
                        <button class="btn btn-outline btn-sm" onclick="editPage('${p.slug}')">Sửa</button>
                        <button class="btn btn-outline btn-sm text-danger" onclick="deletePage('${p.slug}')">Xóa</button>
                    </td>
                </tr>`;
            });
            document.getElementById('admin-pages-tbody').innerHTML = tbody || '<tr><td colspan="4" class="text-center">Chưa có trang nào</td></tr>';
        }
    } catch(e) {
        document.getElementById('admin-pages-tbody').innerHTML = '<tr><td colspan="4" class="text-center">Backend CMS chưa khởi tạo.</td></tr>';
    }
}

let editingPageSlug = null;

function openPageModal(slug = null) {
    editingPageSlug = slug;
    document.getElementById('page-title').value = '';
    document.getElementById('page-slug').value = '';
    document.getElementById('page-content').value = '';
    document.getElementById('page-status').checked = true;
    document.getElementById('page-modal-title').innerText = slug ? 'Sửa Trang' : 'Tạo Trang Mới';
    document.getElementById('page-modal').style.display = 'block';
}

window.editPage = async function(slug) {
    try {
        const res = await fetch(`${API_URL}/pages/${slug}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const page = await res.json();
            editingPageSlug = slug;
            document.getElementById('page-title').value = page.title || '';
            document.getElementById('page-slug').value = page.slug || '';
            document.getElementById('page-content').value = page.content || '';
            document.getElementById('page-status').checked = page.is_active;
            document.getElementById('page-modal-title').innerText = 'Sửa Trang';
            document.getElementById('page-modal').style.display = 'block';
        }
    } catch(e) { alert('Lỗi tải trang'); }
}

window.deletePage = async function(slug) {
    if (!confirm(`Xóa trang "${slug}"?`)) return;
    try {
        const res = await fetch(`${API_URL}/pages/${slug}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) { loadPages(); }
        else { alert('Lỗi xóa trang'); }
    } catch(e) { alert('Lỗi kết nối'); }
}

async function savePage() {
    const title = document.getElementById('page-title').value.trim();
    const slug = document.getElementById('page-slug').value.trim();
    const content = document.getElementById('page-content').value;
    const is_active = document.getElementById('page-status').checked;

    if (!title || !slug) { alert('Vui lòng nhập tiêu đề và slug.'); return; }

    try {
        let res;
        if (editingPageSlug) {
            res = await fetch(`${API_URL}/pages/${editingPageSlug}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, content, is_active })
            });
        } else {
            res = await fetch(`${API_URL}/pages`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ slug, title, content, is_active })
            });
        }
        if (res.ok) {
            document.getElementById('page-modal').style.display = 'none';
            editingPageSlug = null;
            loadPages();
        } else {
            const data = await res.json();
            alert(data.detail || 'Lỗi lưu trang');
        }
    } catch(e) { alert('Lỗi kết nối'); }
}

// --- Notifications ---
async function loadScheduledNotifs() {
    try {
        const res = await fetch(`${API_URL}/notifications/admin/scheduled`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if(res.ok) {
            const data = await res.json();
            let tbody = '';
            data.forEach(n => {
                tbody += `<tr>
                    <td>${n.id}</td>
                    <td>${n.title}</td>
                    <td>${n.type}</td>
                    <td>${n.status}</td>
                    <td><button class="btn btn-outline text-danger btn-sm">Xoá</button></td>
                </tr>`;
            });
            document.getElementById('admin-scheduled-notifs-tbody').innerHTML = tbody || '<tr><td colspan="5" class="text-center">Không có lịch.</td></tr>';
        }
    } catch(e) {}
}

async function sendNotification() {
    const payload = {
        title: document.getElementById('notif-title').value,
        message: document.getElementById('notif-message').value,
        type: document.getElementById('notif-type').value
    };
    try {
        const res = await fetch(`${API_URL}/notifications/admin/send`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showMsg('notif-msg', 'Gửi thành công.');
            setTimeout(() => hideMsg('notif-msg'), 3000);
        }
    } catch(e) {}
}

// --- API Config & AI Config ---
async function loadApiConfig() {
    try {
        const res = await fetch(`${API_URL}/admin/site-config`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const cfg = await res.json();
            document.getElementById('cfg-google-id').value = cfg.google_client_id || '';
            document.getElementById('cfg-google-secret').value = cfg.google_client_secret || '';
            document.getElementById('cfg-smtp-server').value = cfg.smtp_server || '';
            document.getElementById('cfg-smtp-port').value = cfg.smtp_port || '';
            document.getElementById('cfg-smtp-user').value = cfg.smtp_user || '';
            document.getElementById('cfg-smtp-pass').value = cfg.smtp_pass || '';
            document.getElementById('cfg-vnpay-tmn').value = cfg.vnpay_tmn_code || '';
            document.getElementById('cfg-vnpay-hash').value = cfg.vnpay_hash_secret || '';
            document.getElementById('cfg-vnpay-url').value = cfg.vnpay_payment_url || '';
            document.getElementById('cfg-vnpay-return').value = cfg.vnpay_return_url || '';
        }
    } catch(e) {}
}

async function loadAiConfig() {
    try {
        const res = await fetch(`${API_URL}/admin/site-config`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const cfg = await res.json();
            document.getElementById('cfg-ai-provider').value = cfg.ai_provider || 'groq';
            document.getElementById('cfg-ai-groq').value = cfg.ai_groq_key || '';
            document.getElementById('cfg-ai-gemini').value = cfg.ai_gemini_key || '';
            document.getElementById('cfg-ai-openai').value = cfg.ai_openai_key || '';
        }
    } catch(e) {}
}

async function saveApiConfig() {
    const cfg = {
        google_client_id: document.getElementById('cfg-google-id').value,
        google_client_secret: document.getElementById('cfg-google-secret').value,
        smtp_server: document.getElementById('cfg-smtp-server').value,
        smtp_port: document.getElementById('cfg-smtp-port').value,
        smtp_user: document.getElementById('cfg-smtp-user').value,
        smtp_pass: document.getElementById('cfg-smtp-pass').value,
        vnpay_tmn_code: document.getElementById('cfg-vnpay-tmn').value,
        vnpay_hash_secret: document.getElementById('cfg-vnpay-hash').value,
        vnpay_payment_url: document.getElementById('cfg-vnpay-url').value,
        vnpay_return_url: document.getElementById('cfg-vnpay-return').value
    };
    try {
        const res = await fetch(`${API_URL}/admin/site-config`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(cfg)
        });
        if (res.ok) {
            showMsg('payment-config-save-message', 'Lưu cấu hình hệ thống thành công.');
            setTimeout(() => hideMsg('payment-config-save-message'), 3000);
        } else {
            showMsg('payment-config-save-message', 'Lỗi lưu cấu hình.', true);
        }
    } catch(e) {
        showMsg('payment-config-save-message', 'Lỗi kết nối máy chủ.', true);
    }
}

async function saveAiConfigData() {
    const cfg = {
        ai_provider: document.getElementById('cfg-ai-provider').value,
        ai_groq_key: document.getElementById('cfg-ai-groq').value,
        ai_gemini_key: document.getElementById('cfg-ai-gemini').value,
        ai_openai_key: document.getElementById('cfg-ai-openai').value
    };
    try {
        const res = await fetch(`${API_URL}/admin/site-config`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(cfg)
        });
        if (res.ok) {
            showMsg('ai-save-message', 'Lưu cấu hình AI thành công.');
            setTimeout(() => hideMsg('ai-save-message'), 3000);
        } else {
            showMsg('ai-save-message', 'Lỗi lưu cấu hình.', true);
        }
    } catch(e) {
        showMsg('ai-save-message', 'Lỗi kết nối máy chủ.', true);
    }
}

// ------------------- BỔ SUNG CÁC TAB CƠ BẢN -------------------

// 1. Thống kê (Dashboard Stats)
let chartModels = null;
let chartVerdicts = null;
let chartTimeline = null;
let chartTopUsers = null;
window.adminDashboardItems = [];

async function fetchAdminStats() {
    try {
        const res = await fetch(`${API_URL}/history/?all=true`, { headers: { Authorization: `Bearer ${authToken}` } });
        if(res.ok) {
            const data = await res.json();
            const items = data.items || [];
            window.adminDashboardItems = items;
            
            // Tính toán stats
            const total = items.length;
            const fakeCount = items.filter(x => x.label === 'fake').length;
            const realCount = total - fakeCount;
            const fakeRate = total > 0 ? ((fakeCount/total)*100).toFixed(1) : 0;
            
            // Tính Model
            const mCount = {};
            items.forEach(i => mCount[i.model_type] = (mCount[i.model_type] || 0) + 1);
            let topM = '-'; let topV = 0;
            Object.keys(mCount).forEach(k => { if(mCount[k] > topV) { topV = mCount[k]; topM = k; }});
            
            document.getElementById('admin-stat-total').innerText = total;
            document.getElementById('admin-stat-fake-rate').innerText = fakeRate + '%';
            document.getElementById('admin-stat-top-model').innerText = topM;
            
            // Render Charts
            const colors = ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0', '#6f42c1', '#fd7e14'];
            
            if(chartModels) chartModels.destroy();
            chartModels = new Chart(document.getElementById('chart-models'), {
                type: 'pie',
                data: {
                    labels: Object.keys(mCount),
                    datasets: [{
                        data: Object.values(mCount),
                        backgroundColor: colors.slice(0, Object.keys(mCount).length)
                    }]
                }
            });
            
            if(chartVerdicts) chartVerdicts.destroy();
            chartVerdicts = new Chart(document.getElementById('chart-verdicts'), {
                type: 'doughnut',
                data: {
                    labels: ['Fake', 'Real'],
                    datasets: [{
                        data: [fakeCount, realCount],
                        backgroundColor: ['#dc3545', '#198754']
                    }]
                }
            });
            
            // Timeline (Last 7 days)
            const timeData = {};
            items.forEach(i => {
                const d = new Date(i.created_at).toLocaleDateString();
                timeData[d] = (timeData[d] || 0) + 1;
            });
            const sortedDays = Object.keys(timeData).sort((a,b) => new Date(a) - new Date(b)).slice(-7);
            const timeValues = sortedDays.map(d => timeData[d]);
            
            if(chartTimeline) chartTimeline.destroy();
            chartTimeline = new Chart(document.getElementById('chart-timeline'), {
                type: 'line',
                data: {
                    labels: sortedDays,
                    datasets: [{
                        label: 'Lượt quét',
                        data: timeValues,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        fill: true,
                        tension: 0.3
                    }]
                }
            });

            // Top 5 Users
            const userCounts = {};
            items.forEach(i => {
                userCounts[i.username] = (userCounts[i.username] || 0) + 1;
            });
            const topUsersArr = Object.entries(userCounts).sort((a,b) => b[1] - a[1]).slice(0, 5);
            
            if(chartTopUsers) chartTopUsers.destroy();
            chartTopUsers = new Chart(document.getElementById('chart-top-users'), {
                type: 'bar',
                data: {
                    labels: topUsersArr.map(x => x[0]),
                    datasets: [{
                        label: 'Lượt dùng',
                        data: topUsersArr.map(x => x[1]),
                        backgroundColor: '#6f42c1'
                    }]
                }
            });
            
            
            // Users count
            const uRes = await fetch(`${API_URL}/auth/admin/users`, { headers: { Authorization: `Bearer ${authToken}` } });
            if(uRes.ok) {
                const uData = await uRes.json();
                document.getElementById('admin-stat-users').innerText = uData.length || 0;
            }
        }
    } catch(e) {}
}

// 2. Quản lý User
let rawAdminUsers = [];
async function fetchAdminUsers() {
    const tbody = document.getElementById('admin-users-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Đang tải...</td></tr>';
    try {
        const res = await fetch(`${API_URL}/auth/admin/users`, { headers: { Authorization: `Bearer ${authToken}` } });
        if(res.ok) {
            rawAdminUsers = await res.json();
            renderAdminUsers();
        } else { tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Lỗi kết nối.</td></tr>'; }
    } catch(e) {}
}

function renderAdminUsers() {
    const term = (document.getElementById('admin-search-users')?.value || '').toLowerCase();
    const tbody = document.getElementById('admin-users-tbody');
    let html = '';
    rawAdminUsers.filter(u => u.username.toLowerCase().includes(term) || (u.email||'').toLowerCase().includes(term))
    .forEach(u => {
        let disabled = (u.username === 'admin' && localStorage.getItem('user') !== 'admin') ? 'disabled' : '';
        html += `<tr>
            <td>${u.id}</td>
            <td><strong>${window.escapeHTML(u.username)}</strong> ${u.username==='admin' ? '<small class="text-danger">(Super)</small>' : ''}</td>
            <td>${u.email ? window.escapeHTML(u.email) : '-'}</td>
            <td>${u.prediction_tokens}</td>
            <td>
                <select class="form-control" onchange="changeUserRole('${u.username}', this.value)" ${disabled} style="display:inline-block; width:auto; padding:0.2rem;">
                    <option value="user" ${u.role === 'user' ? 'selected' : ''}>User</option>
                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                </select>
            </td>
        </tr>`;
    });
    tbody.innerHTML = html || '<tr><td colspan="5" class="text-center text-muted">Không tìm thấy user.</td></tr>';
}

window.changeUserRole = async function(username, newRole) {
    try {
        const res = await fetch(`${API_URL}/auth/admin/users/role`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ username, new_role: newRole })
        });
        if(res.ok) { showMsg('admin-user-msg', 'Cập nhật phân quyền thành công!'); fetchAdminUsers(); }
    } catch(e) {}
}

// 3. Quản lý Models
async function fetchAdminModels() {
    const tbody = document.getElementById('admin-models-tbody');
    try {
        const res = await fetch(`${API_URL}/admin/models`, { headers: { Authorization: `Bearer ${authToken}` } });
        if(res.ok) {
            const data = await res.json();
            let html = '';
            data.models.forEach(m => {
                const isChecked = m.is_active ? 'checked' : '';
                html += `<tr>
                    <td><code>${m.model_type}</code></td>
                    <td>Mô hình phân tích (Academic)</td>
                    <td id="status-${m.model_type}">${m.is_active ? '<span class="text-success">Đang bật</span>' : '<span class="text-danger">Đã tắt</span>'}</td>
                    <td>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleAdminModel('${m.model_type}', this)" ${isChecked}>
                            <span class="slider"></span>
                        </label>
                    </td>
                </tr>`;
            });
            tbody.innerHTML = html;
        }
    } catch(e) {}
}

window.toggleAdminModel = async function(modelType, cb) {
    try {
        const res = await fetch(`${API_URL}/admin/models/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ model_type: modelType, is_active: cb.checked })
        });
        if(res.ok) {
            document.getElementById(`status-${modelType}`).innerHTML = cb.checked ? '<span class="text-success">Đang bật</span>' : '<span class="text-danger">Đã tắt</span>';
        } else { cb.checked = !cb.checked; }
    } catch(e) { cb.checked = !cb.checked; }
}

// 4. Nạp Token
async function topupUserTokens() {
    const username = document.getElementById('topup-username').value.trim();
    const amount = parseInt(document.getElementById('topup-amount').value);
    if(!username || !amount) return;
    try {
        const res = await fetch(`${API_URL}/auth/admin/tokens/topup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ username, amount })
        });
        const data = await res.json();
        if(res.ok) {
            showMsg('topup-msg', `Đã cấp ${data.added_tokens} tokens cho ${username}. Mới: ${data.prediction_tokens}`);
        } else {
            showMsg('topup-msg', data.detail || 'Lỗi cấp phát');
        }
    } catch(e) {}
}

// 5. Lịch sử Toàn cục
let rawHistItems = [];
async function fetchAdminHistory() {
    const tbody = document.getElementById('admin-history-tbody');
    try {
        const res = await fetch(`${API_URL}/history/?all=true`, { headers: { Authorization: `Bearer ${authToken}` } });
        if(res.ok) {
            const data = await res.json();
            rawHistItems = data.items || [];
            applyHistFilter();
            
            // Render filter options
            const models = new Set(rawHistItems.map(i => i.model_type));
            const select = document.getElementById('admin-hist-model');
            select.innerHTML = '<option value="all">Tất cả mô hình</option>';
            models.forEach(m => select.innerHTML += `<option value="${m}">${m}</option>`);
        }
    } catch(e) {}
}

function applyHistFilter() {
    const keyword = (document.getElementById('admin-hist-search')?.value || '').toLowerCase();
    const mod = document.getElementById('admin-hist-model')?.value || 'all';
    const ver = document.getElementById('admin-hist-verdict')?.value || 'all';
    
    let html = '';
    rawHistItems.filter(i => {
        const m1 = !keyword || i.username.toLowerCase().includes(keyword) || i.filename.toLowerCase().includes(keyword);
        const m2 = mod === 'all' || i.model_type === mod;
        const m3 = ver === 'all' || i.label === ver;
        return m1 && m2 && m3;
    }).forEach(i => {
        html += `<tr>
            <td>${new Date(i.created_at).toLocaleString()}</td>
            <td><strong>${i.username}</strong></td>
            <td>${i.filename}</td>
            <td>${i.model_type}</td>
            <td>${(i.probability*100).toFixed(2)}%</td>
            <td class="${i.label==='fake'?'text-danger':'text-success'}"><strong>${i.label.toUpperCase()}</strong></td>
        </tr>`;
    });
    document.getElementById('admin-history-tbody').innerHTML = html || '<tr><td colspan="6" class="text-center text-muted">Không có lịch sử</td></tr>';
}
