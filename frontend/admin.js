const API_URL = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) ? "http://localhost:8000" : "https://cnn-detection-api.onrender.com";

const token = localStorage.getItem('token');
const user = localStorage.getItem('user');
const role = localStorage.getItem('role');

const adminUserLabel = document.getElementById('admin-user-label');
const historyBody = document.getElementById('admin-history-body');
const modelsBody = document.getElementById('admin-models-body');
const refreshBtn = document.getElementById('refresh-btn');
const exportBtn = document.getElementById('export-btn');
const searchInput = document.getElementById('search-user');
const filterModel = document.getElementById('filter-model');
const filterLabel = document.getElementById('filter-label');
const topupUsernameInput = document.getElementById('topup-username');
const topupAmountInput = document.getElementById('topup-amount');
const topupBtn = document.getElementById('topup-btn');
const topupMessage = document.getElementById('topup-message');
const navUserDashboard = document.getElementById('nav-user-dashboard');
const navAdminDashboard = document.getElementById('nav-admin-dashboard');

let rawItems = [];
let viewItems = [];

// Biến lưu trữ instances của Chart.js để hủy trước khi vẽ lại
let pieChartInstance = null;
let barChartInstance = null;
let lineChartInstance = null;

function ensureAdmin() {
    if (!token || !user) {
        alert('Vui lòng đăng nhập trước khi vào admin.');
        window.location.href = 'app.html';
        return false;
    }

    if (role !== 'admin') {
        alert('Chỉ tài khoản admin mới có quyền truy cập trang này.');
        window.location.href = 'app.html';
        return false;
    }

    adminUserLabel.textContent = `${t('admin_login_as')} ${user}`;
    return true;
}

function syncHeaderNav() {
    if (!navUserDashboard || !navAdminDashboard) return;

    navUserDashboard.classList.remove('active');
    navAdminDashboard.classList.add('active');

    if (role === 'admin') {
        navAdminDashboard.classList.remove('hidden');
    } else {
        navAdminDashboard.classList.add('hidden');
    }
}

// ----------------- TABS LOGIC -----------------
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to current
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
            
            if (tabId === 'tab-payment-history') {
                fetchPaymentHistory();
            } else if (tabId === 'tab-pages') {
                loadPagesList();
            }
        });
    });
}

async function fetchPaymentHistory() {
    const historyBody = document.getElementById('admin-payment-history-body');
    if (!historyBody) return;

    historyBody.innerHTML = '<tr><td colspan="6" class="loading-cell">Đang tải dữ liệu...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/payment-history/?all=true`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });
        
        if (res.status === 401 || res.status === 403) {
            logout();
            return;
        }

        const data = await res.json();
        if (res.ok) {
            if (!data.items || data.items.length === 0) {
                historyBody.innerHTML = '<tr><td colspan="6" class="loading-cell">Chưa có giao dịch mua hàng nào.</td></tr>';
                return;
            }
            
            // Calculate admin stats
            const totalRevenue = data.items.reduce((sum, item) => sum + item.amount, 0);
            const totalTokens = data.items.reduce((sum, item) => sum + item.tokens, 0);
            
            const elTotalRevenue = document.getElementById('admin-total-revenue');
            const elTotalTokens = document.getElementById('admin-total-tokens-granted');
            const elTotalTx = document.getElementById('admin-total-transactions');
            
            if (elTotalRevenue) elTotalRevenue.innerText = totalRevenue.toLocaleString('vi-VN') + ' đ';
            if (elTotalTokens) elTotalTokens.innerText = totalTokens.toLocaleString('vi-VN');
            if (elTotalTx) elTotalTx.innerText = data.items.length.toLocaleString('vi-VN');

            historyBody.innerHTML = '';
            data.items.forEach(item => {
                const dateStr = new Date(item.created_at).toLocaleString('vi-VN');
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${dateStr}</td>
                    <td style="font-weight:bold; color:var(--primary);">${item.username}</td>
                    <td>${item.order_id}</td>
                    <td>${item.amount.toLocaleString('vi-VN')} đ</td>
                    <td style="color:var(--primary);font-weight:bold;">+${item.tokens}</td>
                    <td><span class="badge" style="background:#ecfdf5;color:#065f46;border-color:#86efac;">Thành công</span></td>
                    <td><button class="btn btn-sm btn-view-order" style="padding: 5px 10px; font-size: 0.8rem;"><i class="fa-solid fa-eye"></i> Xem</button></td>
                `;
                historyBody.appendChild(tr);

                const btnView = tr.querySelector('.btn-view-order');
                btnView.addEventListener('click', () => {
                    document.getElementById('modal-order-id').innerText = item.order_id;
                    const userEl = document.getElementById('modal-order-user');
                    if (userEl) userEl.innerText = item.username;
                    document.getElementById('modal-order-time').innerText = dateStr;
                    document.getElementById('modal-order-amount').innerText = item.amount.toLocaleString('vi-VN');
                    document.getElementById('modal-order-tokens').innerText = `+${item.tokens}`;
                    document.getElementById('modal-order-bank').innerText = item.bank_code || 'N/A';
                    document.getElementById('modal-order-card').innerText = item.card_type || 'N/A';
                    document.getElementById('modal-order-vnpay-no').innerText = item.vnp_transaction_no || 'N/A';
                    
                    document.getElementById('order-details-modal').classList.remove('hidden');
                });
            });

            // Setup close buttons for order details modal
            const closeBtn1 = document.getElementById('btn-close-order-modal');
            const closeBtn2 = document.getElementById('btn-close-order-modal-2');
            const orderModal = document.getElementById('order-details-modal');
            if (closeBtn1) closeBtn1.onclick = () => orderModal.classList.add('hidden');
            if (closeBtn2) closeBtn2.onclick = () => orderModal.classList.add('hidden');
            
        } else {
            historyBody.innerHTML = `<tr><td colspan="6" class="loading-cell">Lỗi: ${data.detail || 'Không lấy được dữ liệu'}</td></tr>`;
        }
    } catch (e) {
        console.error("fetchPaymentHistory error:", e);
        historyBody.innerHTML = '<tr><td colspan="6" class="loading-cell">Lỗi kết nối tới API.</td></tr>';
    }
}

function modelLabel(modelType) {
    const names = {
        dual_stream_enhanced: 'Dual Stream Enhanced',
        dual_stream_resnet: 'Dual Stream ResNet18',
        resnet50: 'ResNet-50'
    };
    return names[modelType] || modelType;
}

// ----------------- CHARTS LOGIC -----------------
function renderCharts(items) {
    const pieCtx = document.getElementById('chart-pie-fake-real');
    const barCtx = document.getElementById('chart-bar-models');
    const lineCtx = document.getElementById('chart-line-time');

    if (!pieCtx || !barCtx || !lineCtx) return;

    // Hủy chart cũ nếu có
    if (pieChartInstance) pieChartInstance.destroy();
    if (barChartInstance) barChartInstance.destroy();
    if (lineChartInstance) lineChartInstance.destroy();

    if (!items.length) return;

    // Dữ liệu Fake / Real
    const fakeCount = items.filter(x => x.label === 'fake').length;
    const realCount = items.length - fakeCount;

    // Dữ liệu Model
    const modelCount = {};
    items.forEach(item => {
        modelCount[item.model_type] = (modelCount[item.model_type] || 0) + 1;
    });
    const modelLabels = Object.keys(modelCount).map(k => modelLabel(k));
    const modelData = Object.values(modelCount);

    // Dữ liệu theo thời gian (nhóm theo ngày)
    const timeCount = {};
    items.forEach(item => {
        const dateStr = new Date(item.created_at).toLocaleDateString('vi-VN');
        timeCount[dateStr] = (timeCount[dateStr] || 0) + 1;
    });
    // Sắp xếp theo ngày tăng dần
    const sortedDates = Object.keys(timeCount).sort((a, b) => {
        const [d1, m1, y1] = a.split('/');
        const [d2, m2, y2] = b.split('/');
        return new Date(`${y1}-${m1}-${d1}`) - new Date(`${y2}-${m2}-${d2}`);
    });
    const timeData = sortedDates.map(date => timeCount[date]);

    // Vẽ Pie Chart
    pieChartInstance = new Chart(pieCtx, {
        type: 'doughnut',
        data: {
            labels: ['Fake', 'Real'],
            datasets: [{
                data: [fakeCount, realCount],
                backgroundColor: ['#ef4444', '#10b981'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });

    // Vẽ Bar Chart
    barChartInstance = new Chart(barCtx, {
        type: 'bar',
        data: {
            labels: modelLabels,
            datasets: [{
                label: 'Lượt sử dụng',
                data: modelData,
                backgroundColor: '#0ea5a4',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            },
            plugins: { legend: { display: false } }
        }
    });

    // Vẽ Line Chart
    lineChartInstance = new Chart(lineCtx, {
        type: 'line',
        data: {
            labels: sortedDates,
            datasets: [{
                label: 'Lượt phân tích',
                data: timeData,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}

function updateStats(items) {
    const total = items.length;
    const users = new Set(items.map((x) => x.username)).size;
    const fakeCount = items.filter((x) => x.label === 'fake').length;
    const fakeRate = total ? ((fakeCount / total) * 100).toFixed(1) : 0;

    const modelCount = {};
    items.forEach((item) => {
        modelCount[item.model_type] = (modelCount[item.model_type] || 0) + 1;
    });

    let topModel = '-';
    let topModelCount = 0;
    Object.keys(modelCount).forEach((k) => {
        if (modelCount[k] > topModelCount) {
            topModelCount = modelCount[k];
            topModel = modelLabel(k);
        }
    });

    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-users').textContent = users;
    document.getElementById('stat-fake-rate').textContent = `${fakeRate}%`;
    document.getElementById('stat-top-model').textContent = topModel;
    
    // Cập nhật biểu đồ cùng lúc
    renderCharts(items);
}

function renderTable(items) {
    if (!items.length) {
        historyBody.innerHTML = '<tr><td colspan="6" class="loading-cell">Không có dữ liệu phù hợp bộ lọc.</td></tr>';
        return;
    }

    let html = '';
    items.forEach((item) => {
        const timeStr = new Date(item.created_at).toLocaleString('vi-VN');
        const fakePercent = (item.probability * 100).toFixed(2);
        const isFake = item.label === 'fake';

        html += `
            <tr>
                <td>${timeStr}</td>
                <td>${item.username}</td>
                <td title="${item.filename}">${item.filename}</td>
                <td>${modelLabel(item.model_type)}</td>
                <td>${fakePercent}%</td>
                <td class="${isFake ? 'fake' : 'real'}">${isFake ? 'FAKE' : 'REAL'}</td>
            </tr>
        `;
    });

    historyBody.innerHTML = html;
}

function applyFilter() {
    const keyword = searchInput.value.trim().toLowerCase();
    const model = filterModel.value;
    const label = filterLabel.value;

    viewItems = rawItems.filter((item) => {
        const matchKeyword = !keyword
            || item.username.toLowerCase().includes(keyword)
            || item.filename.toLowerCase().includes(keyword);
        const matchModel = model === 'all' || item.model_type === model;
        const matchLabel = label === 'all' || item.label === label;
        return matchKeyword && matchModel && matchLabel;
    });

    updateStats(viewItems);
    renderTable(viewItems);
}

async function fetchAdminHistory() {
    historyBody.innerHTML = '<tr><td colspan="6" class="loading-cell">Đang tải dữ liệu...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/history/?all=true`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (res.status === 401) {
            alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
            window.location.href = 'app.html';
            return;
        }

        const data = await res.json();
        if (!res.ok) {
            historyBody.innerHTML = `<tr><td colspan="6" class="loading-cell">Lỗi: ${data.detail || 'Không lấy được dữ liệu'}</td></tr>`;
            return;
        }

        if (!data.is_admin) {
            alert('API từ chối: tài khoản hiện tại không phải admin.');
            window.location.href = 'app.html';
            return;
        }

        rawItems = data.items || [];
        applyFilter();
    } catch (error) {
        historyBody.innerHTML = '<tr><td colspan="6" class="loading-cell">Lỗi kết nối tới API.</td></tr>';
    }
}

// ----------------- QUẢN LÝ MODEL -----------------
async function fetchAdminModels() {
    if (!modelsBody) return;
    modelsBody.innerHTML = '<tr><td colspan="4" class="loading-cell">Đang tải danh sách model...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/admin/models`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });
        const data = await res.json();
        
        if (!res.ok) {
            modelsBody.innerHTML = `<tr><td colspan="4" class="loading-cell">Lỗi: ${data.detail || 'Không lấy được dữ liệu'}</td></tr>`;
            return;
        }

        let html = '';
        data.models.forEach(m => {
            const isChecked = m.is_active ? 'checked' : '';
            const statusText = m.is_active ? '<span style="color:#10b981;font-weight:bold;">Đang bật</span>' : '<span style="color:#ef4444;font-weight:bold;">Đã tắt</span>';
            html += `
                <tr>
                    <td><code>${m.model_type}</code></td>
                    <td>${modelLabel(m.model_type)}</td>
                    <td id="status-text-${m.model_type}">${statusText}</td>
                    <td>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleModel('${m.model_type}', this)" ${isChecked}>
                            <span class="slider"></span>
                        </label>
                    </td>
                </tr>
            `;
        });
        modelsBody.innerHTML = html;
        
    } catch (error) {
        modelsBody.innerHTML = '<tr><td colspan="4" class="loading-cell">Lỗi kết nối tới API.</td></tr>';
    }
}

async function toggleModel(modelType, checkbox) {
    const isActive = checkbox.checked;
    checkbox.disabled = true; // Disable temporarily while fetching

    try {
        const res = await fetch(`${API_URL}/admin/models/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
                model_type: modelType,
                is_active: isActive
            })
        });

        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || 'Lỗi khi cập nhật trạng thái model');
            checkbox.checked = !isActive; // Revert
        } else {
            // Update UI status text
            const textTd = document.getElementById(`status-text-${modelType}`);
            if (textTd) {
                textTd.innerHTML = isActive ? '<span style="color:#10b981;font-weight:bold;">Đang bật</span>' : '<span style="color:#ef4444;font-weight:bold;">Đã tắt</span>';
            }
        }
    } catch (error) {
        alert('Lỗi kết nối tới API');
        checkbox.checked = !isActive; // Revert
    } finally {
        checkbox.disabled = false;
    }
}

// Global scope for HTML onclick
window.toggleModel = toggleModel;

// ----------------- NẠP TOKEN -----------------
async function topupUserTokens() {
    if (!topupUsernameInput || !topupAmountInput || !topupBtn || !topupMessage) return;

    const username = topupUsernameInput.value.trim();
    const amount = Number(topupAmountInput.value);

    topupMessage.className = 'topup-message';
    topupMessage.textContent = '';

    if (!username) {
        topupMessage.classList.add('error');
        topupMessage.textContent = 'Vui lòng nhập username.';
        return;
    }
    if (!Number.isFinite(amount) || amount <= 0) {
        topupMessage.classList.add('error');
        topupMessage.textContent = 'Số token nạp phải lớn hơn 0.';
        return;
    }

    topupBtn.disabled = true;

    try {
        const res = await fetch(`${API_URL}/auth/admin/tokens/topup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
                username,
                amount: Math.floor(amount)
            })
        });

        const data = await res.json();
        if (!res.ok) {
            topupMessage.classList.add('error');
            topupMessage.textContent = data.detail || 'Nạp token thất bại.';
            return;
        }

        topupMessage.classList.add('success');
        topupMessage.textContent = `Đã nạp +${data.added_tokens} token cho ${data.username}. Tổng hiện tại: ${data.prediction_tokens}.`;
    } catch {
        topupMessage.classList.add('error');
        topupMessage.textContent = 'Lỗi kết nối tới API khi nạp token.';
    } finally {
        topupBtn.disabled = false;
    }
}

// ----------------- QUẢN LÝ USER -----------------
let rawUsers = [];

async function fetchAdminUsers() {
    const usersBody = document.getElementById('admin-users-body');
    if (!usersBody) return;
    
    usersBody.innerHTML = '<tr><td colspan="5" class="loading-cell">Đang tải dữ liệu...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/auth/admin/users`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        
        if (!res.ok) {
            usersBody.innerHTML = '<tr><td colspan="5" class="loading-cell">Không lấy được dữ liệu users</td></tr>';
            return;
        }

        rawUsers = await res.json();
        renderAdminUsers();
    } catch (e) {
        usersBody.innerHTML = '<tr><td colspan="5" class="loading-cell">Lỗi kết nối tới API.</td></tr>';
    }
}

function renderAdminUsers() {
    const usersBody = document.getElementById('admin-users-body');
    const searchInput = document.getElementById('search-users-input');
    if (!usersBody) return;

    let filterText = searchInput ? searchInput.value.toLowerCase() : '';
    
    let filteredUsers = rawUsers.filter(u => 
        u.username.toLowerCase().includes(filterText) || 
        (u.email && u.email.toLowerCase().includes(filterText))
    );

    if (filteredUsers.length === 0) {
        usersBody.innerHTML = '<tr><td colspan="5" class="loading-cell">Không tìm thấy user nào</td></tr>';
        return;
    }

    let html = '';
    filteredUsers.forEach(u => {
        // Disabled logic for super admin
        let disabled = (u.username === 'admin' && user !== 'admin') ? 'disabled' : '';
        
        html += `
            <tr>
                <td>${u.id}</td>
                <td><strong>${u.username}</strong> ${u.username === 'admin' ? '<span style="color:red; font-size:12px;">(Super Admin)</span>' : ''}</td>
                <td>${u.email || '-'}</td>
                <td>${u.prediction_tokens}</td>
                <td>
                    <select onchange="changeUserRole('${u.username}', this.value)" ${disabled} style="padding: 5px; border-radius: 4px; background: var(--color-bg2); color: var(--color-text); border: 1px solid var(--border);">
                        <option value="user" ${u.role === 'user' ? 'selected' : ''}>User</option>
                        <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                    </select>
                </td>
            </tr>
        `;
    });
    
    usersBody.innerHTML = html;
}

async function changeUserRole(username, newRole) {
    const msgEl = document.getElementById('user-role-message');
    try {
        const res = await fetch(`${API_URL}/auth/admin/users/role`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({ username: username, new_role: newRole })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            msgEl.className = 'topup-message success';
            msgEl.textContent = data.message;
            fetchAdminUsers(); // Reload
        } else {
            msgEl.className = 'topup-message error';
            msgEl.textContent = data.detail || 'Lỗi phân quyền';
            fetchAdminUsers(); // Revert
        }
    } catch (e) {
        msgEl.className = 'topup-message error';
        msgEl.textContent = 'Lỗi kết nối tới API';
    }
    
    setTimeout(() => { msgEl.textContent = ''; msgEl.className = 'topup-message'; }, 3000);
}
window.changeUserRole = changeUserRole;

// Bind search input
if (document.getElementById('search-users-input')) {
    document.getElementById('search-users-input').addEventListener('input', renderAdminUsers);
}


function exportCsv() {
    if (!viewItems.length) {
        alert('Không có dữ liệu để xuất.');
        return;
    }

    const header = ['created_at', 'username', 'filename', 'model_type', 'probability', 'label'];
    const rows = viewItems.map((item) => [
        item.created_at,
        item.username,
        item.filename,
        item.model_type,
        item.probability,
        item.label
    ]);

    const csvContent = [header, ...rows]
        .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
        .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `admin-history-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ----------------- TÙY CHỈNH GIAO DIỆN -----------------

// Mapping: form field ID -> config key
const CONFIG_FIELDS = {
    'cfg-color-primary': 'color_primary',
    'cfg-color-accent': 'color_accent',
    'cfg-color-bg': 'color_bg',
    'cfg-color-bg2': 'color_bg2',
    'cfg-color-bg3': 'color_bg3',
    'cfg-color-text': 'color_text',
    'cfg-site-name': 'site_name',
    'cfg-site-slogan': 'site_slogan',
    'cfg-footer-text': 'footer_text',
    'cfg-hero-title1': 'hero_title_line1',
    'cfg-hero-title2': 'hero_title_line2',
    'cfg-hero-desc': 'hero_desc',
    'cfg-hero-cta': 'hero_cta_text',
    'cfg-f1-title': 'feature1_title',
    'cfg-f1-desc': 'feature1_desc',
    'cfg-f2-title': 'feature2_title',
    'cfg-f2-desc': 'feature2_desc',
    'cfg-f3-title': 'feature3_title',
    'cfg-f3-desc': 'feature3_desc',
    'cfg-s1-title': 'step1_title',
    'cfg-s1-desc': 'step1_desc',
    'cfg-s2-title': 'step2_title',
    'cfg-s2-desc': 'step2_desc',
    'cfg-s3-title': 'step3_title',
    'cfg-s3-desc': 'step3_desc',

};

const TOGGLE_FIELDS = {
    'cfg-show-stats': 'show_stats',
    'cfg-show-marquee': 'show_marquee',
    'cfg-show-features': 'show_features',
    'cfg-show-howitworks': 'show_howitworks',
    'cfg-show-cta': 'show_cta',
};

const configMsg = document.getElementById('config-save-message');

function showConfigMsg(text, type = 'success') {
    if (!configMsg) return;
    configMsg.textContent = text;
    configMsg.className = 'topup-message ' + type;
    setTimeout(() => { configMsg.textContent = ''; configMsg.className = 'topup-message'; }, 4000);
}

// Sync color hex display
function setupColorSync() {
    const pairs = [
        ['cfg-color-primary', 'hex-primary'],
        ['cfg-color-accent', 'hex-accent'],
        ['cfg-color-bg', 'hex-bg'],
        ['cfg-color-bg2', 'hex-bg2'],
        ['cfg-color-bg3', 'hex-bg3'],
        ['cfg-color-text', 'hex-text'],
    ];
    pairs.forEach(([inputId, hexId]) => {
        const inp = document.getElementById(inputId);
        const hex = document.getElementById(hexId);
        if (inp && hex) {
            inp.addEventListener('input', () => { hex.textContent = inp.value; });
        }
    });
}

async function fetchSiteConfig() {
    try {
        const res = await fetch(`${API_URL}/site-config`);
        if (!res.ok) return;
        const config = await res.json();

        // Fill text/color fields
        for (const [fieldId, configKey] of Object.entries(CONFIG_FIELDS)) {
            const el = document.getElementById(fieldId);
            if (el && config[configKey] !== undefined) {
                el.value = config[configKey];
            }
        }

        // Fill toggles
        for (const [fieldId, configKey] of Object.entries(TOGGLE_FIELDS)) {
            const el = document.getElementById(fieldId);
            if (el && config[configKey] !== undefined) {
                el.checked = config[configKey] === '1';
            }
        }

        // Sync color hex displays
        ['cfg-color-primary', 'cfg-color-accent', 'cfg-color-bg', 'cfg-color-text'].forEach(id => {
            const inp = document.getElementById(id);
            const hexId = id.replace('cfg-color-', 'hex-');
            const hex = document.getElementById(hexId);
            if (inp && hex) hex.textContent = inp.value;
        });

        // Logo preview
        if (config.logo_url) {
            const preview = document.getElementById('logo-preview');
            const removeBtn = document.getElementById('btn-remove-logo');
            if (preview) {
                preview.src = config.logo_url;
                preview.style.display = 'block';
            }
            if (removeBtn) removeBtn.style.display = 'inline-flex';
        }

        // Token Packages
        if (config.token_packages) {
            try {
                const packages = JSON.parse(config.token_packages);
                renderAdminPackages(packages);
            } catch (err) {
                console.error("Failed to parse token_packages", err);
            }
        } else {
            renderAdminPackages([]);
        }

    } catch (e) {
        console.error('Lỗi khi tải site config:', e);
    }
}

async function saveSiteConfig() {
    const data = {};

    // Collect text/color fields
    for (const [fieldId, configKey] of Object.entries(CONFIG_FIELDS)) {
        const el = document.getElementById(fieldId);
        if (el) data[configKey] = el.value;
    }

    // Collect toggles
    for (const [fieldId, configKey] of Object.entries(TOGGLE_FIELDS)) {
        const el = document.getElementById(fieldId);
        if (el) data[configKey] = el.checked ? '1' : '0';
    }

    // Collect Token Packages
    data['token_packages'] = JSON.stringify(collectAdminPackages());

    // Logo URL (stored separately via upload, just include current value)
    const logoPreview = document.getElementById('logo-preview');
    if (logoPreview && logoPreview.src && logoPreview.style.display !== 'none') {
        data['logo_url'] = logoPreview.src;
    } else {
        data['logo_url'] = '';
    }

    try {
        const res = await fetch(`${API_URL}/admin/site-config`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(data),
        });
        const result = await res.json();
        if (res.ok) {
            showConfigMsg('✅ Đã lưu thay đổi giao diện thành công!', 'success');
        } else {
            showConfigMsg('❌ ' + (result.detail || 'Lỗi khi lưu.'), 'error');
        }
    } catch (e) {
        showConfigMsg('❌ Không thể kết nối tới server.', 'error');
    }
}

async function resetSiteConfig() {
    if (!confirm('Bạn có chắc muốn khôi phục toàn bộ giao diện về mặc định? Hành động này không thể hoàn tác.')) return;

    try {
        const res = await fetch(`${API_URL}/admin/site-config/reset`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        const result = await res.json();
        if (res.ok) {
            showConfigMsg('✅ Đã khôi phục giao diện mặc định!', 'success');
            fetchSiteConfig(); // Reload form values
        } else {
            showConfigMsg('❌ ' + (result.detail || 'Lỗi khi khôi phục.'), 'error');
        }
    } catch (e) {
        showConfigMsg('❌ Không thể kết nối tới server.', 'error');
    }
}

async function uploadLogo(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_URL}/admin/upload-image`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${token}`,
            },
            body: formData,
        });
        const result = await res.json();
        if (res.ok) {
            const preview = document.getElementById('logo-preview');
            const removeBtn = document.getElementById('btn-remove-logo');
            if (preview) {
                preview.src = result.url;
                preview.style.display = 'block';
            }
            if (removeBtn) removeBtn.style.display = 'inline-flex';
            showConfigMsg('✅ Upload logo thành công! Nhớ bấm "Lưu thay đổi".', 'success');
        } else {
            showConfigMsg('❌ ' + (result.detail || 'Lỗi upload.'), 'error');
        }
    } catch (e) {
        showConfigMsg('❌ Không thể upload ảnh.', 'error');
    }
}

function initCustomizeTab() {
    setupColorSync();

    const saveBtn = document.getElementById('btn-save-config');
    const resetBtn = document.getElementById('btn-reset-config');
    const previewBtn = document.getElementById('btn-preview-site');
    const logoInput = document.getElementById('logo-file-input');
    const removeLogoBtn = document.getElementById('btn-remove-logo');

    if (saveBtn) saveBtn.addEventListener('click', saveSiteConfig);
    if (resetBtn) resetBtn.addEventListener('click', resetSiteConfig);
    if (previewBtn) previewBtn.addEventListener('click', () => window.open('index.html', '_blank'));

    if (logoInput) {
        logoInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                uploadLogo(e.target.files[0]);
            }
        });
    }

    if (removeLogoBtn) {
        removeLogoBtn.addEventListener('click', () => {
            const preview = document.getElementById('logo-preview');
            if (preview) {
                preview.src = '';
                preview.style.display = 'none';
            }
            removeLogoBtn.style.display = 'none';
            showConfigMsg('Logo đã xóa. Nhớ bấm "Lưu thay đổi".', 'success');
        });
    }

    fetchSiteConfig();
}

// ----------------- CMS PAGES LOGIC -----------------
let quillEditor = null;

function initCMS() {
    // Init Quill Editor
    if (typeof Quill !== 'undefined' && !quillEditor) {
        quillEditor = new Quill('#page-content-editor', {
            theme: 'snow',
            modules: {
                toolbar: [
                    [{ 'header': [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    ['blockquote', 'code-block'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    [{ 'color': [] }, { 'background': [] }],
                    ['link', 'image', 'video'],
                    ['clean']
                ]
            }
        });
    }

    const modal = document.getElementById('page-editor-modal');
    const btnAdd = document.getElementById('btn-add-page');
    const btnClose = document.getElementById('btn-close-page-modal');
    const btnCancel = document.getElementById('btn-cancel-page-modal');
    const btnSave = document.getElementById('btn-save-page');

    if (btnAdd) btnAdd.addEventListener('click', () => openPageModal('add'));
    if (btnClose) btnClose.addEventListener('click', () => modal.classList.add('hidden'));
    if (btnCancel) btnCancel.addEventListener('click', () => modal.classList.add('hidden'));
    if (btnSave) btnSave.addEventListener('click', savePage);
}

async function loadPagesList() {
    const tbody = document.getElementById('admin-pages-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Đang tải...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/pages?is_admin=true`, {
            headers: { 'Authorization': `Bearer ${token}` },
            cache: 'no-store'
        });
        
        if (!response.ok) throw new Error('Không thể tải danh sách trang');
        
        const pages = await response.json();
        if (pages.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Chưa có trang nào được tạo.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        pages.forEach(p => {
            const tr = document.createElement('tr');
            const isActive = p.is_active ? '<span class="badge" style="background:#ecfdf5;color:#065f46;">Đang bật</span>' : '<span class="badge" style="background:#fef2f2;color:#991b1b;">Đã tắt</span>';
            const date = new Date(p.updated_at || p.created_at).toLocaleString('vi-VN');
            
            tr.innerHTML = `
                <td><strong>${p.title}</strong></td>
                <td><code>/${p.slug}</code></td>
                <td>${isActive}</td>
                <td>${date}</td>
                <td>
                    <button class="nav-btn" onclick="editPage('${p.slug}')"><i class="fa-solid fa-pen"></i></button>
                    <button class="nav-btn reset-btn" onclick="deletePage('${p.slug}')"><i class="fa-solid fa-trash"></i></button>
                    <a href="page.html?id=${p.slug}" target="_blank" class="nav-btn"><i class="fa-solid fa-eye"></i></a>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" style="color:red;text-align:center;">Lỗi: ${err.message}</td></tr>`;
    }
}

async function editPage(slug) {
    try {
        const response = await fetch(`${API_URL}/pages/${slug}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Lỗi tải chi tiết trang');
        const page = await response.json();
        
        openPageModal('edit', page);
    } catch (err) {
        alert("Lỗi: " + err.message);
    }
}

function openPageModal(mode, pageData = null) {
    document.getElementById('page-edit-mode').value = mode;
    document.getElementById('page-save-message').textContent = '';
    document.getElementById('page-save-message').className = 'topup-message';
    
    if (mode === 'add') {
        document.getElementById('page-modal-title').innerHTML = '<i class="fa-solid fa-plus"></i> Tạo Trang Mới';
        document.getElementById('page-slug-input').value = '';
        document.getElementById('page-slug-input').disabled = false;
        document.getElementById('page-title-input').value = '';
        document.getElementById('page-active-input').checked = true;
        if(quillEditor) quillEditor.root.innerHTML = '';
    } else {
        document.getElementById('page-modal-title').innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Chỉnh Sửa Trang';
        document.getElementById('page-slug-input').value = pageData.slug;
        document.getElementById('page-slug-input').disabled = true; // Không cho sửa slug
        document.getElementById('page-title-input').value = pageData.title;
        document.getElementById('page-active-input').checked = pageData.is_active;
        if(quillEditor) quillEditor.root.innerHTML = pageData.content;
    }
    
    document.getElementById('page-editor-modal').classList.remove('hidden');
}

async function savePage() {
    const mode = document.getElementById('page-edit-mode').value;
    const slug = document.getElementById('page-slug-input').value.trim();
    const title = document.getElementById('page-title-input').value.trim();
    const content = quillEditor ? quillEditor.root.innerHTML : '';
    const isActive = document.getElementById('page-active-input').checked;
    const msgEl = document.getElementById('page-save-message');
    
    if (!slug || !title) {
        msgEl.textContent = 'Vui lòng nhập Tiêu đề và Slug.';
        msgEl.className = 'topup-message error';
        return;
    }
    
    // Validate slug
    if (!/^[a-z0-9-]+$/.test(slug)) {
        msgEl.textContent = 'Slug chỉ được chứa chữ thường không dấu, số và dấu gạch ngang.';
        msgEl.className = 'topup-message error';
        return;
    }
    
    const payload = { slug, title, content, is_active: isActive };
    const method = mode === 'add' ? 'POST' : 'PUT';
    const url = mode === 'add' ? `${API_URL}/pages` : `${API_URL}/pages/${slug}`;
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        
        const resData = await response.json();
        if (!response.ok) throw new Error(resData.detail || 'Lỗi lưu trang');
        
        msgEl.textContent = 'Đã lưu trang thành công!';
        msgEl.className = 'topup-message success';
        
        // Tắt modal sau 1s
        setTimeout(() => {
            document.getElementById('page-editor-modal').classList.add('hidden');
            loadPagesList();
        }, 1000);
    } catch (err) {
        msgEl.textContent = err.message;
        msgEl.className = 'topup-message error';
    }
}

async function deletePage(slug) {
    if (!confirm(`Bạn có chắc muốn xóa trang /${slug} không? Hành động này không thể hoàn tác.`)) return;
    
    try {
        const response = await fetch(`${API_URL}/pages/${slug}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Không thể xóa');
        
        alert('Đã xóa thành công!');
        loadPagesList();
    } catch (err) {
        alert(err.message);
    }
}

// ----------------- INIT -----------------
syncHeaderNav();
initTabs();

if (ensureAdmin()) {
    fetchAdminHistory();
    fetchAdminModels();
    fetchAdminUsers();
    initCustomizeTab();
    initCMS();
}

refreshBtn.addEventListener('click', () => {
    fetchAdminHistory();
    fetchAdminModels();
    fetchAdminUsers();
});
exportBtn.addEventListener('click', exportCsv);
searchInput.addEventListener('input', applyFilter);
filterModel.addEventListener('change', applyFilter);
filterLabel.addEventListener('change', applyFilter);
if (topupBtn) {
    topupBtn.addEventListener('click', topupUserTokens);
}


// --- Token Packages Admin Logic ---
function renderAdminPackages(packages) {
    const list = document.getElementById('pricing-packages-list');
    if (!list) return;
    list.innerHTML = '';
    
    packages.forEach((pkg, index) => {
        addPackageDOM(pkg);
    });
}

function addPackageDOM(pkg = {}) {
    const list = document.getElementById('pricing-packages-list');
    if (!list) return;
    
    const div = document.createElement('div');
    div.className = 'config-field admin-package-item';
    div.style = 'background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid var(--border); position: relative; display: grid; gap: 10px;';
    
    div.innerHTML = `
        <button type="button" class="btn-remove-pkg" style="position: absolute; top: 10px; right: 10px; background: none; border: none; color: var(--danger); cursor: pointer; font-size: 16px;"><i class="fa-solid fa-trash"></i></button>
        
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center;">
            <input type="text" class="pkg-name" placeholder="Tên gói (VD: Gói Cơ Bản)" value="${pkg.name || ''}">
            <label style="display: flex; align-items: center; gap: 5px; font-size: 14px; cursor: pointer;">
                <input type="checkbox" class="pkg-popular" ${pkg.popular ? 'checked' : ''}>
                Nổi bật
            </label>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <input type="number" class="pkg-price" placeholder="Giá (VND)" value="${pkg.price || ''}">
            <input type="number" class="pkg-tokens" placeholder="Số Token" value="${pkg.tokens || ''}">
        </div>
        
        <input type="text" class="pkg-features" placeholder="Các tính năng, phân cách bằng dấu phẩy (,)" value="${(pkg.features || []).join(', ')}">
    `;
    
    div.querySelector('.btn-remove-pkg').addEventListener('click', () => {
        div.remove();
    });
    
    list.appendChild(div);
}

function collectAdminPackages() {
    const list = document.getElementById('pricing-packages-list');
    if (!list) return [];
    
    const packages = [];
    const items = list.querySelectorAll('.admin-package-item');
    items.forEach((item, index) => {
        const name = item.querySelector('.pkg-name').value.trim();
        const price = parseInt(item.querySelector('.pkg-price').value) || 0;
        const tokens = parseInt(item.querySelector('.pkg-tokens').value) || 0;
        const popular = item.querySelector('.pkg-popular').checked;
        const featuresStr = item.querySelector('.pkg-features').value.trim();
        const features = featuresStr ? featuresStr.split(',').map(f => f.trim()).filter(f => f.length > 0) : [];
        
        packages.push({
            id: 'pkg_' + (index + 1),
            name,
            price,
            tokens,
            popular,
            features
        });
    });
    return packages;
}

document.addEventListener('DOMContentLoaded', () => {
    const btnAdd = document.getElementById('btn-add-package');
    if (btnAdd) {
        btnAdd.addEventListener('click', () => {
            addPackageDOM();
        });
    }
});
