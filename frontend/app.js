const API_URL = "http://localhost:8000";

// --- DOM Elements ---
const authSection = document.getElementById('auth-section');
const dashSection = document.getElementById('dashboard-section');
const btnLoginTab = document.querySelectorAll('.tab-btn')[0];
const btnRegTab = document.querySelectorAll('.tab-btn')[1];
const loginForm = document.getElementById('login-form');
const regForm = document.getElementById('register-form');
const googleLoginContainer = document.getElementById('google-login-container');
const googleSigninBtn = document.getElementById('google-signin-btn');
const googleLoginError = document.getElementById('google-login-error');
const loginInfo = document.getElementById('login-info');
const userMenuBtn = document.getElementById('user-menu-btn');
const userDropdown = document.getElementById('user-dropdown');
const displayUsername = document.getElementById('display-username');
const displayRole = document.getElementById('display-role');
const tokenCard = document.getElementById('token-card');
const tokenCount = document.getElementById('token-count');
const logoutBtn = document.getElementById('logout-btn');
const adminPanelBtn = document.getElementById('admin-panel-btn');
const navUserDashboard = document.getElementById('nav-user-dashboard');
const navAdminDashboard = document.getElementById('nav-admin-dashboard');
const sidebarItems = document.querySelectorAll('.sidebar-item[data-tab]');
const workspaceSearchInput = document.querySelector('.workspace-search input');

// Predict DOM
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadContent = document.getElementById('upload-content');
const imgPreview = document.getElementById('image-preview');
const removeImgBtn = document.getElementById('remove-img-btn');
const analyzeBtn = document.getElementById('analyze-btn');
const modelSelect = document.getElementById('model-select');

// Result DOM
const resPlaceholder = document.getElementById('result-placeholder');
const resContent = document.getElementById('result-content');
const verdictBox = document.getElementById('verdict-box');
const verdictIcon = document.getElementById('verdict-icon');
const verdictText = document.getElementById('verdict-text');
const resConf = document.getElementById('res-confidence');
const resProb = document.getElementById('res-probability');
const resModel = document.getElementById('res-model');
const probMarker = document.getElementById('prob-marker');

// History DOM
const historyRefreshBtn = document.getElementById('history-refresh-btn');

// Batch DOM
const batchDrop = document.getElementById('batch-drop');
const batchFileInput = document.getElementById('batch-file-input');
const batchRunBtn = document.getElementById('batch-run-btn');
const batchModelSelect = document.getElementById('batch-model-select');
const batchSummary = document.getElementById('batch-summary');
const batchResultTbody = document.getElementById('batch-result-tbody');

// Analytics DOM
const statTotalScans = document.getElementById('stat-total-scans');
const statFakeRate = document.getElementById('stat-fake-rate');
const statRealRate = document.getElementById('stat-real-rate');
const statTopModel = document.getElementById('stat-top-model');
const statAvgFake = document.getElementById('stat-avg-fake');
const analyticsModelTbody = document.getElementById('analytics-model-tbody');

// API Management DOM
const apiTokenPreview = document.getElementById('api-token-preview');
const apiEndpointSelect = document.getElementById('api-endpoint-select');
const apiGenerateBtn = document.getElementById('api-generate-btn');
const apiCopyBtn = document.getElementById('api-copy-btn');
const apiTestBtn = document.getElementById('api-test-btn');
const apiCurlOutput = document.getElementById('api-curl-output');
const apiTestResult = document.getElementById('api-test-result');

// Settings DOM
const settingsThreshold = document.getElementById('settings-threshold');
const settingsThresholdValue = document.getElementById('settings-threshold-value');
const settingsAutoHistory = document.getElementById('settings-auto-history');
const saveSettingsBtn = document.getElementById('save-settings-btn');
const settingsSaveMsg = document.getElementById('settings-save-msg');

// --- Global State ---
let authToken = localStorage.getItem('token');
let authUser = localStorage.getItem('user');
let authRole = localStorage.getItem('role') || 'user';
let authPredictionTokens = Number(localStorage.getItem('prediction_tokens'));
let currentFile = null;
let batchFiles = [];
let cachedHistoryItems = [];
let googleInitRetry = 0;
const GOOGLE_INIT_MAX_RETRY = 10;

const MODEL_NAMES = {
    'dual_stream_enhanced': 'Dual Stream Enhanced',
    'dual_stream_resnet': 'Dual Stream ResNet18',
    'resnet50': 'ResNet-50'
};

const DEFAULT_USER_SETTINGS = {
    verdictThreshold: 85,
    autoLoadHistoryForAnalytics: true,
    preferredModel: 'dual_stream_enhanced'
};

let userSettings = loadUserSettings();

if (!Number.isFinite(authPredictionTokens)) {
    authPredictionTokens = 0;
}

function loadUserSettings() {
    try {
        const raw = localStorage.getItem('dashboard_settings');
        if (!raw) return { ...DEFAULT_USER_SETTINGS };
        const parsed = JSON.parse(raw);
        return { ...DEFAULT_USER_SETTINGS, ...parsed };
    } catch {
        return { ...DEFAULT_USER_SETTINGS };
    }
}

function saveUserSettings() {
    localStorage.setItem('dashboard_settings', JSON.stringify(userSettings));
}

function applySettingsToUI() {
    if (settingsThreshold) {
        settingsThreshold.value = String(userSettings.verdictThreshold);
    }
    if (settingsThresholdValue) {
        settingsThresholdValue.innerText = `${userSettings.verdictThreshold}%`;
    }
    if (settingsAutoHistory) {
        settingsAutoHistory.checked = !!userSettings.autoLoadHistoryForAnalytics;
    }
    if (modelSelect && userSettings.preferredModel) {
        modelSelect.value = userSettings.preferredModel;
    }
    if (batchModelSelect && userSettings.preferredModel) {
        batchModelSelect.value = userSettings.preferredModel;
    }
}

function getVerdictByThreshold(probability) {
    const threshold = userSettings.verdictThreshold / 100;
    return probability >= threshold ? 'fake' : 'real';
}

// --- Menu Toggle Logic ---
document.addEventListener('click', (e) => {
    const menuBtn = e.target.closest('#user-menu-btn');
    const menuDropdown = document.getElementById('user-dropdown');
    
    if (menuBtn) {
        e.stopPropagation();
        if (menuDropdown) menuDropdown.classList.toggle('hidden');
    } else {
        if (menuDropdown && !menuDropdown.contains(e.target)) {
            menuDropdown.classList.add('hidden');
        }
    }
});

// --- Init Application ---
function init() {
    syncHeaderNavByRole();
    initGoogleSignIn();
    if (authToken && authUser) {
        showDashboard();
    } else {
        showAuth();
    }
}

function setAuthPredictionTokens(tokens) {
    const parsed = Number(tokens);
    authPredictionTokens = Number.isFinite(parsed) ? Math.max(0, Math.floor(parsed)) : 0;
    localStorage.setItem('prediction_tokens', String(authPredictionTokens));
}

function showGoogleLoginFallback(message) {
    if (!googleLoginContainer || !googleSigninBtn) return;

    googleSigninBtn.innerHTML = `
        <button type="button" class="google-fallback-btn" disabled>
            <i class="fa-brands fa-google"></i>
            <span>Đăng nhập với Google</span>
        </button>
    `;

    googleLoginContainer.classList.remove('hidden');
    if (googleLoginError) {
        googleLoginError.innerText = message || '';
    }
}

async function initGoogleSignIn() {
    if (!googleLoginContainer || !googleSigninBtn) return;

    try {
        const res = await fetch(`${API_URL}/auth/google/config`);
        if (!res.ok) {
            showGoogleLoginFallback('Không tải được cấu hình Google Sign-In từ server.');
            return;
        }

        const cfg = await res.json();
        if (!cfg.enabled || !cfg.client_id) {
            showGoogleLoginFallback('Google Sign-In chưa bật trên server. Thêm GOOGLE_CLIENT_ID vào .env rồi restart API.');
            return;
        }

        if (!window.google || !window.google.accounts || !window.google.accounts.id) {
            if (googleInitRetry < GOOGLE_INIT_MAX_RETRY) {
                googleInitRetry += 1;
                setTimeout(initGoogleSignIn, 500);
            } else {
                showGoogleLoginFallback('Không tải được Google Identity script. Kiểm tra mạng hoặc extension chặn script.');
            }
            return;
        }

        window.google.accounts.id.initialize({
            client_id: cfg.client_id,
            callback: onGoogleCredentialResponse,
        });

        googleSigninBtn.innerHTML = '';
        window.google.accounts.id.renderButton(
            googleSigninBtn,
            {
                theme: 'outline',
                size: 'large',
                shape: 'pill',
                text: 'signin_with',
                width: 320,
            }
        );

        googleLoginContainer.classList.remove('hidden');
    } catch {
        showGoogleLoginFallback('Lỗi kết nối khi khởi tạo Google Sign-In.');
    }
}

async function onGoogleCredentialResponse(response) {
    if (!response || !response.credential) {
        if (googleLoginError) {
            googleLoginError.innerText = 'Không nhận được Google credential.';
        }
        return;
    }

    if (googleLoginError) {
        googleLoginError.innerText = '';
    }

    try {
        const res = await fetch(`${API_URL}/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: response.credential }),
        });

        const data = await res.json();
        if (!res.ok) {
            if (googleLoginError) {
                googleLoginError.innerText = data.detail || 'Đăng nhập Google thất bại.';
            }
            return;
        }

        authToken = data.access_token;
        authUser = data.username;
        authRole = data.role || 'user';
        setAuthPredictionTokens(data.prediction_tokens);

        localStorage.setItem('token', authToken);
        localStorage.setItem('user', authUser);
        localStorage.setItem('role', authRole);
        localStorage.removeItem('last_registered_tokens');

        showDashboard();
    } catch {
        if (googleLoginError) {
            googleLoginError.innerText = 'Lỗi kết nối server khi đăng nhập Google.';
        }
    }
}

// --- UI Navigation ---
function showAuth() {
    authSection.classList.remove('hidden');
    dashSection.classList.add('hidden');
    const lastGranted = Number(localStorage.getItem('last_registered_tokens'));
    if (loginInfo && Number.isFinite(lastGranted) && lastGranted > 0) {
        loginInfo.innerText = `Tài khoản mới được cấp ${lastGranted} token.`;
    }
    syncHeaderNavByRole();
}

function showDashboard() {
    authSection.classList.add('hidden');
    dashSection.classList.remove('hidden');

    // Cập nhật thông tin trong Dropdown
    if (displayUsername) displayUsername.innerText = authUser;
    if (displayRole) {
        displayRole.innerText = authRole === 'admin' ? 'Admin' : 'User';
        displayRole.className = `badge ${authRole === 'admin' ? 'admin-badge' : 'token-badge'}`;
    }

    // Cập nhật Token trong Sidebar
    if (tokenCard && tokenCount) {
        tokenCard.classList.remove('hidden');
        tokenCount.innerText = authRole === 'admin' ? 'Unlimited' : authPredictionTokens;
    }

    if (authRole === 'admin') {
        adminPanelBtn.classList.remove('hidden');
    } else {
        adminPanelBtn.classList.add('hidden');
    }

    syncHeaderNavByRole();
    applySettingsToUI();
    syncApiTokenPreview();

    switchDashTab('single-scan'); // Default tab
}

function syncApiTokenPreview() {
    if (!apiTokenPreview) return;
    if (!authToken) {
        apiTokenPreview.innerText = 'Chưa đăng nhập';
        return;
    }
    const shortToken = authToken.length > 42
        ? `${authToken.slice(0, 18)}...${authToken.slice(-14)}`
        : authToken;
    apiTokenPreview.innerText = `Bearer ${shortToken}`;
}

function syncHeaderNavByRole() {
    if (!navUserDashboard || !navAdminDashboard) return;

    navUserDashboard.classList.add('active');
    navAdminDashboard.classList.remove('active');

    if (authToken && authUser && authRole === 'admin') {
        navAdminDashboard.classList.remove('hidden');
    } else {
        navAdminDashboard.classList.add('hidden');
    }
}

function initSidebarNavigation() {
    sidebarItems.forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.dataset.tab;
            if (tab) switchDashTab(tab);
        });
    });
}

function switchAuthTab(tab) {
    if (tab === 'login') {
        btnLoginTab.classList.add('active');
        btnRegTab.classList.remove('active');
        loginForm.classList.add('active');
        regForm.classList.remove('active');
    } else {
        btnRegTab.classList.add('active');
        btnLoginTab.classList.remove('active');
        regForm.classList.add('active');
        loginForm.classList.remove('active');
        if (loginInfo) {
            loginInfo.innerText = "";
        }
        document.getElementById('register-success').innerText = "";
    }
}

// --- Authentication Logic ---

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = loginForm.querySelector('.btn-primary');
    const txt = btn.querySelector('.btn-text');
    const ldr = btn.querySelector('.loader');
    const err = document.getElementById('login-error');

    txt.classList.add('hidden');
    ldr.classList.remove('hidden');
    err.innerText = "";
    if (loginInfo) {
        loginInfo.innerText = "";
    }

    const pb = {
        username: document.getElementById('login-username').value,
        password: document.getElementById('login-password').value
    };

    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pb)
        });
        const data = await res.json();
        if (res.ok) {
            authToken = data.access_token;
            authUser = data.username;
            authRole = data.role;
            setAuthPredictionTokens(data.prediction_tokens);
            localStorage.setItem('token', authToken);
            localStorage.setItem('user', authUser);
            localStorage.setItem('role', authRole);
            localStorage.removeItem('last_registered_tokens');
            showDashboard();
        } else {
            err.innerText = data.detail || "Đăng nhập thất bại!";
        }
    } catch (e) { err.innerText = "Lỗi kết nối server!"; }

    txt.classList.remove('hidden');
    ldr.classList.add('hidden');
});

regForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = regForm.querySelector('.btn-primary');
    const txt = btn.querySelector('.btn-text');
    const ldr = btn.querySelector('.loader');
    const err = document.getElementById('register-error');
    const succ = document.getElementById('register-success');

    txt.classList.add('hidden');
    ldr.classList.remove('hidden');
    err.innerText = "";
    succ.innerText = "";

    const pb = {
        username: document.getElementById('reg-username').value,
        password: document.getElementById('reg-password').value
    };

    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pb)
        });
        const data = await res.json();
        if (res.ok) {
            const grantedTokens = Number.isFinite(Number(data.prediction_tokens))
                ? Number(data.prediction_tokens)
                : 5;
            localStorage.setItem('last_registered_tokens', String(grantedTokens));
            succ.innerText = `Đăng ký thành công! Bạn được tặng ${grantedTokens} token. Hãy đăng nhập.`;
            setTimeout(() => {
                switchAuthTab('login');
                if (loginInfo) {
                    loginInfo.innerText = `Tài khoản mới được cấp ${grantedTokens} token.`;
                }
            }, 1200);
        } else {
            err.innerText = data.detail || "Đăng ký thất bại!";
        }
    } catch (e) { err.innerText = "Lỗi kết nối server!"; }

    txt.classList.remove('hidden');
    ldr.classList.add('hidden');
});

logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('role');
    localStorage.removeItem('prediction_tokens');
    authToken = null;
    authUser = null;
    authRole = 'user';
    authPredictionTokens = 0;
    currentFile = null;
    syncHeaderNavByRole();
    resetImage();
    resPlaceholder.classList.remove('hidden');
    resContent.classList.add('hidden');
    cachedHistoryItems = [];
    clearAnalytics();
    clearBatchResults();
    showAuth();
});

if (adminPanelBtn) {
    adminPanelBtn.addEventListener('click', () => {
        if (authRole !== 'admin') {
            alert('Bạn không có quyền truy cập trang quản trị.');
            return;
        }
        window.location.href = 'admin.html';
    });
}

// --- Upload Logic ---

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFile(e.target.files[0]);
});

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert("Vui lòng chọn file hình ảnh!");
        return;
    }
    currentFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        imgPreview.src = e.target.result;
        imgPreview.classList.remove('hidden');
        uploadContent.classList.add('hidden');
        removeImgBtn.classList.remove('hidden');
        analyzeBtn.disabled = false;

        // Reset kết quả
        resPlaceholder.classList.remove('hidden');
        resContent.classList.add('hidden');
    };
    reader.readAsDataURL(file);
}

removeImgBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resetImage();
});

function resetImage() {
    currentFile = null;
    fileInput.value = "";
    imgPreview.src = "";
    imgPreview.classList.add('hidden');
    uploadContent.classList.remove('hidden');
    removeImgBtn.classList.add('hidden');
    analyzeBtn.disabled = true;
}

function clearBatchResults() {
    if (batchSummary) {
        batchSummary.innerText = 'Chưa có dữ liệu batch.';
    }
    if (batchResultTbody) {
        batchResultTbody.innerHTML = '';
    }
}

function clearAnalytics() {
    if (statTotalScans) statTotalScans.innerText = '0';
    if (statFakeRate) statFakeRate.innerText = '0%';
    if (statRealRate) statRealRate.innerText = '0%';
    if (statTopModel) statTopModel.innerText = '-';
    if (statAvgFake) statAvgFake.innerText = '0%';
    if (analyticsModelTbody) {
        analyticsModelTbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">Chưa có dữ liệu.</td></tr>';
    }
}

// --- Prediction Logic ---

analyzeBtn.addEventListener('click', async () => {
    if (!currentFile) return;

    analyzeBtn.disabled = true;
    analyzeBtn.querySelector('.fa-magnifying-glass').classList.add('hidden');
    analyzeBtn.querySelector('.loader').classList.remove('hidden');

    // Chuẩn bị FormData
    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('model_type', modelSelect.value);

    try {
        const res = await fetch(`${API_URL}/predict`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}` // Token xác thực
            },
            body: formData
        });

        if (res.status === 401) {
            alert("Phiên đăng nhập hết hạn, vui lòng đăng nhập lại.");
            logoutBtn.click();
            return;
        }

        const data = await res.json();
        if (res.ok) {
            if (data.remaining_tokens !== undefined && data.remaining_tokens !== null) {
                setAuthPredictionTokens(data.remaining_tokens);
                if (tokenCount) tokenCount.innerText = data.remaining_tokens;
            }
            displayResult(data);
        } else {
            alert(`Lỗi: ${data.detail || "Không thể phân tích ảnh"}`);
        }
    } catch (e) {
        alert("Lỗi kết nối đến API Server.");
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.querySelector('.fa-magnifying-glass').classList.remove('hidden');
        analyzeBtn.querySelector('.loader').classList.add('hidden');
    }
});

function displayResult(data) {
    resPlaceholder.classList.add('hidden');
    resContent.classList.remove('hidden');

    const effectiveLabel = getVerdictByThreshold(data.probability);
    const isFake = effectiveLabel === 'fake';

    // Cập nhật giao diện theo FAKE / REAL
    verdictBox.className = `verdict-box ${isFake ? 'fake' : 'real'}`;
    verdictIcon.innerHTML = isFake ? '<i class="fa-solid fa-triangle-exclamation"></i>' : '<i class="fa-solid fa-check"></i>';
    verdictText.innerText = isFake ? 'ẢNH GIẢ MẠO (AI)' : 'ẢNH THẬT (REAL)';

    // Cập nhật metrics
    resConf.innerText = data.confidence;
    resProb.innerText = data.probability.toFixed(4);

    resModel.innerText = MODEL_NAMES[data.model_used] || data.model_used;

    // FFT Visualization
    if (data.fft_base64) {
        document.getElementById('fft-container').classList.remove('hidden');
        document.getElementById('fft-image').src = `data:image/png;base64,${data.fft_base64}`;
    } else {
        document.getElementById('fft-container').classList.add('hidden');
    }

    // Hiệu ứng thanh Progress
    const probPercent = data.probability * 100;

    // Delay xíu để xem animation
    setTimeout(() => {
        probMarker.style.left = `${probPercent}%`;
    }, 100);
}

// Khởi chạy
init();
initSidebarNavigation();

// --- Dashboard Tabs & History Logic ---
function switchDashTab(tab) {
    const tabIds = [
        'single-scan',
        'batch-scan',
        'analytics',
        'history',
        'api-management',
        'settings'
    ];

    tabIds.forEach(id => {
        const pane = document.getElementById(`${id}-tab`);
        if (!pane) return;
        if (id === tab) {
            pane.classList.remove('hidden');
            pane.classList.add('active');
        } else {
            pane.classList.add('hidden');
            pane.classList.remove('active');
        }
    });

    sidebarItems.forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tab);
    });

    if (tab === 'history') {
        fetchHistory();
    }

    if (tab === 'analytics') {
        if (cachedHistoryItems.length > 0) {
            updateAnalytics(cachedHistoryItems);
        } else if (userSettings.autoLoadHistoryForAnalytics) {
            fetchHistory({ updateHistoryTable: false, updateAnalyticsOnly: true });
        } else {
            clearAnalytics();
        }
    }

    if (tab === 'api-management') {
        generateApiCurl();
        syncApiTokenPreview();
    }
}

async function fetchHistory(options = {}) {
    const {
        updateHistoryTable = true,
        updateAnalyticsOnly = false
    } = options;

    const tbody = document.getElementById('history-tbody');
    const badge = document.getElementById('history-badge');

    if (updateHistoryTable && tbody) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center"><div class="loader" style="position:static; margin:0 auto"></div></td></tr>';
    }

    try {
        const res = await fetch(`${API_URL}/history/`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (res.status === 401) {
            logoutBtn.click();
            return;
        }

        const data = await res.json();
        if (res.ok) {
            cachedHistoryItems = data.items || [];
            if (badge) {
                badge.innerText = data.total;
            }

            if (updateAnalyticsOnly || document.getElementById('analytics-tab')?.classList.contains('active')) {
                updateAnalytics(cachedHistoryItems);
            }

            if (updateHistoryTable) {
                if (cachedHistoryItems.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Chưa có dữ liệu phân tích nào.</td></tr>';
                    return;
                }

                let html = '';
                cachedHistoryItems.forEach(item => {
                    const effectiveLabel = getVerdictByThreshold(item.probability);
                    const isFake = effectiveLabel === 'fake';
                    const dateObj = new Date(item.created_at);
                    const timeStr = dateObj.toLocaleString('vi-VN');

                    html += `
                        <tr>
                            <td>${timeStr}</td>
                            <td><i class="fa-solid fa-user" style="color:var(--text-muted)"></i> ${item.username}</td>
                            <td title="${item.filename}">${item.filename.length > 20 ? item.filename.substring(0, 20) + '...' : item.filename}</td>
                            <td>${MODEL_NAMES[item.model_type] || item.model_type}</td>
                            <td>${(item.probability * 100).toFixed(2)}%</td>
                            <td class="${isFake ? 'fake' : 'real'}">${isFake ? 'FAKE' : 'REAL'}</td>
                        </tr>
                    `;
                });
                tbody.innerHTML = html;
            }
        } else if (updateHistoryTable) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--danger)">Lỗi: ${data.detail}</td></tr>`;
        }
    } catch (e) {
        if (updateHistoryTable) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--danger)">Lỗi kết nối.</td></tr>';
        }
    }
}

function updateAnalytics(items) {
    if (!items || items.length === 0) {
        clearAnalytics();
        return;
    }

    const total = items.length;
    const fakeCount = items.filter((x) => getVerdictByThreshold(x.probability) === 'fake').length;
    const realCount = total - fakeCount;
    const fakeRate = ((fakeCount / total) * 100).toFixed(1);
    const realRate = ((realCount / total) * 100).toFixed(1);
    const avgFake = ((items.reduce((sum, x) => sum + x.probability, 0) / total) * 100).toFixed(1);

    const byModel = {};
    items.forEach((item) => {
        byModel[item.model_type] = (byModel[item.model_type] || 0) + 1;
    });

    let topModel = '-';
    let topCount = 0;
    Object.keys(byModel).forEach((k) => {
        if (byModel[k] > topCount) {
            topCount = byModel[k];
            topModel = MODEL_NAMES[k] || k;
        }
    });

    statTotalScans.innerText = String(total);
    statFakeRate.innerText = `${fakeRate}%`;
    statRealRate.innerText = `${realRate}%`;
    statTopModel.innerText = topModel;
    statAvgFake.innerText = `${avgFake}%`;

    const sortedModels = Object.entries(byModel).sort((a, b) => b[1] - a[1]);
    analyticsModelTbody.innerHTML = sortedModels
        .map(([model, count]) => {
            const pct = ((count / total) * 100).toFixed(1);
            return `
                <tr>
                    <td>${MODEL_NAMES[model] || model}</td>
                    <td>${count}</td>
                    <td>${pct}%</td>
                </tr>
            `;
        })
        .join('');
}

function handleBatchFiles(files) {
    const validImageFiles = Array.from(files).filter((file) => file.type.startsWith('image/'));
    if (validImageFiles.length === 0) {
        batchFiles = [];
        batchSummary.innerText = 'Không có file ảnh hợp lệ. Hỗ trợ JPG, PNG, WEBP.';
        return;
    }
    batchFiles = validImageFiles.slice(0, 20);
    batchSummary.innerText = `Đã chọn ${batchFiles.length} ảnh cho batch scan.`;
}

async function runBatchScan() {
    if (!batchFiles.length) {
        alert('Vui lòng chọn ảnh trước khi quét hàng loạt.');
        return;
    }

    batchRunBtn.disabled = true;
    batchSummary.innerText = 'Đang phân tích hàng loạt...';
    batchResultTbody.innerHTML = '<tr><td colspan="4" style="text-align:center"><div class="loader" style="position:static; margin:0 auto"></div></td></tr>';

    const formData = new FormData();
    formData.append('model_type', batchModelSelect.value);
    batchFiles.forEach((file) => formData.append('files', file));

    try {
        const res = await fetch(`${API_URL}/predict/batch`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });

        if (res.status === 401) {
            alert('Phiên đăng nhập hết hạn, vui lòng đăng nhập lại.');
            logoutBtn.click();
            return;
        }

        const data = await res.json();
        if (!res.ok) {
            batchSummary.innerText = `Lỗi: ${data.detail || 'Không thể batch scan.'}`;
            batchResultTbody.innerHTML = '';
            return;
        }

        if (data.remaining_tokens !== undefined && data.remaining_tokens !== null) {
            setAuthPredictionTokens(data.remaining_tokens);
            if (tokenCount) tokenCount.innerText = data.remaining_tokens;
        }

        const results = data.results || [];
        const fakeCount = results.filter((x) => getVerdictByThreshold(x.probability || 0) === 'fake').length;
        batchSummary.innerText = `Hoàn tất ${results.length} ảnh. Fake: ${fakeCount}, Real: ${results.length - fakeCount}.`;

        batchResultTbody.innerHTML = results.map((item) => {
            if (item.label === 'error') {
                return `
                    <tr>
                        <td>${item.filename}</td>
                        <td>${MODEL_NAMES[item.model_used] || item.model_used}</td>
                        <td>N/A</td>
                        <td class="error">ERROR</td>
                    </tr>
                `;
            }

            const effectiveLabel = getVerdictByThreshold(item.probability || 0);
            const isFake = effectiveLabel === 'fake';
            return `
                <tr>
                    <td title="${item.filename}">${item.filename}</td>
                    <td>${MODEL_NAMES[item.model_used] || item.model_used}</td>
                    <td>${((item.probability || 0) * 100).toFixed(2)}%</td>
                    <td class="${isFake ? 'fake' : 'real'}">${isFake ? 'FAKE' : 'REAL'}</td>
                </tr>
            `;
        }).join('');
    } catch {
        batchSummary.innerText = 'Lỗi kết nối API khi batch scan.';
        batchResultTbody.innerHTML = '';
    } finally {
        batchRunBtn.disabled = false;
    }
}

function generateApiCurl() {
    if (!apiEndpointSelect || !apiCurlOutput) return;

    const selected = apiEndpointSelect.value;
    const authHeader = authToken ? `-H "Authorization: Bearer ${authToken}" ` : '';
    let command = '';

    if (selected === 'health') {
        command = 'curl -X GET "http://127.0.0.1:8000/"';
    } else if (selected === 'models') {
        command = 'curl -X GET "http://127.0.0.1:8000/models"';
    } else if (selected === 'history') {
        command = `curl -X GET "http://127.0.0.1:8000/history/" ${authHeader}`.trim();
    }

    apiCurlOutput.value = command;
}

async function testApiEndpoint() {
    if (!apiEndpointSelect || !apiTestResult) return;
    const selected = apiEndpointSelect.value;
    let endpoint = '/';

    if (selected === 'models') endpoint = '/models';
    if (selected === 'history') endpoint = '/history/';

    const headers = {};
    if (selected === 'history' && authToken) {
        headers.Authorization = `Bearer ${authToken}`;
    }

    apiTestResult.innerText = 'Đang test endpoint...';

    try {
        const res = await fetch(`${API_URL}${endpoint}`, { headers });
        const text = await res.text();
        apiTestResult.innerText = `HTTP ${res.status}: ${text.slice(0, 240)}${text.length > 240 ? '...' : ''}`;
    } catch {
        apiTestResult.innerText = 'Lỗi kết nối khi test endpoint.';
    }
}

function saveDashboardSettings() {
    userSettings.verdictThreshold = Number(settingsThreshold.value);
    userSettings.autoLoadHistoryForAnalytics = settingsAutoHistory.checked;
    userSettings.preferredModel = modelSelect.value;
    saveUserSettings();
    applySettingsToUI();
    settingsSaveMsg.innerText = 'Đã lưu cài đặt.';

    if (cachedHistoryItems.length) {
        if (document.getElementById('history-tab')?.classList.contains('active')) {
            fetchHistory();
        }
        updateAnalytics(cachedHistoryItems);
    }
}

function initWorkspaceSearch() {
    if (!workspaceSearchInput) return;
    workspaceSearchInput.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter') return;
        const q = workspaceSearchInput.value.trim().toLowerCase();
        if (!q) return;

        if (q.includes('batch') || q.includes('hàng loạt')) return switchDashTab('batch-scan');
        if (q.includes('analytics') || q.includes('phân tích') || q.includes('thống kê')) return switchDashTab('analytics');
        if (q.includes('history') || q.includes('lịch sử')) return switchDashTab('history');
        if (q.includes('api')) return switchDashTab('api-management');
        if (q.includes('setting') || q.includes('cài đặt')) return switchDashTab('settings');

        switchDashTab('single-scan');
    });
}

if (historyRefreshBtn) {
    historyRefreshBtn.addEventListener('click', () => fetchHistory());
}

if (batchDrop) {
    batchDrop.addEventListener('dragover', (e) => {
        e.preventDefault();
        batchDrop.classList.add('dragover');
    });
    batchDrop.addEventListener('dragleave', () => {
        batchDrop.classList.remove('dragover');
    });
    batchDrop.addEventListener('drop', (e) => {
        e.preventDefault();
        batchDrop.classList.remove('dragover');
        handleBatchFiles(e.dataTransfer.files);
    });
}

if (batchFileInput) {
    batchFileInput.addEventListener('change', (e) => {
        handleBatchFiles(e.target.files);
    });
}

if (batchRunBtn) {
    batchRunBtn.addEventListener('click', runBatchScan);
}

if (apiEndpointSelect) {
    apiEndpointSelect.addEventListener('change', generateApiCurl);
}

if (apiGenerateBtn) {
    apiGenerateBtn.addEventListener('click', generateApiCurl);
}

if (apiCopyBtn) {
    apiCopyBtn.addEventListener('click', async () => {
        if (!apiCurlOutput.value) generateApiCurl();
        try {
            await navigator.clipboard.writeText(apiCurlOutput.value);
            apiTestResult.innerText = 'Đã copy lệnh curl.';
        } catch {
            apiTestResult.innerText = 'Không thể copy tự động. Vui lòng copy thủ công.';
        }
    });
}

if (apiTestBtn) {
    apiTestBtn.addEventListener('click', testApiEndpoint);
}

if (settingsThreshold) {
    settingsThreshold.addEventListener('input', () => {
        settingsThresholdValue.innerText = `${settingsThreshold.value}%`;
    });
}

if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', saveDashboardSettings);
}

initWorkspaceSearch();
init();

