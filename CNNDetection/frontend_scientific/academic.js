const API_URL = ["localhost", "127.0.0.1", ""].includes(window.location.hostname) ? "http://localhost:8000" : "https://cnn-detection-api.onrender.com";

// --- Global State ---
let authToken = localStorage.getItem('token');
let authUser = localStorage.getItem('user');
let authRole = localStorage.getItem('role') || 'user';
let authPredictionTokens = Number(localStorage.getItem('prediction_tokens')) || 0;
let userSettings = { verdictThreshold: 85, autoLoadHistory: true };

const MODEL_NAMES = {
    'dual_stream_enhanced': 'Dual Stream Enhanced',
    'dual_stream_resnet': 'Dual Stream ResNet18',
    'resnet50': 'ResNet-50'
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    initSettings();
    const path = window.location.pathname;
    
    if (path.includes('dashboard.html')) {
        if (!authToken) {
            window.location.href = 'login.html';
            return;
        }
        initDashboard();
    } else if (path.includes('admin.html')) {
        if (!authToken || authRole !== 'admin') {
            window.location.href = 'login.html';
            return;
        }
        initAdmin();
    } else if (path.includes('login.html')) {
        if (authToken) {
            window.location.href = 'dashboard.html';
            return;
        }
        initAuth();
    }
    
    // Global logout button binding
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            logout();
        });
    }
});

// --- Utility Functions ---
function formatApiError(detail, fallback) {
    if (!detail) return fallback;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(e => e.msg).join(', ');
    if (typeof detail === 'object') return JSON.stringify(detail);
    return fallback;
}

function showMsg(elementId, text, isError = false) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = text;
    el.className = `msg-box ${isError ? 'error' : 'success'}`;
    el.style.display = 'block';
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('role');
    window.location.href = 'login.html';
}

function hideMsg(elId) {
    const el = document.getElementById(elId);
    if (el) el.classList.add('hidden');
}

// --- Auth Logic ---
function initAuth() {
    const tabs = document.querySelectorAll('.auth-tab');
    const sections = document.querySelectorAll('.auth-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.getAttribute('data-target');
            document.getElementById(`section-${target}`).classList.add('active');
            
            // Hide forgot password tab if switching away
            if (target !== 'forgot') {
                document.querySelector('.auth-tab[data-target="forgot"]').style.display = 'none';
            }
        });
    });

    document.querySelectorAll('.switch-tab').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const target = btn.getAttribute('data-target');
            if (target === 'forgot') {
                document.querySelector('.auth-tab[data-target="forgot"]').style.display = 'block';
            }
            document.querySelector(`.auth-tab[data-target="${target}"]`).click();
        });
    });

    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = loginForm.querySelector('button[type="submit"]');
            const loader = btn.querySelector('.loader');
            const btnText = btn.querySelector('.btn-text');
            
            hideMsg('login-msg');
            btnText.classList.add('hidden');
            loader.classList.remove('hidden');

            const payload = {
                username: document.getElementById('login-username').value,
                password: document.getElementById('login-password').value
            };

            try {
                const res = await fetch(`${API_URL}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    localStorage.setItem('token', data.access_token);
                    localStorage.setItem('user', data.username);
                    localStorage.setItem('role', data.role);
                    localStorage.setItem('prediction_tokens', data.prediction_tokens || 0);
                    window.location.href = 'dashboard.html';
                } else {
                    showMsg('login-msg', formatApiError(data.detail, 'Đăng nhập thất bại'), true);
                }
            } catch (err) {
                showMsg('login-msg', 'Lỗi kết nối máy chủ.', true);
            } finally {
                btnText.classList.remove('hidden');
                loader.classList.add('hidden');
            }
        });
    }

    // Google Auth Init
    fetch(`${API_URL}/auth/google/config`)
        .then(res => res.json())
        .then(data => {
            if (data.client_id && window.google) {
                google.accounts.id.initialize({
                    client_id: data.client_id,
                    callback: handleCredentialResponse
                });
                google.accounts.id.renderButton(
                    document.getElementById("google-signin-btn"),
                    { theme: "outline", size: "large", text: "continue_with" }
                );
            }
        }).catch(e => console.log('Google login not configured'));

    async function handleCredentialResponse(response) {
        showMsg('login-msg', 'Đang xác thực Google...', false);
        try {
            const res = await fetch(`${API_URL}/auth/google`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ credential: response.credential })
            });
            const data = await res.json();
            if (res.ok && data.access_token) {
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('user', data.username);
                localStorage.setItem('role', data.role);
                localStorage.setItem('prediction_tokens', data.prediction_tokens || 0);
                window.location.href = 'dashboard.html';
            } else {
                showMsg('login-msg', formatApiError(data.detail, 'Đăng nhập Google thất bại'), true);
            }
        } catch (err) {
            showMsg('login-msg', 'Lỗi kết nối máy chủ.', true);
        }
    }

    // Register Logic
    const btnReqReg = document.getElementById('btn-req-reg');
    if (btnReqReg) {
        btnReqReg.addEventListener('click', async () => {
            const email = document.getElementById('reg-email').value;
            const username = document.getElementById('reg-username').value;
            const password = document.getElementById('reg-password').value;
            if (!email || !username || password.length < 6) {
                showMsg('reg-msg', 'Vui lòng điền đầy đủ thông tin. Mật khẩu ít nhất 6 ký tự.', true);
                return;
            }
            hideMsg('reg-msg');
            const loader = btnReqReg.querySelector('.loader');
            const btnText = btnReqReg.querySelector('.btn-text');
            btnText.classList.add('hidden');
            loader.classList.remove('hidden');

            try {
                const res = await fetch(`${API_URL}/auth/request-otp`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, username, password })
                });
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('reg-step-1').classList.add('hidden');
                    document.getElementById('reg-step-2').classList.remove('hidden');
                    showMsg('reg-msg', 'Mã OTP đã được gửi đến email của bạn.');
                } else {
                    showMsg('reg-msg', formatApiError(data.detail, 'Lỗi đăng ký'), true);
                }
            } catch(e) {
                showMsg('reg-msg', 'Lỗi kết nối máy chủ', true);
            } finally {
                btnText.classList.remove('hidden');
                loader.classList.add('hidden');
            }
        });
    }

    const btnConfReg = document.getElementById('btn-conf-reg');
    if (btnConfReg) {
        btnConfReg.addEventListener('click', async () => {
            const email = document.getElementById('reg-email').value;
            const otpInput = document.getElementById('reg-otp').value;
            if (!otpInput || otpInput.length !== 6) {
                showMsg('reg-msg', 'Mã OTP phải gồm 6 chữ số.', true);
                return;
            }
            hideMsg('reg-msg');
            const loader = btnConfReg.querySelector('.loader');
            const btnText = btnConfReg.querySelector('.btn-text');
            btnText.classList.add('hidden');
            loader.classList.remove('hidden');

            try {
                const res = await fetch(`${API_URL}/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, otp_code: otpInput })
                });
                const data = await res.json();
                if (res.ok) {
                    showMsg('reg-msg', 'Đăng ký thành công! Đang chuyển hướng...');
                    setTimeout(() => {
                        document.querySelector('.auth-tab[data-target="login"]').click();
                        document.getElementById('login-username').value = document.getElementById('reg-username').value;
                    }, 1500);
                } else {
                    showMsg('reg-msg', formatApiError(data.detail, 'Mã OTP không hợp lệ'), true);
                }
            } catch(e) {
                showMsg('reg-msg', 'Lỗi kết nối máy chủ', true);
            } finally {
                btnText.classList.remove('hidden');
                loader.classList.add('hidden');
            }
        });
    }

    // Forgot Password Logic
    const btnSendOtp = document.getElementById('btn-send-otp');
    if (btnSendOtp) {
        btnSendOtp.addEventListener('click', async () => {
            const email = document.getElementById('forgot-email').value;
            if (!email) {
                showMsg('forgot-msg', 'Vui lòng nhập email.', true);
                return;
            }
            hideMsg('forgot-msg');
            const loader = btnSendOtp.querySelector('.loader');
            const btnText = btnSendOtp.querySelector('.btn-text');
            btnText.classList.add('hidden');
            loader.classList.remove('hidden');

            try {
                const res = await fetch(`${API_URL}/auth/request-reset-otp?email=${encodeURIComponent(email)}`, { method: 'POST' });
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('forgot-step-1').classList.add('hidden');
                    document.getElementById('forgot-step-2').classList.remove('hidden');
                    showMsg('forgot-msg', 'Mã OTP đã được gửi đến email của bạn.');
                } else {
                    showMsg('forgot-msg', formatApiError(data.detail, 'Lỗi gửi OTP'), true);
                }
            } catch(e) {
                showMsg('forgot-msg', 'Lỗi kết nối máy chủ', true);
            } finally {
                btnText.classList.remove('hidden');
                loader.classList.add('hidden');
            }
        });
    }

    const btnResetPwd = document.getElementById('btn-reset-password');
    if (btnResetPwd) {
        btnResetPwd.addEventListener('click', async () => {
            const email = document.getElementById('forgot-email').value;
            const otpInput = document.getElementById('forgot-otp').value;
            const newPassword = document.getElementById('forgot-new-password').value;
            if (!otpInput || newPassword.length < 6) {
                showMsg('forgot-msg', 'Vui lòng điền đủ OTP và mật khẩu mới (tối thiểu 6 ký tự).', true);
                return;
            }
            hideMsg('forgot-msg');
            const loader = btnResetPwd.querySelector('.loader');
            const btnText = btnResetPwd.querySelector('.btn-text');
            btnText.classList.add('hidden');
            loader.classList.remove('hidden');

            try {
                const res = await fetch(`${API_URL}/auth/reset-password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, otp_code: otpInput, new_password: newPassword })
                });
                const data = await res.json();
                if (res.ok) {
                    showMsg('forgot-msg', 'Đổi mật khẩu thành công! Hãy đăng nhập lại.');
                    setTimeout(() => {
                        document.querySelector('.auth-tab[data-target="login"]').click();
                    }, 2000);
                } else {
                    showMsg('forgot-msg', formatApiError(data.detail, 'Mã OTP không hợp lệ'), true);
                }
            } catch(e) {
                showMsg('forgot-msg', 'Lỗi kết nối máy chủ', true);
            } finally {
                btnText.classList.remove('hidden');
                loader.classList.add('hidden');
            }
        });
    }
}

async function handleCredentialResponse(response) {
    try {
        const res = await fetch(`${API_URL}/auth/google/callback_direct`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: response.credential })
        });
        const data = await res.json();
        if (res.ok) {
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('user', data.username);
            localStorage.setItem('role', data.role);
            localStorage.setItem('prediction_tokens', data.prediction_tokens || 0);
            window.location.href = 'dashboard.html';
        } else {
            showMsg('login-msg', 'Lỗi đăng nhập Google: ' + data.detail, true);
        }
    } catch (e) {
        showMsg('login-msg', 'Lỗi kết nối máy chủ.', true);
    }
}

// --- Dashboard Logic ---
function initDashboard() {
    document.getElementById('display-username').innerText = authUser;
    document.getElementById('display-role').innerText = authRole.toUpperCase();
    document.getElementById('display-tokens').innerText = authRole === 'admin' ? 'Unlimited' : authPredictionTokens;


    // Add Admin button if admin
    if (authRole === 'admin') {
        const sf = document.querySelector('.sidebar-footer');
        if (sf) {
            sf.insertAdjacentHTML('afterbegin', `<div class="mb-2"><a href="admin.html" class="btn btn-outline" style="width:100%; border-color:var(--danger); color:var(--danger);"><i class="fa-solid fa-user-shield"></i> <span data-i18n="btn_goto_admin">Chuyển sang Quản trị (Admin)</span></a></div>`);
        }
    }

    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            item.classList.add('active');
            const targetId = `tab-${item.getAttribute('data-tab')}`;
            document.getElementById(targetId).classList.add('active');
            
            if (targetId === 'tab-analytics') {
                loadPaymentHistory();
            }
            if (targetId === 'tab-history') {
                loadHistory();
            }
        });
    });

    fetchModels();
    initSingleScan();
    initBatchScan();
    initPaymentModal();
    initNotifications();
}

async function initPaymentModal() {
    const openBtn = document.getElementById('open-payment-modal-btn');
    const modal = document.getElementById('payment-modal');
    const closeBtn = document.getElementById('close-payment-modal');
    const grid = document.getElementById('pricing-grid-container');

    if (!openBtn || !modal) return;

    openBtn.addEventListener('click', async () => {
        modal.classList.remove('hidden');
        grid.innerHTML = '<div style="padding: 20px; width: 100%;"><i class="fa-solid fa-circle-notch fa-spin text-primary" style="font-size: 2rem;"></i></div>';
        
        try {
            const res = await fetch(`${API_URL}/site-config`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (res.ok) {
                const config = await res.json();
                let packages = [];
                try {
                    packages = JSON.parse(config.token_packages || '[]');
                } catch(e) {}
                
                let html = '';
                packages.forEach(pkg => {
                    html += `
                        <div class="pricing-card" style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; min-width: 200px; text-align: center; flex: 1; cursor: pointer; transition: 0.3s;" onmouseover="this.style.borderColor='var(--primary)'" onmouseout="this.style.borderColor='var(--border-color)'" onclick="createPayment(${pkg.id || 0}, ${pkg.price || 0}, ${pkg.tokens || 0})">
                            <h3 style="color: var(--primary); margin-bottom: 10px; font-size: 1.2rem;">${pkg.name}</h3>
                            <div style="font-size: 1.5rem; font-weight: bold; color: var(--text-primary); margin-bottom: 10px;">${Number(pkg.price || 0).toLocaleString('vi-VN')}đ</div>
                            <p style="color: var(--text-secondary); font-size: 0.9rem;"><i class="fa-solid fa-coins text-warning"></i> +${pkg.tokens} Tokens</p>
                        </div>
                    `;
                });
                grid.innerHTML = html || '<p>Không có gói nạp nào.</p>';
            }
        } catch(e) {
            grid.innerHTML = '<p class="text-danger">Lỗi tải dữ liệu gói nạp.</p>';
        }
    });

    closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });
}

window.createPayment = async function(pkgId, amount, tokens) {
    if (!confirm('Bạn có chắc chắn muốn mua gói này?')) return;
    try {
        const res = await fetch(`${API_URL}/payment/create_payment_url`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, tokens })
        });
        const data = await res.json();
        if (res.ok && data.payment_url) {
            window.location.href = data.payment_url;
        } else {
            alert('Lỗi tạo URL thanh toán: ' + (data.detail || ''));
        }
    } catch(e) {
        alert('Lỗi kết nối máy chủ');
    }
}

async function fetchModels() {
    try {
        const res = await fetch(`${API_URL}/models`);
        if (res.ok) {
            const data = await res.json();
            const models = data.available_models || [];
            updateSelect('model-select', models);
            updateSelect('batch-model-select', models);
        }
    } catch(e) { console.error('Failed to fetch models'); }
}

function updateSelect(id, models) {
    const sel = document.getElementById(id);
    if (!sel) return;
    let html = '';
    models.forEach(m => {
        html += `<option value="${m}">${MODEL_NAMES[m] || m}</option>`;
    });
    if (html) sel.innerHTML = html;
}

// --- Single Scan ---
let currentSingleFile = null;

function initSingleScan() {
    const dropZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const previewContainer = document.getElementById('preview-container');
    const previewImg = document.getElementById('img-preview');
    const fileName = document.getElementById('file-name');
    const analyzeBtn = document.getElementById('btn-analyze');

    dropZone?.addEventListener('click', () => {
        fileInput.value = '';
        fileInput?.click();
    });

    previewContainer?.addEventListener('click', () => {
        fileInput.value = '';
        fileInput?.click();
    });
    
    fileInput?.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            currentSingleFile = e.target.files[0];
            const reader = new FileReader();
            reader.onload = (ev) => {
                if(previewImg) previewImg.src = ev.target.result;
                if(previewContainer) previewContainer.classList.remove('hidden');
                if(dropZone) dropZone.classList.add('hidden');
                if(fileName) fileName.innerText = currentSingleFile.name;
                if(analyzeBtn) analyzeBtn.disabled = false;
            };
            reader.readAsDataURL(currentSingleFile);
        }
    });

    analyzeBtn?.addEventListener('click', async () => {
        if (!currentSingleFile) return;
        
        analyzeBtn.disabled = true;
        const orgHtml = analyzeBtn.innerHTML;
        analyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang phân tích...';
        
        const model = document.getElementById('model-select').value;
        const formData = new FormData();
        formData.append('file', currentSingleFile);
        formData.append('model_type', model);
        
        document.getElementById('result-placeholder')?.classList.add('hidden');
        document.getElementById('result-content')?.classList.remove('hidden');

        try {
            const res = await fetch(`${API_URL}/predict`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${authToken}` },
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                renderSingleResult(data, model);
                // Update token
                if (authRole !== 'admin') {
                    authPredictionTokens = Math.max(0, authPredictionTokens - 1);
                    const dt = document.getElementById('display-tokens');
                    if(dt) dt.innerText = authPredictionTokens;
                    localStorage.setItem('prediction_tokens', authPredictionTokens);
                }
            } else {
                alert(formatApiError(data.detail, 'Lỗi phân tích ảnh'));
                document.getElementById('result-placeholder')?.classList.remove('hidden');
                document.getElementById('result-content')?.classList.add('hidden');
            }
        } catch (e) {
            alert('Lỗi kết nối máy chủ');
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = orgHtml;
        }
    });
}

function renderSingleResult(data, model) {
    const pFake = data.probability;
    const threshold = userSettings.verdictThreshold / 100;
    const isFake = pFake >= threshold;
    
    const vBox = document.getElementById('res-verdict');
    if(vBox) {
        vBox.innerText = isFake ? 'FAKE' : 'REAL';
        vBox.style.color = isFake ? 'var(--danger)' : 'var(--success)';
    }
    
    const pBox = document.getElementById('res-prob');
    if(pBox) pBox.innerText = pFake.toFixed(4);
    
    const mBox = document.getElementById('res-model');
    if(mBox) mBox.innerText = MODEL_NAMES[model] || model;
    
    const lBox = document.getElementById('res-latency');
    if(lBox) lBox.innerText = data.latency ? (data.latency * 1000).toFixed(0) : 'N/A';
    
    const hmImg = document.getElementById('res-heatmap');
    if(hmImg && data.fft_base64) hmImg.src = `data:image/png;base64,${data.fft_base64}`;
    
    if (data.metadata_analysis) {
        const bg = document.getElementById('res-meta-bg');
        const ed = document.getElementById('res-meta-edge');
        const co = document.getElementById('res-meta-comp');
        if(bg) bg.innerText = data.metadata_analysis.noise_variance || 'N/A';
        if(ed) ed.innerText = data.metadata_analysis.edge_intensity || 'N/A';
        if(co) co.innerText = data.metadata_analysis.compression_level || 'N/A';
    } else {
        const bg = document.getElementById('res-meta-bg');
        const ed = document.getElementById('res-meta-edge');
        const co = document.getElementById('res-meta-comp');
        if(bg) bg.innerText = 'N/A';
        if(ed) ed.innerText = 'N/A';
        if(co) co.innerText = 'N/A';
    }
}

// --- Batch Scan ---
function initBatchScan() {
    const batchSelectBtn = document.getElementById('batch-upload-zone');
    const batchInput = document.getElementById('batch-file-input');
    const batchRunBtn = document.getElementById('btn-batch-analyze');
    const batchPreviewList = document.getElementById('batch-preview-list');
    let batchFiles = [];

    batchSelectBtn?.addEventListener('click', () => {
        batchInput.value = '';
        batchInput?.click();
    });

    batchPreviewList?.addEventListener('click', () => {
        batchInput.value = '';
        batchInput?.click();
    });

    batchInput?.addEventListener('change', (e) => {
        batchFiles = Array.from(e.target.files).slice(0, 20); // max 20
        if (batchPreviewList) {
            batchPreviewList.innerHTML = `<div class="badge text-primary" style="padding:10px; border:1px solid var(--border-color); border-radius:4px; cursor:pointer;">Đã chọn ${batchFiles.length} tệp. <span style="font-size:0.8rem; color:var(--text-muted);">(Nhấn để chọn lại)</span></div>`;
        }
        const tbody = document.getElementById('batch-result-tbody');
        if(tbody) tbody.innerHTML = '';
        if(batchRunBtn) batchRunBtn.disabled = batchFiles.length === 0;
    });

    batchRunBtn?.addEventListener('click', async () => {
        if (batchFiles.length === 0) return;
        batchRunBtn.disabled = true;
        const orgHtml = batchRunBtn.innerHTML;
        batchRunBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý...';
        
        const model = document.getElementById('batch-model-select').value;
        const formData = new FormData();
        batchFiles.forEach(f => formData.append('files', f));
        formData.append('model_type', model);

        try {
            const res = await fetch(`${API_URL}/predict/batch`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${authToken}` },
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                renderBatchResult(data.results, model);
                // Update token
                if (authRole !== 'admin') {
                    authPredictionTokens = Math.max(0, authPredictionTokens - batchFiles.length);
                    const dt = document.getElementById('display-tokens');
                    if(dt) dt.innerText = authPredictionTokens;
                    localStorage.setItem('prediction_tokens', authPredictionTokens);
                }
            } else {
                alert(formatApiError(data.detail, 'Lỗi phân tích Batch'));
            }
        } catch(e) {
            alert('Lỗi kết nối máy chủ');
        } finally {
            batchRunBtn.disabled = false;
            batchRunBtn.innerHTML = orgHtml;
        }
    });
}

function renderBatchResult(results, model) {
    const tbody = document.getElementById('batch-result-tbody');
    let html = '';
    const threshold = userSettings.verdictThreshold / 100;

    results.forEach(r => {
        if (r.error) {
            html += `<tr><td>${r.filename}</td><td colspan="3" class="text-danger">${r.error}</td></tr>`;
        } else {
            const isFake = r.probability >= threshold;
            const predCls = isFake ? 'text-danger' : 'text-success';
            const predTxt = isFake ? 'FAKE' : 'REAL';
            
            html += `<tr>
                <td>${r.filename}</td>
                <td>${MODEL_NAMES[model] || model}</td>
                <td>${r.probability.toFixed(4)}</td>
                <td class="${predCls} font-weight-bold">${predTxt}</td>
            </tr>`;
        }
    });
    tbody.innerHTML = html;
}

// --- History & Analytics ---
async function loadHistory() {
    try {
        const res = await fetch(`${API_URL}/history/`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const data = await res.json();
            renderHistory(data.items || []);
        }
    } catch(e) { console.error(e); }
}

function renderHistory(data) {
    const tbody = document.getElementById('history-tbody');
    let html = '';
    const threshold = userSettings.verdictThreshold / 100;
    
    data.forEach(h => {
        const date = new Date(h.created_at).toLocaleString('vi-VN');
        const pFake = h.probability !== null ? h.probability : 0;
        const isFake = pFake >= threshold;
        const cls = isFake ? 'text-danger' : 'text-success';
        
        html += `<tr>
            <td>${date}</td>
            <td>${h.filename || 'Unknown'}</td>
            <td>${MODEL_NAMES[h.model_type] || h.model_type}</td>
            <td>${pFake.toFixed(4)}</td>
            <td class="${cls} font-weight-bold">${isFake ? 'FAKE' : 'REAL'}</td>
        </tr>`;
    });
    if(!html) html = '<tr><td colspan="5" class="text-center text-muted">Chưa có lịch sử.</td></tr>';
    tbody.innerHTML = html;
}

async function loadAnalytics() {
    try {
        const res = await fetch(`${API_URL}/history/`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const data = await res.json();
            renderAnalytics(data.items || []);
        }
    } catch(e) {}

    // Also load payment history
    loadPaymentHistory();
}

function renderAnalytics(data) {
    const total = data.length;
    document.getElementById('stat-total-scans').innerText = total;
    if (total === 0) return;
    
    const threshold = userSettings.verdictThreshold / 100;
    let fakeCount = 0;
    let sumProb = 0;
    let models = {};

    data.forEach(h => {
        const p = h.probability || 0;
        if (p >= threshold) fakeCount++;
        sumProb += p;
        const m = h.model_type || 'unknown';
        models[m] = (models[m] || 0) + 1;
    });

    document.getElementById('stat-fake-rate').innerText = ((fakeCount / total) * 100).toFixed(1) + '%';
    document.getElementById('stat-real-rate').innerText = (((total - fakeCount) / total) * 100).toFixed(1) + '%';
    document.getElementById('stat-avg-fake').innerText = (sumProb / total).toFixed(4);

    let tbody = '';
    Object.keys(models).forEach(k => {
        let pct = ((models[k] / total) * 100).toFixed(1);
        tbody += `<tr><td>${MODEL_NAMES[k] || k}</td><td>${models[k]}</td><td>${pct}%</td></tr>`;
    });
    document.getElementById('analytics-model-tbody').innerHTML = tbody;
}

async function loadPaymentHistory() {
    const tbody = document.getElementById('payment-history-tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/payment-history/`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const data = await res.json();
            renderPaymentHistory(data.items || []);
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Không thể tải dữ liệu giao dịch.</td></tr>';
        }
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Lỗi kết nối máy chủ.</td></tr>';
    }
}

function renderPaymentHistory(items) {
    const tbody = document.getElementById('payment-history-tbody');
    if (!tbody) return;

    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Chưa có giao dịch nào.</td></tr>';
        return;
    }

    let html = '';
    items.forEach(item => {
        const statusClass = item.status === 'success' ? 'color: var(--success); font-weight: bold;' : 'color: var(--danger);';
        const statusText = item.status === 'success' ? '✅ Thành công' : '❌ ' + (item.status || 'Thất bại');
        const amount = Number(item.amount || 0).toLocaleString('vi-VN');
        const date = item.created_at ? new Date(item.created_at).toLocaleString('vi-VN') : 'N/A';

        html += `<tr>
            <td style="font-family: monospace; font-size: 0.85rem;">${item.order_id || 'N/A'}</td>
            <td>${amount}đ</td>
            <td style="font-weight: bold; color: var(--primary);">+${item.tokens || 0}</td>
            <td style="${statusClass}">${statusText}</td>
            <td>${item.bank_code || '-'}</td>
            <td style="font-size: 0.85rem;">${date}</td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

document.getElementById('history-refresh-btn')?.addEventListener('click', loadHistory);

// --- Settings ---
function initSettings() {
    try {
        const saved = JSON.parse(localStorage.getItem('academic_settings'));
        if (saved) userSettings = { ...userSettings, ...saved };
    } catch(e) {}

    const elThresh = document.getElementById('settings-threshold');
    const elThreshVal = document.getElementById('settings-threshold-value');
    const elAutoHist = document.getElementById('settings-auto-history');

    if (elThresh) {
        elThresh.value = userSettings.verdictThreshold / 100;
        elThreshVal.innerText = (userSettings.verdictThreshold / 100).toFixed(2);
        elAutoHist.checked = userSettings.autoLoadHistory;

        elThresh.addEventListener('input', (e) => {
            elThreshVal.innerText = parseFloat(e.target.value).toFixed(2);
        });

        document.getElementById('save-settings-btn').addEventListener('click', () => {
            userSettings.verdictThreshold = parseFloat(elThresh.value) * 100;
            userSettings.autoLoadHistory = elAutoHist.checked;
            localStorage.setItem('academic_settings', JSON.stringify(userSettings));
            showMsg('settings-msg', 'Lưu cấu hình thành công.');
            setTimeout(() => hideMsg('settings-msg'), 3000);
        });
    }
}

// --- Notifications ---
function initNotifications() {
    const bellBtn = document.getElementById('notif-bell-btn');
    const dropdown = document.getElementById('notif-dropdown');
    const markAllBtn = document.getElementById('notif-mark-all-btn');

    if (!bellBtn || !dropdown) return;

    // Toggle dropdown
    bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isHidden = dropdown.classList.contains('hidden');
        dropdown.classList.toggle('hidden');
        if (isHidden) {
            loadNotifications();
        }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target) && !bellBtn.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });

    // Mark all as read
    markAllBtn?.addEventListener('click', async () => {
        try {
            await fetch(`${API_URL}/notifications/read-all`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            loadNotifications();
            updateNotifBadge(0);
        } catch(e) {}
    });

    // Initial load of unread count
    loadUnreadCount();

    // Auto-refresh unread count every 60s
    setInterval(loadUnreadCount, 60000);
}

async function loadUnreadCount() {
    try {
        const res = await fetch(`${API_URL}/notifications/unread-count`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const data = await res.json();
            updateNotifBadge(data.count || 0);
        }
    } catch(e) {}
}

function updateNotifBadge(count) {
    const badge = document.getElementById('notif-badge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

async function loadNotifications() {
    const listEl = document.getElementById('notif-list');
    if (!listEl) return;
    listEl.innerHTML = '<div class="text-center text-muted" style="padding: 20px;"><i class="fa-solid fa-spinner fa-spin"></i></div>';

    try {
        const res = await fetch(`${API_URL}/notifications/?limit=30`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const data = await res.json();
            renderNotifications(data);
        } else {
            listEl.innerHTML = '<div class="text-center text-muted" style="padding: 20px;">Lỗi tải thông báo.</div>';
        }
    } catch(e) {
        listEl.innerHTML = '<div class="text-center text-danger" style="padding: 20px;">Lỗi kết nối.</div>';
    }
}

function renderNotifications(items) {
    const listEl = document.getElementById('notif-list');
    if (!listEl) return;

    if (!items || items.length === 0) {
        listEl.innerHTML = '<div class="text-center text-muted" style="padding: 30px;"><i class="fa-solid fa-bell-slash" style="font-size: 2rem; opacity: 0.4; margin-bottom: 8px;"></i><p>Không có thông báo nào.</p></div>';
        return;
    }

    const typeIcons = {
        'info': 'fa-circle-info',
        'warning': 'fa-triangle-exclamation',
        'success': 'fa-circle-check',
        'payment': 'fa-coins',
        'system': 'fa-gear'
    };
    const typeColors = {
        'info': 'var(--primary)',
        'warning': '#f59e0b',
        'success': 'var(--success)',
        'payment': '#f59e0b',
        'system': 'var(--text-muted)'
    };

    let html = '';
    items.forEach(n => {
        const icon = typeIcons[n.type] || 'fa-bell';
        const color = typeColors[n.type] || 'var(--primary)';
        const isUnread = !n.is_read;
        const bgStyle = isUnread ? 'background: rgba(37, 99, 235, 0.05);' : '';
        const boldStyle = isUnread ? 'font-weight: 600;' : '';
        const timeAgo = formatTimeAgo(n.created_at);

        html += `<div class="notif-item" style="padding: 12px 16px; border-bottom: 1px solid var(--border-color); cursor: pointer; transition: background 0.2s; ${bgStyle}" 
            onmouseover="this.style.background='rgba(0,0,0,0.03)'" 
            onmouseout="this.style.background='${isUnread ? 'rgba(37, 99, 235, 0.05)' : ''}'"
            onclick="markNotifRead(${n.id}, this)">
            <div style="display: flex; gap: 10px; align-items: flex-start;">
                <i class="fa-solid ${icon}" style="color: ${color}; margin-top: 3px; font-size: 1rem;"></i>
                <div style="flex: 1; min-width: 0;">
                    <div style="${boldStyle} font-size: 0.9rem; color: var(--text-primary); margin-bottom: 2px;">${n.title || 'Thông báo'}</div>
                    <div style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.4;">${n.message || ''}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">${timeAgo}</div>
                </div>
                ${isUnread ? '<div style="width: 8px; height: 8px; background: var(--primary); border-radius: 50%; margin-top: 6px; flex-shrink: 0;"></div>' : ''}
            </div>
        </div>`;
    });
    listEl.innerHTML = html;
}

window.markNotifRead = async function(notifId, el) {
    try {
        await fetch(`${API_URL}/notifications/${notifId}/read`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (el) {
            el.style.background = '';
            const dot = el.querySelector('div[style*="border-radius: 50%"]');
            if (dot) dot.remove();
        }
        loadUnreadCount();
    } catch(e) {}
}

function formatTimeAgo(dateStr) {
    if (!dateStr) return '';
    const now = new Date();
    const date = new Date(dateStr);
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'Vừa xong';
    if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`;
    return date.toLocaleDateString('vi-VN');
}

// --- Admin Logic ---
// Note: All admin data loading and actions are handled by admin-extended.js
// This function only sets up the basic navigation and UI.
function initAdmin() {
    document.getElementById('display-admin-username').innerText = authUser;
    
    // Navigation (tab switching only - data loading is handled by admin-extended.js)
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            item.classList.add('active');
            const targetId = `tab-${item.getAttribute('data-tab')}`;
            document.getElementById(targetId).classList.add('active');
        });
    });
}
