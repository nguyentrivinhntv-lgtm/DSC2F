const translations = {
    vi: {
        // --- General ---
        "site_title": "CNNDetection Research - Phân Tích Hình Ảnh",
        "btn_login": "Đăng nhập",
        "btn_access_portal": "Truy cập Cổng Phân Tích",
        
        // --- Landing Page ---
        "marquee_text": "* CẬP NHẬT: Mô hình Dual-Stream Enhanced đã đạt độ chính xác 98.5% trên tập test * | * Hỗ trợ API cho các nhóm nghiên cứu * | * Liên hệ Admin để cấp phát Token *",
        "hero_title": "Hệ Thống Nhận Diện Ảnh Giả Mạo Dựa Trên Kiến Trúc Dual-Stream CNN",
        "hero_desc": "<strong>Tóm tắt (Abstract):</strong> Công cụ đánh giá pháp y kỹ thuật số ứng dụng mô hình Học sâu (Deep Learning) kết hợp thông tin Không gian (RGB) và Phổ tần số (FFT) để nhận diện hình ảnh được tạo ra hoặc chỉnh sửa bởi AI (Deepfake).",
        "btn_run_inference": "Bắt đầu Phân tích (Run Inference)",
        
        "stats_title": "Thống Kê Khảo Sát Kỹ Thuật (System Metrics)",
        "stat_acc_lbl": "Độ chính xác (Accuracy)",
        "stat_lat_lbl": "Độ trễ TB (Latency)",
        "stat_sample_lbl": "Mẫu đã kiểm thử",
        
        "features_title": "Đặc tả Kỹ thuật (Methodology & Features)",
        "features_subtitle": "Hệ thống được thiết kế tối ưu cho quá trình nghiên cứu và xác minh hình ảnh trực tuyến.",
        "f1_title": "Mạng nơ-ron Đa Luồng (Dual-Stream)",
        "f1_desc": "Khai thác đồng thời đặc trưng không gian (Spatial Features) qua ResNet và đặc trưng tần số (Frequency Features) để phát hiện nhiễu giả tạo từ GAN/Diffusion models.",
        "f2_title": "Đánh giá Lô (Batch Evaluation)",
        "f2_desc": "Hỗ trợ phân tích hàng loạt tập dữ liệu lớn với độ trễ thấp. Kết xuất kết quả trực tiếp ra bảng biểu phục vụ tính toán độ đo (Accuracy, F1-Score).",
        "f3_title": "Phân tích Siêu dữ liệu (Metadata)",
        "f3_desc": "Kết hợp phân tích nhiễu nền (Background Noise), viền cạnh (Edge Artifacts), và các dấu vết nén JPEG để tăng cường độ tin cậy.",
        
        "workflow_title": "Quy trình Vận hành (Workflow)",
        "s1_title": "Chuẩn bị Dữ liệu (Data Input)",
        "s1_desc": "Người dùng tải lên một hoặc nhiều hình ảnh (Batch) cần kiểm định tính xác thực thông qua giao diện Web.",
        "s2_title": "Trích xuất Đặc trưng (Feature Extraction)",
        "s2_desc": "Hệ thống thực hiện biến đổi Fourier (FFT) và đưa dữ liệu qua mạng CNN đa luồng để tính toán phân bố nhiễu.",
        "s3_title": "Kết xuất Đánh giá (Evaluation Output)",
        "s3_desc": "Hệ thống trả về xác suất Fake, độ tin cậy, hình ảnh phổ tần số và siêu dữ liệu cho người nghiên cứu phân tích.",
        
        "pricing_title": "Tài nguyên Tính toán (Compute Resources)",
        "pricing_subtitle": "Các gói tài trợ chi phí tính toán đám mây cho nghiên cứu viên.",
        "btn_topup": "Tiến hành Nạp",
        
        "cta_title": "Sẵn sàng bắt đầu quá trình nghiên cứu?",
        "cta_desc": "Khởi tạo tài khoản miễn phí để nhận ngay 10 tokens trải nghiệm khả năng nhận diện Deepfake.",
        "btn_register_research": "Đăng ký Tài khoản Nghiên cứu",
        
        "footer_copyright": "&copy; 2026 CNNDetection Research Project. All rights reserved.",
        "footer_contact": "Contact: support@cnndetection.com | Phone: +1 800 123 4567",
        
        // --- Auth Page ---
        "auth_title": "CNNDetection Research Portal",
        "auth_subtitle": "Hệ Thống Đánh Giá Hình Ảnh",
        "auth_desc": "Truy cập hệ thống phân tích hình ảnh và đánh giá Deepfake chuyên sâu.",
        "tab_login": "Đăng Nhập",
        "tab_register": "Đăng Ký",
        "lbl_username": "Định danh (Username)",
        "lbl_password": "Khóa bảo mật (Password)",
        "lbl_email": "Hòm thư (Email - Tùy chọn)",
        "ph_username": "Nhập username",
        "ph_password": "Nhập password",
        "ph_email": "Nhập email (để reset mật khẩu)",
        "btn_login_submit": "Xác Thực",
        "btn_register_submit": "Khởi Tạo Tài Khoản",
        "link_forgot": "Quên khóa bảo mật?",
        "or_login_with": "hoặc đăng nhập với",
        "link_back_home": "Quay về Cổng Thông Tin",
        
        // --- Dashboard / Common ---
        "nav_workspace": "Workspace Analysis",
        "nav_single": "Quét Đơn Lẻ (Single)",
        "nav_batch": "Quét Lô (Batch)",
        "nav_analytics": "Báo cáo Toàn cục",
        "nav_purchase_history": "Lịch sử Mua hàng",
        "nav_history": "Dữ liệu Lịch sử",
        "nav_payment": "Quản lý Tài nguyên",
        "nav_settings": "Cấu hình Thông số",
        "btn_logout": "Thoát phiên (Logout)",
        "btn_goto_admin": "Chuyển sang Quản trị (Admin)",
        "user_role_admin": "Quản trị viên",
        "user_role_user": "Nghiên cứu viên",
        
        "upload_drag": "Kéo thả hình ảnh vào vùng này",
        "upload_or": "hoặc nhấn để duyệt tệp",
        "upload_formats": "Hỗ trợ: JPEG, PNG, WEBP (Max 5MB)",
        "upload_batch_hint": "Hỗ trợ phân tích tối đa 20 ảnh/lô",
        
        "btn_analyze": "Tiến hành Phân Tích",
        "btn_batch_analyze": "Phân Tích Lô",
        "lbl_model_select": "Kiến trúc Mô hình:",
        
        // Results
        "res_title": "Kết xuất Phân tích (Analysis Output)",
        "res_placeholder": "Hệ thống đang chờ dữ liệu đầu vào...",
        "res_lbl_prob": "Xác suất Fake:",
        "res_lbl_verdict": "Kết luận:",
        "res_lbl_model": "Kiến trúc:",
        "res_lbl_latency": "Độ trễ:",
        "res_title_heatmap": "Bản đồ Nhiệt (Grad-CAM)",
        "res_title_fft": "Phổ Tần số Không gian (FFT)",
        "res_title_meta": "Siêu dữ liệu & Nhiễu (Metadata)",
        "lbl_noise_bg": "Nhiễu nền (Background):",
        "lbl_noise_edge": "Viền cạnh (Edges):",
        "lbl_noise_comp": "Nén JPEG (Compression):",
        
        // Data labels
        "fake": "FAKE",
        "real": "REAL",
        "analyzing": "Đang xử lý...",
        "error_upload": "Lỗi xử lý hình ảnh",
        "no_data": "Không có dữ liệu",
        
        // Analytics
        "stat_total_scans": "Tổng mẫu khảo sát",
        "stat_fake_rate": "Tỉ lệ Fake",
        "stat_real_rate": "Tỉ lệ Real",
        "stat_avg_prob": "P_fake Trung bình",
        "table_model": "Kiến trúc (Model)",
        "table_count": "Số lượng",
        "table_pct": "Tỉ trọng",
        "table_3_title": "Table 3. Phân bố Mô hình (Model Distribution)",
        "btn_add_token": "Nạp Token",
        "config_threshold_lbl": "Ngưỡng Quyết định (Decision Threshold, &tau;) =",
        "config_threshold_desc": "Nếu P_fake &ge; &tau;, hệ thống kết luận FAKE.",
        "config_auto_load": "Tự động tải dữ liệu Analytics khi chuyển tab",
        "btn_save_params": "Lưu Tham số (Save Parameters)",
        "table_payment_title": "Table 4. Lịch sử Giao dịch Mua Token (Token Purchase History)",
        "th_order_id": "Mã đơn hàng",
        "th_amount": "Số tiền (VNĐ)",
        "th_tokens": "Tokens",
        "th_status": "Trạng thái",
        "th_bank": "Ngân hàng",
        "th_date": "Ngày giao dịch",
        "notif_title": "Thông báo",
        "notif_mark_all": "Đánh dấu tất cả đã đọc",
        "notif_empty": "Không có thông báo nào.",
        
        // Admin
        "admin_nav_dashboard": "Thống kê Toàn cục",
        "admin_nav_users": "Quản lý User",
        "admin_nav_deletion": "Yêu cầu Xoá TK",
        "admin_nav_models": "Quản lý Model",
        "admin_nav_tokens": "Cấp phát Token",
        "admin_nav_history": "Lịch sử Toàn hệ thống",
        "admin_nav_payments": "Lịch sử Mua hàng",
        "admin_nav_ui": "Tuỳ chỉnh Giao diện",
        "admin_nav_cms": "Quản lý Trang (CMS)",
        "admin_nav_notifs": "Thông báo Hệ thống",
        "admin_nav_ai": "Cấu hình AI Dịch thuật",
        "admin_nav_api": "Cấu hình Môi trường (API)",
        "admin_back_workspace": "Trở về Workspace"
    },
    en: {
        // --- General ---
        "site_title": "CNNDetection Research - Image Analysis",
        "btn_login": "Login",
        "btn_access_portal": "Access Analysis Portal",
        
        // --- Landing Page ---
        "marquee_text": "* UPDATE: Dual-Stream Enhanced model reached 98.5% accuracy on test set * | * API support for research groups * | * Contact Admin for Token allocation *",
        "hero_title": "Deepfake Image Detection System Based on Dual-Stream CNN Architecture",
        "hero_desc": "<strong>Abstract:</strong> A digital forensics evaluation tool utilizing Deep Learning models combining Spatial (RGB) and Frequency (FFT) information to detect AI-generated or manipulated images (Deepfakes).",
        "btn_run_inference": "Run Inference",
        
        "stats_title": "Technical Evaluation Metrics",
        "stat_acc_lbl": "Accuracy",
        "stat_lat_lbl": "Avg Latency",
        "stat_sample_lbl": "Samples Tested",
        
        "features_title": "Methodology & Features",
        "features_subtitle": "System optimized for online image research and verification.",
        "f1_title": "Dual-Stream Neural Network",
        "f1_desc": "Simultaneously exploits spatial features via ResNet and frequency features to detect artificial noise from GAN/Diffusion models.",
        "f2_title": "Batch Evaluation",
        "f2_desc": "Supports batch analysis of large datasets with low latency. Outputs results directly to tables for metric calculation (Accuracy, F1-Score).",
        "f3_title": "Metadata Analysis",
        "f3_desc": "Combines analysis of background noise, edge artifacts, and JPEG compression traces to enhance reliability.",
        
        "workflow_title": "Workflow",
        "s1_title": "Data Input",
        "s1_desc": "Users upload one or multiple images (Batch) requiring authenticity verification via the Web interface.",
        "s2_title": "Feature Extraction",
        "s2_desc": "The system performs Fourier transform (FFT) and passes data through the dual-stream CNN to calculate noise distribution.",
        "s3_title": "Evaluation Output",
        "s3_desc": "The system returns Fake probability, confidence, frequency spectrum image, and metadata for researchers to analyze.",
        
        "pricing_title": "Compute Resources",
        "pricing_subtitle": "Cloud computing funding packages for researchers.",
        "btn_topup": "Proceed to Top-up",
        
        "cta_title": "Ready to start your research process?",
        "cta_desc": "Create a free account to instantly receive 10 tokens to experience Deepfake detection capabilities.",
        "btn_register_research": "Register Research Account",
        
        "footer_copyright": "&copy; 2026 CNNDetection Research Project. All rights reserved.",
        "footer_contact": "Contact: support@cnndetection.com | Phone: +1 800 123 4567",
        
        // --- Auth Page ---
        "auth_title": "CNNDetection Research Portal",
        "auth_subtitle": "Image Evaluation System",
        "auth_desc": "Access the image analysis system for in-depth Deepfake evaluation.",
        "tab_login": "Login",
        "tab_register": "Register",
        "lbl_username": "Identifier (Username)",
        "lbl_password": "Security Key (Password)",
        "lbl_email": "Mailbox (Email - Optional)",
        "ph_username": "Enter username",
        "ph_password": "Enter password",
        "ph_email": "Enter email (to reset password)",
        "btn_login_submit": "Authenticate",
        "btn_register_submit": "Initialize Account",
        "link_forgot": "Forgot security key?",
        "or_login_with": "or authenticate with",
        "link_back_home": "Return to Information Portal",
        
        // --- Dashboard / Common ---
        "nav_workspace": "Workspace Analysis",
        "nav_single": "Single Scan",
        "nav_batch": "Batch Scan",
        "nav_analytics": "Global Analytics",
        "nav_purchase_history": "Purchase History",
        "nav_history": "Historical Data",
        "nav_payment": "Resource Management",
        "nav_settings": "Parameter Configuration",
        "btn_logout": "Terminate Session (Logout)",
        "btn_goto_admin": "Switch to Administration (Admin)",
        "user_role_admin": "Administrator",
        "user_role_user": "Researcher",
        
        "upload_drag": "Drag and drop images into this zone",
        "upload_or": "or click to browse files",
        "upload_formats": "Supported: JPEG, PNG, WEBP (Max 5MB)",
        "upload_batch_hint": "Supports analyzing up to 20 images/batch",
        
        "btn_analyze": "Execute Analysis",
        "btn_batch_analyze": "Execute Batch Analysis",
        "lbl_model_select": "Model Architecture:",
        
        // Results
        "res_title": "Analysis Output",
        "res_placeholder": "System awaiting input data...",
        "res_lbl_prob": "Fake Probability:",
        "res_lbl_verdict": "Verdict:",
        "res_lbl_model": "Architecture:",
        "res_lbl_latency": "Latency:",
        "res_title_heatmap": "Heatmap (Grad-CAM)",
        "res_title_fft": "Spatial Frequency Spectrum (FFT)",
        "res_title_meta": "Metadata & Noise",
        "lbl_noise_bg": "Background Noise:",
        "lbl_noise_edge": "Edge Artifacts:",
        "lbl_noise_comp": "JPEG Compression:",
        
        // Data labels
        "fake": "FAKE",
        "real": "REAL",
        "analyzing": "Processing...",
        "error_upload": "Image processing error",
        "no_data": "No data available",
        
        // Analytics
        "stat_total_scans": "Total Samples Surveyed",
        "stat_fake_rate": "Fake Rate",
        "stat_real_rate": "Real Rate",
        "stat_avg_prob": "Average P_fake",
        "table_model": "Architecture (Model)",
        "table_count": "Quantity",
        "table_pct": "Proportion",
        "table_3_title": "Table 3. Model Distribution",
        "btn_add_token": "Add Token",
        "config_threshold_lbl": "Decision Threshold (&tau;) =",
        "config_threshold_desc": "If P_fake &ge; &tau;, the system concludes FAKE.",
        "config_auto_load": "Automatically load Analytics data when switching tabs",
        "btn_save_params": "Save Parameters",
        "table_payment_title": "Table 4. Token Purchase History",
        "th_order_id": "Order ID",
        "th_amount": "Amount (VNĐ)",
        "th_tokens": "Tokens",
        "th_status": "Status",
        "th_bank": "Bank",
        "th_date": "Transaction Date",
        "notif_title": "Notifications",
        "notif_mark_all": "Mark all as read",
        "notif_empty": "No notifications.",
        
        // Admin
        "admin_nav_dashboard": "Global Statistics",
        "admin_nav_users": "User Management",
        "admin_nav_deletion": "Deletion Requests",
        "admin_nav_models": "Model Configuration",
        "admin_nav_tokens": "Token Allocation",
        "admin_nav_history": "System-wide History",
        "admin_nav_payments": "Purchase History",
        "admin_nav_ui": "UI Customization",
        "admin_nav_cms": "Page Management (CMS)",
        "admin_nav_notifs": "System Notifications",
        "admin_nav_ai": "AI Translation Config",
        "admin_nav_api": "Environment Config (API)",
        "admin_back_workspace": "Return to Workspace"
    }
};

function getLang() {
    return localStorage.getItem('academic_lang') || 'vi';
}

function setLang(lang) {
    if (['vi', 'en'].includes(lang)) {
        localStorage.setItem('academic_lang', lang);
        applyTranslations();
        updateLangButton(lang);
    }
}

function t(key) {
    const lang = getLang();
    return translations[lang][key] || key;
}

function applyTranslations() {
    const lang = getLang();
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[lang][key]) {
            if (el.tagName === 'INPUT' && el.type === 'button') {
                el.value = translations[lang][key];
            } else {
                el.innerHTML = translations[lang][key];
            }
        }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (translations[lang][key]) {
            el.placeholder = translations[lang][key];
        }
    });
}

function updateLangButton(lang) {
    const btn = document.getElementById('lang-toggle');
    if (btn) {
        btn.innerHTML = lang === 'vi' ? '<i class="fa-solid fa-language"></i> EN' : '<i class="fa-solid fa-language"></i> VI';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Inject Language Toggle Button
    const topbars = document.querySelectorAll('.landing-header nav, .topbar');
    topbars.forEach(nav => {
        const btn = document.createElement('button');
        btn.id = 'lang-toggle';
        btn.className = 'btn btn-outline';
        btn.style.marginRight = '10px';
        btn.style.padding = '0.3rem 0.8rem';
        btn.onclick = () => {
            const currentLang = getLang();
            setLang(currentLang === 'vi' ? 'en' : 'vi');
            // Notify dynamic scripts
            window.dispatchEvent(new Event('languageChanged'));
        };
        // Insert before the first button
        nav.insertBefore(btn, nav.firstChild);
    });
    
    updateLangButton(getLang());
    applyTranslations();
});
