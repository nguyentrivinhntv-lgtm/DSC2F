const API_URL = window.location.hostname === 'localhost' ? "http://localhost:8000" : "https://cnn-detection-api.onrender.com";

const token = localStorage.getItem('token');
const user = localStorage.getItem('user');
const role = localStorage.getItem('role');

const adminUserLabel = document.getElementById('admin-user-label');
const historyBody = document.getElementById('admin-history-body');
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

function ensureAdmin() {
    if (!token || !user) {
        alert('Vui lòng đăng nhập trước khi vào admin.');
        window.location.href = 'index.html';
        return false;
    }

    if (role !== 'admin') {
        alert('Chỉ tài khoản admin mới có quyền truy cập trang này.');
        window.location.href = 'index.html';
        return false;
    }

    adminUserLabel.textContent = `Đăng nhập quản trị: ${user}`;
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

function modelLabel(modelType) {
    const names = {
        dual_stream_enhanced: 'Dual Stream Enhanced',
        dual_stream_resnet: 'Dual Stream ResNet18',
        resnet50: 'ResNet-50'
    };
    return names[modelType] || modelType;
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
        const res = await fetch(`${API_URL}/history/`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (res.status === 401) {
            alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
            window.location.href = 'index.html';
            return;
        }

        const data = await res.json();
        if (!res.ok) {
            historyBody.innerHTML = `<tr><td colspan="6" class="loading-cell">Lỗi: ${data.detail || 'Không lấy được dữ liệu'}</td></tr>`;
            return;
        }

        if (!data.is_admin) {
            alert('API từ chối: tài khoản hiện tại không phải admin.');
            window.location.href = 'index.html';
            return;
        }

        rawItems = data.items || [];
        applyFilter();
    } catch (error) {
        historyBody.innerHTML = '<tr><td colspan="6" class="loading-cell">Lỗi kết nối tới API.</td></tr>';
    }
}

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

syncHeaderNav();

if (ensureAdmin()) {
    fetchAdminHistory();
}

refreshBtn.addEventListener('click', fetchAdminHistory);
exportBtn.addEventListener('click', exportCsv);
searchInput.addEventListener('input', applyFilter);
filterModel.addEventListener('change', applyFilter);
filterLabel.addEventListener('change', applyFilter);
if (topupBtn) {
    topupBtn.addEventListener('click', topupUserTokens);
}
