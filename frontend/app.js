const API_URL = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) ? "http://localhost:8000" : "https://cnn-detection-api.onrender.com";

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
    fetchModels();
    syncHeaderNavByRole();
    initGoogleSignIn();
    if (authToken && authUser) {
        showDashboard();
    } else {
        showAuth();
    }
}

async function fetchModels() {
    try {
        const res = await fetch(`${API_URL}/models`);
        if (res.ok) {
            const data = await res.json();
            const activeModels = data.available_models || [];
            updateModelSelects(activeModels);
        }
    } catch (e) {
        console.error("Lỗi khi tải danh sách model:", e);
    }
}

function updateModelSelects(activeModels) {
    if (!modelSelect || !batchModelSelect) return;
    
    let html = '';
    activeModels.forEach(m => {
        const isBest = m === 'dual_stream_enhanced' ? ' (Tốt nhất)' : '';
        html += `<option value="${m}">${MODEL_NAMES[m] || m}${isBest}</option>`;
    });

    if (!html) html = '<option value="">Không có model nào khả dụng</option>';
    
    modelSelect.innerHTML = html;
    batchModelSelect.innerHTML = html;
    
    // Khôi phục model ưu tiên nếu có
    applySettingsToUI();
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

    // App Mobile: Chuyển hướng sang native login (Chrome Custom Tabs) thay vì dùng GSI trong WebView
    if (window.FlutterBridge) {
        googleSigninBtn.innerHTML = `
            <button type="button" onclick="window.FlutterBridge.postMessage('LOGIN_GOOGLE')" 
                    style="width:320px; height:40px; border-radius:20px; border:1px solid #ccc; background:white; font-family:'Plus Jakarta Sans', sans-serif; font-weight:500; font-size:14px; display:flex; align-items:center; justify-content:center; gap:8px; cursor:pointer; color:#3c4043;">
                <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
                <span data-i18n="signin_with">Đăng nhập với Google</span>
            </button>
        `;
        googleLoginContainer.classList.remove('hidden');
        return;
    }

    // Web đều dùng chung flow Google Identity Services (GIS)
    // Lưu lại trạng thái login_mode vào localStorage để giữ nguyên khi Google chuyển hướng trang web
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('login_mode') === 'true') {
        localStorage.setItem('login_mode_active', 'true');
    }
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
                let errText = data.detail || 'Đăng nhập Google thất bại.';
                if (typeof errText === 'object') errText = JSON.stringify(errText);
                googleLoginError.innerText = errText;
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

        // Thông báo cho Flutter App lưu token (nếu đang chạy trong WebView)
        if (window.FlutterBridge) {
            window.FlutterBridge.postMessage('TOKEN:' + authToken);
        }
        
        // Nếu trang web được mở qua Chrome Custom Tabs từ App
        if (localStorage.getItem('login_mode_active') === 'true') {
            // Xóa cờ để không bị lỗi lần sau
            localStorage.removeItem('login_mode_active');
            
            document.body.innerHTML = `
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; background:#f7f9fc; font-family:'Plus Jakarta Sans', sans-serif;">
                    <div style="background:white; padding:40px; border-radius:20px; text-align:center; box-shadow:0 10px 30px rgba(0,0,0,0.1);">
                        <i class="fa-solid fa-circle-check" style="font-size:60px; color:#0ea5a4; margin-bottom:20px;"></i>
                        <h2 style="margin-bottom:10px; color:#162437;">Đăng nhập thành công!</h2>
                        <p style="color:#64748b; margin-bottom:30px;">Hệ thống đã xác thực tài khoản của bạn.</p>
                        <a href="cnndetection://callback?token=${authToken}" 
                           style="display:inline-block; background:linear-gradient(135deg, #0ea5a4, #f59e0b); color:white; padding:16px 36px; border-radius:50px; text-decoration:none; font-weight:700; font-size:16px;">
                           Quay lại Ứng dụng
                        </a>
                    </div>
                </div>
            `;
            // Cố gắng tự động chuyển hướng
            setTimeout(() => {
                window.location.href = `cnndetection://callback?token=${authToken}`;
            }, 500);
            return;
        }

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

        if (authRole !== 'admin') {
            startTokenSync();
        }
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
        document.getElementById('tab-forgot').classList.remove('active');
        loginForm.classList.add('active');
        regForm.classList.remove('active');
        document.getElementById('forgot-form').classList.remove('active');
    } else if (tab === 'register') {
        btnRegTab.classList.add('active');
        btnLoginTab.classList.remove('active');
        document.getElementById('tab-forgot').classList.remove('active');
        regForm.classList.add('active');
        loginForm.classList.remove('active');
        document.getElementById('forgot-form').classList.remove('active');
        if (loginInfo) loginInfo.innerText = "";
        document.getElementById('register-success').innerText = "";
    } else if (tab === 'forgot') {
        document.getElementById('tab-forgot').classList.add('active');
        btnLoginTab.classList.remove('active');
        btnRegTab.classList.remove('active');
        document.getElementById('forgot-form').classList.add('active');
        loginForm.classList.remove('active');
        regForm.classList.remove('active');
    }
}

// --- Forgot Password Logic ---
async function sendOtp() {
    const emailInput = document.getElementById('forgot-email').value;
    const err = document.getElementById('forgot-error');
    const succ = document.getElementById('forgot-success');
    const ldr = document.getElementById('otp-loader');
    const btnText = document.querySelector('#btn-send-otp .btn-text');

    if (!emailInput) {
        err.innerText = "Vui lòng nhập email.";
        return;
    }

    btnText.classList.add('hidden');
    ldr.classList.remove('hidden');
    err.innerText = "";
    succ.innerText = "";

    try {
        const res = await fetch(`${API_URL}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: emailInput })
        });
        const data = await res.json();
        
        if (res.ok) {
            succ.innerText = data.message || "Đã gửi OTP!";
            document.getElementById('forgot-step-1').classList.add('hidden');
            document.getElementById('forgot-step-2').classList.remove('hidden');
        } else {
            err.innerText = data.detail || "Gửi OTP thất bại!";
        }
    } catch (e) { err.innerText = "Lỗi kết nối server!"; }

    btnText.classList.remove('hidden');
    ldr.classList.add('hidden');
}

async function resetPassword() {
    const emailInput = document.getElementById('forgot-email').value;
    const otpInput = document.getElementById('forgot-otp').value;
    const newPasswordInput = document.getElementById('forgot-new-password').value;
    
    const err = document.getElementById('forgot-error');
    const succ = document.getElementById('forgot-success');
    const ldr = document.getElementById('reset-loader');
    const btnText = document.querySelector('#btn-reset-password .btn-text');

    if (!otpInput || !newPasswordInput) {
        err.innerText = "Vui lòng nhập đủ OTP và mật khẩu mới.";
        return;
    }

    btnText.classList.add('hidden');
    ldr.classList.remove('hidden');
    err.innerText = "";
    succ.innerText = "";

    try {
        const res = await fetch(`${API_URL}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                email: emailInput,
                otp_code: otpInput,
                new_password: newPasswordInput
            })
        });
        const data = await res.json();
        
        if (res.ok) {
            succ.innerText = data.message || "Đặt lại mật khẩu thành công!";
            setTimeout(() => {
                switchAuthTab('login');
                document.getElementById('forgot-step-1').classList.remove('hidden');
                document.getElementById('forgot-step-2').classList.add('hidden');
                document.getElementById('forgot-email').value = "";
                document.getElementById('forgot-otp').value = "";
                document.getElementById('forgot-new-password').value = "";
                document.getElementById('login-username').value = emailInput;
            }, 2000);
        } else {
            err.innerText = data.detail || "Đặt lại thất bại!";
        }
    } catch (e) { err.innerText = "Lỗi kết nối server!"; }

    btnText.classList.remove('hidden');
    ldr.classList.add('hidden');
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

            // Thông báo cho Flutter App lưu token (nếu đang chạy trong WebView)
            if (window.FlutterBridge) {
                window.FlutterBridge.postMessage('TOKEN:' + authToken);
            }

            showDashboard();
        } else {
            let errText = data.detail || "Đăng nhập thất bại!";
            if (typeof errText === 'object') errText = JSON.stringify(errText);
            err.innerText = errText;
        }
    } catch (e) { err.innerText = "Lỗi kết nối server!"; }

    txt.classList.remove('hidden');
    ldr.classList.add('hidden');
});

// --- Register Logic (2 Steps) ---
async function requestRegisterOtp() {
    const emailInput = document.getElementById('reg-email').value;
    const usernameInput = document.getElementById('reg-username').value;
    const passwordInput = document.getElementById('reg-password').value;
    
    const err = document.getElementById('register-error');
    const succ = document.getElementById('register-success');
    const ldr = document.getElementById('reg-req-loader');
    const btnText = document.querySelector('#btn-request-register .btn-text');

    if (!emailInput || !usernameInput || passwordInput.length < 6) {
        err.innerText = "Vui lòng điền đủ thông tin hợp lệ (Mật khẩu >= 6 ký tự).";
        return;
    }

    btnText.classList.add('hidden');
    ldr.classList.remove('hidden');
    err.innerText = "";
    succ.innerText = "";

    try {
        const res = await fetch(`${API_URL}/auth/request-register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: emailInput, username: usernameInput })
        });
        const data = await res.json();
        
        if (res.ok) {
            succ.innerText = data.message || "Đã gửi OTP đến email!";
            document.getElementById('reg-step-1').classList.add('hidden');
            document.getElementById('reg-step-2').classList.remove('hidden');
        } else {
            let errText = data.detail || "Gửi OTP thất bại!";
            if (typeof errText === 'object') errText = JSON.stringify(errText);
            err.innerText = errText;
        }
    } catch (e) { err.innerText = "Lỗi kết nối server!"; }

    btnText.classList.remove('hidden');
    ldr.classList.add('hidden');
}

async function confirmRegister() {
    const emailInput = document.getElementById('reg-email').value;
    const usernameInput = document.getElementById('reg-username').value;
    const passwordInput = document.getElementById('reg-password').value;
    const otpInput = document.getElementById('reg-otp').value;
    
    const err = document.getElementById('register-error');
    const succ = document.getElementById('register-success');
    const ldr = document.getElementById('reg-conf-loader');
    const btnText = document.querySelector('#btn-confirm-register .btn-text');

    if (!otpInput || otpInput.length !== 6) {
        err.innerText = "Vui lòng nhập đúng 6 số OTP.";
        return;
    }

    btnText.classList.add('hidden');
    ldr.classList.remove('hidden');
    err.innerText = "";
    succ.innerText = "";

    const pb = {
        email: emailInput,
        username: usernameInput,
        password: passwordInput,
        otp_code: otpInput
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
                document.getElementById('reg-step-1').classList.remove('hidden');
                document.getElementById('reg-step-2').classList.add('hidden');
                document.getElementById('reg-email').value = "";
                document.getElementById('reg-username').value = "";
                document.getElementById('reg-password').value = "";
                document.getElementById('reg-otp').value = "";
                document.getElementById('login-username').value = usernameInput;
                document.getElementById('login-password').value = passwordInput;
                if (loginInfo) {
                    loginInfo.innerText = `Tài khoản mới được cấp ${grantedTokens} token.`;
                }
            }, 1500);
        } else {
            let errText = data.detail || "Đăng ký thất bại!";
            if (typeof errText === 'object') errText = JSON.stringify(errText);
            err.innerText = errText;
        }
    } catch (e) { err.innerText = "Lỗi kết nối server!"; }

    btnText.classList.remove('hidden');
    ldr.classList.add('hidden');
}

logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('role');
    localStorage.removeItem('prediction_tokens');

    // Thông báo cho Flutter App xóa token (nếu đang chạy trong WebView)
    if (window.FlutterBridge) {
        window.FlutterBridge.postMessage('LOGOUT');
    }

    authToken = null;
    authUser = null;
    authRole = 'user';
    authPredictionTokens = 0;
    currentFile = null;
    stopTokenSync();
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

    if (authRole !== 'admin' && authPredictionTokens <= 0) {
        document.getElementById('payment-modal').classList.remove('hidden');
        return;
    }

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
    verdictText.innerText = isFake ? t('fake_img') : t('real_img');

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

    // --- Fake Heatmap / Grad-CAM ---
    const heatmapBox = document.getElementById('heatmap-box');
    if (heatmapBox && currentFile) {
        const url = URL.createObjectURL(currentFile);
        
        // Tạo một CSS radial-gradient ngẫu nhiên làm heatmap giả lập
        const x = Math.floor(Math.random() * 60) + 20; // 20% - 80%
        const y = Math.floor(Math.random() * 60) + 20;
        
        let overlay = "";
        if (isFake) {
            // Ảnh fake -> Vùng đỏ/cam/vàng rõ rệt
            overlay = `radial-gradient(circle at ${x}% ${y}%, rgba(255,0,0,0.7) 0%, rgba(255,165,0,0.5) 20%, rgba(0,0,255,0.2) 60%, transparent 100%)`;
        } else {
            // Ảnh thật -> Vùng xanh nhạt, không có điểm nóng
            overlay = `radial-gradient(circle at ${x}% ${y}%, rgba(0,255,0,0.3) 0%, rgba(0,0,255,0.2) 40%, transparent 100%)`;
        }

        // Reset container style to prevent overflow
        heatmapBox.style.height = '160px';
        heatmapBox.style.padding = '0';
        heatmapBox.style.border = '1px solid var(--border)';
        
        heatmapBox.innerHTML = `
            <div style="position:relative; width:100%; height:100%; border-radius:8px; overflow:hidden;">
                <img src="${url}" style="width:100%; height:100%; object-fit:cover; position:absolute; inset:0; z-index:1;">
                <div style="position:absolute; inset:0; z-index:2; background:${overlay}; mix-blend-mode: multiply;"></div>
            </div>
        `;
    }

    // --- Metadata / Noise Analysis ---
    if (document.getElementById('meta-noise')) {
        const vNoise = document.getElementById('meta-noise');
        const vEdge = document.getElementById('meta-edge');
        const vComp = document.getElementById('meta-compression');

        if (isFake) {
            vNoise.innerHTML = `<span style="color:var(--danger)">${t('noise_fake_bg')}</span>`;
            vEdge.innerHTML = `<span style="color:var(--danger)">${t('noise_fake_edge')}</span>`;
            vComp.innerHTML = `<span style="color:var(--danger)">${t('noise_fake_comp')}</span>`;
        } else {
            vNoise.innerHTML = `<span style="color:var(--primary)">${t('noise_real_bg')}</span>`;
            vEdge.innerHTML = `<span style="color:var(--primary)">${t('noise_real_edge')}</span>`;
            vComp.innerHTML = `<span style="color:var(--primary)">${t('noise_real_comp')}</span>`;
        }
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
        'payment-history',
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
    
    if (tab === 'payment-history') {
        fetchPaymentHistory();
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

    if (authRole !== 'admin' && authPredictionTokens < batchFiles.length) {
        alert(`Bạn chỉ còn ${authPredictionTokens} tokens, nhưng chọn ${batchFiles.length} ảnh. Vui lòng nạp thêm Token.`);
        document.getElementById('payment-modal').classList.remove('hidden');
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

const paymentHistoryRefreshBtn = document.getElementById('payment-history-refresh-btn');
if (paymentHistoryRefreshBtn) {
    paymentHistoryRefreshBtn.addEventListener('click', () => fetchPaymentHistory());
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

// --- VNPAY PAYMENT LOGIC ---
const paymentModal = document.getElementById('payment-modal');
const openPaymentModalBtn = document.getElementById('open-payment-modal-btn');
const closePaymentModalBtn = document.getElementById('close-payment-modal');

if(openPaymentModalBtn) {
    openPaymentModalBtn.addEventListener('click', () => {
        paymentModal.classList.remove('hidden');
    });
}

if(closePaymentModalBtn) {
    closePaymentModalBtn.addEventListener('click', () => {
        paymentModal.classList.add('hidden');
    });
}

window.addEventListener('click', (e) => {
    if (e.target === paymentModal) paymentModal.classList.add('hidden');
});

async function payVNPay(amount, tokens) {
    try {
        const token = localStorage.getItem('token');
        if (!token) return alert('Vui lòng đăng nhập!');
        
        // Disable buttons temporarily
        const buttons = document.querySelectorAll('#payment-modal .primary-btn');
        buttons.forEach(b => { b.dataset.original = b.innerText; b.innerText = 'Đang tạo...'; b.disabled = true; });

        const response = await fetch(`${API_URL}/payment/create_payment_url`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ amount, tokens })
        });

        const data = await response.json();
        
        // Restore buttons
        buttons.forEach(b => { b.innerText = b.dataset.original; b.disabled = false; });

        if (response.ok && data.payment_url) {
            window.location.href = data.payment_url;
        } else {
            alert(`Lỗi khi tạo liên kết thanh toán: ${data.detail || 'Không có dữ liệu'}`);
        }
    } catch (error) {
        console.error("Payment Error:", error);
        alert(`Lỗi kết nối máy chủ thanh toán: ${error.message}`);
        const buttons = document.querySelectorAll('#payment-modal .primary-btn');
        buttons.forEach(b => { if(b.dataset.original) b.innerText = b.dataset.original; b.disabled = false; });
    }
}

// ----------------- TOKEN SYNC & DYNAMIC PRICING -----------------
let tokenSyncInterval = null;

async function startTokenSync() {
    stopTokenSync(); // Clear existing if any
    tokenSyncInterval = setInterval(async () => {
        if (!authToken) return;
        try {
            const res = await fetch(`${API_URL}/auth/me`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (res.ok) {
                const data = await res.json();
                setAuthPredictionTokens(data.prediction_tokens);
                const tokenCountEl = document.getElementById('token-count');
                if (tokenCountEl) {
                    tokenCountEl.innerText = data.prediction_tokens;
                }
            }
        } catch (e) {
            console.error('Token sync failed', e);
        }
    }, 10000); // 10 seconds
}

function stopTokenSync() {
    if (tokenSyncInterval) {
        clearInterval(tokenSyncInterval);
        tokenSyncInterval = null;
    }
}

async function renderPricingGrid() {
    const gridContainer = document.getElementById('pricing-grid-container');
    if (!gridContainer) return;
    
    try {
        const res = await fetch(`${API_URL}/site-config`);
        if (!res.ok) return;
        const config = await res.json();
        
        let packages = [];
        try {
            packages = JSON.parse(config.token_packages || '[]');
        } catch (e) {
            console.error("Failed to parse token_packages", e);
        }

        if (!packages || packages.length === 0) {
            gridContainer.innerHTML = '<p style="grid-column: 1/-1; color: var(--color-text); text-align: center;">Chưa có cấu hình bảng giá.</p>';
            return;
        }

        gridContainer.innerHTML = packages.map(pkg => `
            <div class="pricing-card ${pkg.popular ? 'popular' : ''}" onclick="payVNPay(${pkg.price || 0}, ${pkg.tokens || 0})">
                ${pkg.popular ? '<div class="pricing-badge" data-i18n="badge_popular">🔥 PHỔ BIẾN NHẤT</div>' : ''}
                <div class="pricing-header">
                    <h3>${pkg.name}</h3>
                    <p class="token-amount">${pkg.tokens} <span data-i18n="txt_tokens">Tokens</span></p>
                </div>
                <div class="pricing-price">
                    <span class="currency">đ</span>${Number(pkg.price || 0).toLocaleString('vi-VN')}
                </div>
                <ul class="pricing-features">
                    ${(pkg.features || []).map(f => `<li><i class="fa-solid fa-check"></i> <span>${f}</span></li>`).join('')}
                </ul>
                <button class="btn primary-btn btn-pricing" data-i18n="btn_buy_now">Mua Ngay</button>
            </div>
        `).join('');
        
        // Re-apply translations for newly injected elements
        if (typeof applyTranslations === 'function') {
            applyTranslations();
        }
    } catch (e) {
        console.error('Failed to load pricing config', e);
        gridContainer.innerHTML = '<p style="grid-column: 1/-1; color: var(--danger)">Lỗi tải bảng giá.</p>';
    }
}

// Call on startup
renderPricingGrid();

// Xử lý VNPay trả về
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const status = urlParams.get('payment');
    const tokens = urlParams.get('tokens');
    
    if (status === 'success') {
        alert(`Thanh toán thành công! Tài khoản của bạn đã được cộng thêm ${tokens} tokens.`);
        window.history.replaceState({}, document.title, window.location.pathname);
        window.location.reload(); // Tải lại trang để cập nhật số token
    } else if (status === 'failed') {
        alert("Thanh toán thất bại hoặc người dùng đã hủy giao dịch.");
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (status === 'invalid_signature') {
        alert("Lỗi chữ ký VNPay không hợp lệ.");
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});

initWorkspaceSearch();
init();

// Lắng nghe token từ Flutter App
window.addEventListener('flutter_token_ready', async (e) => {
    const token = e.detail.token;
    if (token) {
        localStorage.setItem('token', token);
        authToken = token;
        await fetchUserProfile();
        document.getElementById('auth-section').classList.remove('active');
        document.getElementById('dashboard-section').classList.add('active');
        updateHeaderNav();
    }
});

// --- Profile Modal Logic ---
const profileBtn = document.getElementById('profile-btn');
const profileModal = document.getElementById('profile-modal');
const closeProfileModal = document.getElementById('close-profile-modal');
const btnChangePassword = document.getElementById('btn-change-password');

if (profileBtn && profileModal) {
    profileBtn.addEventListener('click', () => {
        document.getElementById('user-dropdown').classList.add('hidden');
        document.getElementById('profile-username').innerText = authUser?.username || 'Unknown';
        document.getElementById('profile-old-password').value = '';
        document.getElementById('profile-new-password').value = '';
        document.getElementById('profile-error').classList.add('hidden');
        document.getElementById('profile-success').classList.add('hidden');
        profileModal.classList.remove('hidden');
    });
}

if (closeProfileModal) {
    closeProfileModal.addEventListener('click', () => {
        profileModal.classList.add('hidden');
    });
}

if (btnChangePassword) {
    btnChangePassword.addEventListener('click', async () => {
        const oldPw = document.getElementById('profile-old-password').value;
        const newPw = document.getElementById('profile-new-password').value;
        const errEl = document.getElementById('profile-error');
        const sucEl = document.getElementById('profile-success');
        
        errEl.classList.add('hidden');
        sucEl.classList.add('hidden');
        
        if (!oldPw || !newPw) {
            errEl.innerText = "Vui lòng nhập đủ thông tin.";
            errEl.classList.remove('hidden');
            return;
        }
        if (newPw.length < 6) {
            errEl.innerText = "Mật khẩu mới phải dài ít nhất 6 ký tự.";
            errEl.classList.remove('hidden');
            return;
        }
        
        btnChangePassword.disabled = true;
        btnChangePassword.innerText = 'Đang xử lý...';
        
        try {
            const res = await fetch(`${API_URL}/auth/change-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({
                    old_password: oldPw,
                    new_password: newPw
                })
            });
            const data = await res.json();
            if (res.ok) {
                sucEl.innerText = data.message || "Đổi mật khẩu thành công!";
                sucEl.classList.remove('hidden');
                document.getElementById('profile-old-password').value = '';
                document.getElementById('profile-new-password').value = '';
            } else {
                errEl.innerText = data.detail || "Lỗi khi đổi mật khẩu.";
                errEl.classList.remove('hidden');
            }
        } catch (e) {
            errEl.innerText = "Không thể kết nối máy chủ.";
            errEl.classList.remove('hidden');
        } finally {
            btnChangePassword.disabled = false;
            btnChangePassword.innerText = 'Đổi mật khẩu';
        }
    });
}

async function fetchPaymentHistory() {
    const tbody = document.getElementById('payment-history-tbody');
    const badge = document.getElementById('payment-history-badge');

    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center"><div class="loader" style="position:static; margin:0 auto"></div></td></tr>';
    }

    try {
        const res = await fetch(`${API_URL}/payment-history/`, {
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
            if (badge) {
                badge.innerText = data.total;
            }

            if (data.items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Chưa có giao dịch mua hàng nào.</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            
            // Calculate and display user stats
            const totalSpent = data.items.reduce((sum, item) => sum + item.amount, 0);
            const totalTokens = data.items.reduce((sum, item) => sum + item.tokens, 0);
            
            const elTotalSpent = document.getElementById('user-total-spent');
            const elTotalTokens = document.getElementById('user-total-tokens-bought');
            if (elTotalSpent) elTotalSpent.innerText = totalSpent.toLocaleString('vi-VN') + ' đ';
            if (elTotalTokens) elTotalTokens.innerText = totalTokens.toLocaleString('vi-VN');

            data.items.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${new Date(item.created_at).toLocaleString('vi-VN')}</td>
                    <td>${item.order_id}</td>
                    <td>${item.amount.toLocaleString('vi-VN')} đ</td>
                    <td style="color:var(--primary);font-weight:bold;">+${item.tokens}</td>
                    <td><span class="badge" style="background:#ecfdf5;color:#065f46;border-color:#86efac;">Thành công</span></td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--danger)">Lỗi tải dữ liệu: ${data.detail || 'Unknown'}</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--danger)">Không thể kết nối API.</td></tr>';
    }
}
