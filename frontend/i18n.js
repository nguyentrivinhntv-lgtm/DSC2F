const translations = {
    vi: {
        // --- General ---
        "logout": "Đăng xuất",
        "save_changes": "Lưu thay đổi",
        "refresh": "Làm mới",
        "export_csv": "Xuất CSV",
        
        // --- Navigation ---
        "nav_dashboard": "User Dashboard",
        "nav_admin": "Admin Dashboard",

        // --- App (Dashboard) ---
        "app_title": "Detection Suite",
        "tab_single_scan": "Quét Đơn Lẻ",
        "tab_batch_scan": "Quét Hàng Loạt",
        "tab_analytics": "Phân Tích & Báo Cáo",
        "tab_history": "Lịch Sử",
                "tab_settings": "Cài Đặt",
        "stat_total_scans": "Tổng lượt quét",
        "stat_fake_rate": "Tỷ lệ Fake",
        "stat_real_rate": "Tỷ lệ Real",
        "stat_top_model": "Model phổ biến",
        "stat_avg_fake": "Độ fake trung bình",
        "col_count": "Số lượt",
        "col_ratio": "Tỷ trọng",
        "history_title": "Lịch sử nhận diện",
        "settings_desc": "Tinh chỉnh ngưỡng hiển thị và trải nghiệm dashboard.",
        "settings_threshold": "Ngưỡng kết luận Fake:",
        "settings_auto_history": "Tự động tải lịch sử khi mở tab Analytics",

        
        // --- Auth ---
        "auth_sys_title": "Hệ thống nhận diện ảnh giả mạo",
        "auth_login_tab": "Đăng nhập",
        "auth_register_tab": "Đăng ký",
        "auth_or": "hoặc",
        "ph_username": "Tên đăng nhập",
        "ph_password": "Mật khẩu",
        "ph_new_username": "Tên đăng nhập mới",
        "ph_new_password": "Mật khẩu (tối thiểu 6 ký tự)",
        
        // --- Landing Page Static ---
        "lp_nav_user": "User Dashboard",
        "lp_nav_admin": "Admin Dashboard",
        "lp_nav_download": "Tải App Android",
        "lp_stat_1": "100K+",
        "lp_stat_1_desc": "Ảnh Đã Quét",
        "lp_stat_2": "99.8%",
        "lp_stat_2_desc": "Độ Chính Xác",
        "lp_stat_3": "< 2s",
        "lp_stat_3_desc": "Thời Gian Phân Tích",
        "lp_tag_tech": "Công Nghệ",
        "lp_title_tech": "Công Nghệ Cốt Lõi",
        "lp_desc_tech": "Kết hợp các mô hình Deep Learning tiên tiến nhất để phân tích ảnh giả mạo ở cấp độ pixel.",
        "lp_tag_process": "Quy Trình",
        "lp_title_process": "Cách Thức Hoạt Động",
        "lp_desc_process": "Chỉ 3 bước đơn giản để nhận kết quả phân tích chuyên nghiệp.",
        "lp_cta_title": "Sẵn Sàng Bảo Vệ <span class='gradient-text'>Sự Thật?</span>",
        "lp_cta_desc": "Tạo tài khoản miễn phí và bắt đầu phân tích ảnh ngay hôm nay.",
        "lp_cta_btn": "Bắt Đầu Ngay <i class='fa-solid fa-arrow-right'></i>",
        
        // --- Upload ---
        "upload_drag": "Kéo thả ảnh vào đây",
        "upload_or": "hoặc <span class='text-gradient'>nhấn để chọn file</span>",
        "upload_hint": "Hỗ trợ JPG, PNG, WEBP",
        "btn_analyze": "Phân Tích Ảnh",
        "upload_batch_hint": "Kéo thả nhiều ảnh (Tối đa 20)",
        "btn_analyze_batch": "Phân Tích Hàng Loạt",

        // --- Results ---
        "res_title": "Kết Quả Nhận Diện",
        "res_placeholder": "Upload ảnh để xem phân tích",
        "lbl_confidence": "Độ tin cậy",
        "lbl_prob": "Xác suất ảnh giả",
        "lbl_model": "Mô hình",
        
        // --- Insights ---
        "lbl_heatmap": "Heatmap / Grad-CAM",
        "lbl_metadata": "Metadata / Noise Analysis",
        "lbl_fft": "Ảnh Phổ Cấu Trúc Không Gian (FFT)",
        "lbl_noise_bg": "Nhiễu nền:",
        "lbl_noise_edge": "Viền khuôn mặt:",
        "lbl_noise_comp": "Dấu vết nén ảnh:",
        "val_analyzing": "Đang phân tích",
        "heatmap_placeholder": "Vùng nghi ngờ sẽ hiển thị tại đây",

        // --- Dynamic JS Strings (VI) ---
        "fake_img": "ẢNH GIẢ MẠO (AI)",
        "real_img": "ẢNH THẬT (REAL)",
        "noise_fake_bg": "Bất thường (Phổ nhiễu cao)",
        "noise_fake_edge": "Có dấu vết cắt ghép (Blending)",
        "noise_fake_comp": "Lỗi ma trận DCT",
        "noise_real_bg": "Tự nhiên (Phân bố đều)",
        "noise_real_edge": "Mượt mà, không vết xước",
        "noise_real_comp": "Nhất quán (Gốc)",

        // --- Admin ---
        "admin_title": "Admin Control Center",
        "admin_subtitle": "Quản lý dữ liệu nhận diện hệ thống",
        "tab_stats": "Thống kê",
        "tab_models": "Quản lý Model",
        "tab_tokens": "Nạp Token",
        "tab_ui": "Tùy chỉnh giao diện",
        "admin_login_as": "Đăng nhập quản trị:",
        
        // --- Admin Stats ---
        "stat_total": "Tổng lượt phân tích",
        "stat_users": "Tổng người dùng",
        "stat_fake_rate": "Tỷ lệ Fake",
        "stat_top_model": "Mô hình phổ biến",
        "chart_fake_real": "Tỷ lệ Fake / Real",
        "chart_model_usage": "Sử dụng Model",
        "chart_timeline": "Lượt dùng theo thời gian",

        // --- Admin Models ---
        "col_model_name": "Tên Model",
        "col_desc": "Mô tả",
        "col_status": "Trạng thái",
        "col_action": "Thao tác",
        "col_model_id": "Mã Model",
        "admin_models_desc": "Bật hoặc tắt các model trên hệ thống. Model bị tắt sẽ không thể sử dụng.",
        "loading_models": "Đang tải danh sách model...",

        // --- Admin Token ---
        "token_user": "Username",
        "token_amount": "Số token nạp",
        "btn_add_token": "Nạp token",
        "ph_token_username": "Nhập username cần nạp token",

        // --- Admin History ---
        "hist_search_user": "Tìm theo user / tên ảnh",
        "ph_search_user": "Nhập user hoặc tên file...",
        "hist_filter_model": "Lọc model",
        "hist_filter_label": "Lọc kết luận",
        "col_time": "Thời gian",
        "col_user": "User",
        "col_filename": "Tên ảnh",
        "col_model": "Model",
        "col_prob": "Xác suất fake",
        "col_verdict": "Kết luận",
        "loading_data": "Đang tải dữ liệu...",

        // --- Admin UI ---
        "ui_desc": "Thay đổi màu sắc, nội dung, ảnh và bật/tắt các phần trên trang giới thiệu.",
        "btn_preview": "Xem trước",
        "btn_save_changes": "Lưu thay đổi",
        "ui_colors": "Màu sắc",
        "ui_bg1": "Màu nền 1",
        "ui_bg2": "Màu nền 2",
        "ui_bg3": "Màu nền 3",
        "ui_primary": "Màu chủ đạo",
        "ui_accent": "Màu phụ (Accent)",
        "ui_text": "Màu chữ",
        
        "ui_general": "Thông tin chung",
        "ui_site_name": "Tên trang web",
        "ui_slogan": "Slogan / Mô tả ngắn",
        "ui_footer": "Nội dung chân trang",

        "ui_hero": "Hero Banner",
        "ui_hero_l1": "Tiêu đề dòng 1",
        "ui_hero_l2": "Tiêu đề dòng 2",
        "ui_hero_desc": "Mô tả chi tiết",
        "ui_hero_cta": "Nút Call to Action",

        "ui_features": "3 Tính năng (Features)",
        "ui_f1": "Tính năng 1",
        "ui_f2": "Tính năng 2",
        "ui_f3": "Tính năng 3",
        "ui_f_title": "Tiêu đề",
        "ui_f_desc": "Mô tả",

        "ui_steps": "3 Bước (How it Works)",
        "ui_s1": "Bước 1",
        "ui_s2": "Bước 2",
        "ui_s3": "Bước 3",

        "ui_toggles": "Bật / Tắt các phần",
        "ui_show_stats": "Thống kê (Stats)",
        "ui_show_marquee": "Dải chạy (Marquee)",
        "ui_show_features": "Tính năng",
        "ui_show_steps": "Cách hoạt động",
        "ui_show_cta": "Call to action cuối trang",
        "ui_logo": "Logo trang web",
        "ui_logo_upload": "Tải Logo Lên",
        "btn_reset": "Khôi phục mặc định",
        // --- Extra Missing ---
        "ph_search": "Tìm chức năng, mô hình, lịch sử...",
        "desc_single_scan": "Phân tích nhanh 1 ảnh với visual forensic nâng cao.",
        "lbl_select_model": "Chọn Mô Hình (AI Model)",
        "app_footer": "&copy; 2026 CNN Detection AI - Chuyên Cung Cấp Giải Pháp Phát Hiện Ảnh Deepfake",
        "lp_goto_dashboard": "Đi tới Dashboard",
        "lp_footer": "&copy; 2026 CNN Detection Hub &mdash; AI Deepfake Detection Platform",
        
        // --- Pricing & Upload ---
        "pricing_title": "Nạp thêm Token",
        "pricing_subtitle": "Lựa chọn gói Token phù hợp để tiếp tục sử dụng hệ thống AI phân tích Deepfake.",
        "btn_buy_now": "Mua Ngay",
        "badge_popular": "🔥 PHỔ BIẾN NHẤT",
        "feat_basic_1": "Phân tích ảnh cơ bản",
        "feat_basic_2": "Hỗ trợ lưu lịch sử",
        "feat_adv_1": "Phân tích ảnh nâng cao",
        "feat_adv_2": "Hỗ trợ Batch Scan",
        "feat_adv_3": "Tiết kiệm 10%",
        "feat_exp_1": "Mọi tính năng cao cấp",
        "feat_exp_2": "Ưu tiên phân tích (Fast)",
        "feat_exp_3": "Tiết kiệm 20%",
        "txt_tokens": "Tokens",
        "admin_pricing_title": "Bảng Giá Nạp Token",
        "admin_pricing_basic": "Gói Cơ Bản",
        "admin_pricing_adv": "Gói Nâng Cao",
        "admin_pricing_exp": "Gói Chuyên Gia",
        "ph_pkg_name": "Tên Gói",
        "ph_pkg_price": "Giá (VND)",
        "ph_pkg_tokens": "Số Token",
        "filter_all_models": "Tất cả model",
        "filter_all": "Tất cả",

        // --- Admin Missing ---
        "tab_payments": "Lịch sử Mua Hàng",
        "tab_pages": "Quản lý Trang",
        "tab_notifications": "Thông báo",
        "tab_ai_config": "Cấu hình AI",
        "tab_pages_title": "Quản lý Trang Web",
        "tab_ai_title": "Cấu hình AI Dịch Thuật",
        "tab_notif_title": "Quản lý Thông báo",
        "title_invoice_detail": "Chi Tiết Hoá Đơn",
        "title_edit_page": "Soạn Thảo Trang",
        "title_send_notif": "Gửi Thông Báo Mới",

        // --- Index Missing ---
        "nav_documents": "Tài liệu",
        "about_tag": "Khoá Luận Tốt Nghiệp DSC2F",
        "about_title": "Về Dự Án CNN Detection",
        "about_mission_title": "Sứ mệnh",
        "about_mission_desc": "Trong thời đại AI phát triển, ranh giới giữa thật và giả đang mờ dần. CNN Detection ra đời nhằm cung cấp một công cụ mạnh mẽ để dễ dàng phát hiện hình ảnh bị chỉnh sửa hoặc tạo bởi AI (Deepfake).",
        "about_tech_title": "Công nghệ Tiên tiến",
        "about_tech_desc": "Sử dụng mạng nơ-ron tích chập đa luồng (Dual Stream CNN). Bằng cách phân tích cả dữ liệu không gian (RGB) và tần số (Noise), mô hình phát hiện những dấu vết giả mạo tinh vi nhất mà mắt người không thể nhìn thấy.",
        "about_team_title": "Đội ngũ phát triển",
        "about_team_desc": "Dự án được thực hiện bởi nhóm Nghiên cứu Khoá Luận Tốt Nghiệp DSC2F với sự tâm huyết cao độ. Cam kết liên tục cập nhật các mô hình AI mới nhất (ResNet, EfficientNet) để đối phó kỹ thuật giả mạo ngày càng tinh vi.",
        "legal_tag": "Pháp lý & Tin cậy",
        "legal_privacy_title": "Chính sách Quyền riêng tư",
        "legal_privacy_desc": "Cách chúng tôi thu thập, sử dụng và bảo vệ dữ liệu cá nhân của bạn.",
        "legal_badge_req": "Bắt buộc",
        "legal_view_more": "Xem chi tiết",
        "legal_terms_title": "Điều khoản Sử dụng",
        "legal_terms_desc": "Quy định và điều kiện khi sử dụng ứng dụng CNN Detection.",
        "legal_data_title": "Xóa Dữ liệu",
        "legal_data_desc": "Yêu cầu xóa tài khoản và toàn bộ dữ liệu cá nhân khỏi hệ thống.",
        "legal_badge_warn": "Thường bắt buộc",
        "legal_ai_title": "Chính sách AI",
        "legal_ai_desc": "Cách AI hoạt động, mô hình Deep Learning và giới hạn kết quả phân tích.",
        "legal_badge_apple": "Apple đánh giá cao",
        "legal_support_title": "Hỗ trợ & Liên hệ",
        "legal_support_desc": "FAQ, hướng dẫn sử dụng, báo lỗi và thông tin liên hệ đội ngũ hỗ trợ.",
        "legal_badge_rec": "Nên có",
        "footer_desc": "Ứng dụng nhận diện ảnh AI tiên tiến, sử dụng Deep Learning để phát hiện Deepfake. Hỗ trợ đa nền tảng Web, Android & iOS.",
        "footer_col1": "Pháp lý",
        "footer_col2": "Sản phẩm",
        "footer_col3": "Hỗ trợ",
    },
    en: {
        // --- General ---
        "logout": "Logout",
        "save_changes": "Save Changes",
        "refresh": "Refresh",
        "export_csv": "Export CSV",
        
        // --- Navigation ---
        "nav_dashboard": "User Dashboard",
        "nav_admin": "Admin Dashboard",

        // --- App (Dashboard) ---
        "app_title": "Detection Suite",
        "tab_single_scan": "Quét Đơn Lẻ",
        "tab_batch_scan": "Quét Hàng Loạt",
        "tab_analytics": "Analytics",
        "tab_history": "History",
                "tab_settings": "Settings",
        "stat_total_scans": "Total Scans",
        "stat_fake_rate": "Fake Rate",
        "stat_real_rate": "Real Rate",
        "stat_top_model": "Top Model",
        "stat_avg_fake": "Avg Fake Score",
        "col_count": "Count",
        "col_ratio": "Ratio",
        "history_title": "Detection History",
        "settings_desc": "Adjust display thresholds and dashboard experience.",
        "settings_threshold": "Fake threshold:",
        "settings_auto_history": "Auto load history when opening Analytics tab",

        
        // --- Auth ---
        "auth_sys_title": "Deepfake Detection System",
        "auth_login_tab": "Login",
        "auth_register_tab": "Register",
        "auth_or": "or",
        "ph_username": "Username",
        "ph_password": "Password",
        "ph_new_username": "New username",
        "ph_new_password": "Password (min 6 chars)",
        
        // --- Landing Page Static ---
        "lp_nav_user": "User Dashboard",
        "lp_nav_admin": "Admin Dashboard",
        "lp_nav_download": "Download Android App",
        "lp_stat_1": "100K+",
        "lp_stat_1_desc": "Scanned Images",
        "lp_stat_2": "99.8%",
        "lp_stat_2_desc": "Accuracy",
        "lp_stat_3": "< 2s",
        "lp_stat_3_desc": "Processing Time",
        "lp_tag_tech": "Technology",
        "lp_title_tech": "Core Technology",
        "lp_desc_tech": "Combining the most advanced Deep Learning models to analyze forged images at the pixel level.",
        "lp_tag_process": "Process",
        "lp_title_process": "How It Works",
        "lp_desc_process": "Just 3 simple steps to get professional analysis results.",
        "lp_cta_title": "Ready to Protect <span class='gradient-text'>the Truth?</span>",
        "lp_cta_desc": "Create a free account and start analyzing images today.",
        "lp_cta_btn": "Get Started <i class='fa-solid fa-arrow-right'></i>",
        
        // --- Upload ---
        "upload_drag": "Drag & drop image here",
        "upload_or": "or <span class='text-gradient'>click to browse</span>",
        "upload_hint": "Supports JPG, PNG, WEBP",
        "btn_analyze": "Analyze Image",
        "upload_batch_hint": "Drag & drop multiple images (Max 20)",
        "btn_analyze_batch": "Analyze Batch",

        // --- Results ---
        "res_title": "Detection Results",
        "res_placeholder": "Upload an image to see analysis",
        "lbl_confidence": "Confidence",
        "lbl_prob": "Fake Probability",
        "lbl_model": "Model",
        
        // --- Insights ---
        "lbl_heatmap": "Heatmap / Grad-CAM",
        "lbl_metadata": "Metadata / Noise Analysis",
        "lbl_fft": "Spatial Frequency Spectrum (FFT)",
        "lbl_noise_bg": "Background Noise:",
        "lbl_noise_edge": "Facial Edges:",
        "lbl_noise_comp": "Compression Artifacts:",
        "val_analyzing": "Analyzing...",
        "heatmap_placeholder": "Suspicious regions will appear here",

        // --- Dynamic JS Strings (EN) ---
        "fake_img": "FAKE IMAGE (AI)",
        "real_img": "REAL IMAGE",
        "noise_fake_bg": "Anomalous (High noise spectrum)",
        "noise_fake_edge": "Blending artifacts detected",
        "noise_fake_comp": "DCT matrix inconsistencies",
        "noise_real_bg": "Natural (Uniform distribution)",
        "noise_real_edge": "Smooth, no edge artifacts",
        "noise_real_comp": "Consistent (Original)",

        // --- Admin ---
        "admin_title": "Admin Control Center",
        "admin_subtitle": "System detection data management",
        "tab_stats": "Analytics",
        "tab_models": "Model Manager",
        "tab_tokens": "Add Tokens",
        "tab_ui": "UI Customization",
        "admin_login_as": "Logged in as:",
        
        // --- Admin Stats ---
        "stat_total": "Total Scans",
        "stat_users": "Total Users",
        "stat_fake_rate": "Fake Rate",
        "stat_top_model": "Top Model",
        "chart_fake_real": "Fake / Real Ratio",
        "chart_model_usage": "Model Usage",
        "chart_timeline": "Scans over Time",

        // --- Admin Models ---
        "col_model_name": "Model Name",
        "col_desc": "Description",
        "col_status": "Status",
        "col_action": "Action",
        "col_model_id": "Model ID",
        "admin_models_desc": "Enable or disable models. Disabled models cannot be used.",
        "loading_models": "Loading models...",

        // --- Admin Token ---
        "token_user": "Username",
        "token_amount": "Tokens to Add",
        "btn_add_token": "Add Tokens",
        "ph_token_username": "Enter username to add tokens",

        // --- Admin History ---
        "hist_search_user": "Search User/Filename",
        "ph_search_user": "Enter user or filename...",
        "hist_filter_model": "Filter Model",
        "hist_filter_label": "Filter Verdict",
        "col_time": "Time",
        "col_user": "User",
        "col_filename": "Filename",
        "col_model": "Model",
        "col_prob": "Fake Probability",
        "col_verdict": "Verdict",
        "loading_data": "Loading data...",

        // --- Admin UI ---
        "ui_desc": "Change colors, content, images and toggle sections on the landing page.",
        "btn_preview": "Preview",
        "btn_save_changes": "Save Changes",
        "ui_colors": "Colors",
        "ui_bg1": "Background 1",
        "ui_bg2": "Background 2",
        "ui_bg3": "Background 3",
        "ui_primary": "Primary Color",
        "ui_accent": "Accent Color",
        "ui_text": "Text Color",
        
        "ui_general": "General Information",
        "ui_site_name": "Site Name",
        "ui_slogan": "Slogan",
        "ui_footer": "Footer Text",

        "ui_hero": "Hero Banner",
        "ui_hero_l1": "Title Line 1",
        "ui_hero_l2": "Title Line 2",
        "ui_hero_desc": "Detailed Description",
        "ui_hero_cta": "Call to Action Button",

        "ui_features": "3 Features",
        "ui_f1": "Feature 1",
        "ui_f2": "Feature 2",
        "ui_f3": "Feature 3",
        "ui_f_title": "Title",
        "ui_f_desc": "Description",

        "ui_steps": "3 Steps (How it Works)",
        "ui_s1": "Step 1",
        "ui_s2": "Step 2",
        "ui_s3": "Step 3",

        "ui_toggles": "Toggle Sections",
        "ui_show_stats": "Statistics",
        "ui_show_marquee": "Marquee",
        "ui_show_features": "Features",
        "ui_show_steps": "How it Works",
        "ui_show_cta": "Bottom CTA",
        "ui_logo": "Site Logo",
        "ui_logo_upload": "Upload Logo",
        "btn_reset": "Restore Defaults",
        // --- Extra Missing ---
        "ph_search": "Search features, models, history...",
        "desc_single_scan": "Quick analysis of a single image with advanced visual forensics.",
        "lbl_select_model": "Select AI Model",
        "app_footer": "&copy; 2026 CNN Detection AI - Deepfake Detection Solutions",
        "lp_goto_dashboard": "Go to Dashboard",
        "lp_footer": "&copy; 2026 CNN Detection Hub &mdash; AI Deepfake Detection Platform",

        // --- Pricing & Upload ---
        "pricing_title": "Top up Tokens",
        "pricing_subtitle": "Choose a suitable Token package to continue using the Deepfake AI analysis system.",
        "btn_buy_now": "Buy Now",
        "badge_popular": "🔥 MOST POPULAR",
        "feat_basic_1": "Basic image analysis",
        "feat_basic_2": "History support",
        "feat_adv_1": "Advanced image analysis",
        "feat_adv_2": "Batch Scan support",
        "feat_adv_3": "Save 10%",
        "feat_exp_1": "All premium features",
        "feat_exp_2": "Priority analysis (Fast)",
        "feat_exp_3": "Save 20%",
        "txt_tokens": "Tokens",
        "admin_pricing_title": "Token Pricing Configuration",
        "admin_pricing_basic": "Basic Package",
        "admin_pricing_adv": "Advanced Package",
        "admin_pricing_exp": "Expert Package",
        "ph_pkg_name": "Package Name",
        "ph_pkg_price": "Price",
        "ph_pkg_tokens": "Tokens",
        "filter_all_models": "All models",
        "filter_all": "All",

        // --- Admin Missing ---
        "tab_payments": "Payment History",
        "tab_pages": "CMS Pages",
        "tab_notifications": "Notifications",
        "tab_ai_config": "AI Configuration",
        "tab_pages_title": "CMS Page Management",
        "tab_ai_title": "AI Translation Configuration",
        "tab_notif_title": "Notification Management",
        "title_invoice_detail": "Invoice Details",
        "title_edit_page": "Page Editor",
        "title_send_notif": "Send New Notification",

        // --- Index Missing ---
        "nav_documents": "Documents",
        "about_tag": "DSC2F Graduation Thesis",
        "about_title": "About CNN Detection",
        "about_mission_title": "Mission",
        "about_mission_desc": "In the era of AI, the line between real and fake is blurring. CNN Detection provides a powerful tool to easily detect AI-manipulated or AI-generated images (Deepfakes).",
        "about_tech_title": "Advanced Technology",
        "about_tech_desc": "Utilizing Dual Stream CNNs. By analyzing both spatial (RGB) and frequency (Noise) data, the model detects subtle manipulation traces invisible to the naked eye.",
        "about_team_title": "Development Team",
        "about_team_desc": "Developed by the DSC2F Thesis Research Group with great dedication. Committed to continuously updating the latest AI models (ResNet, EfficientNet) to counter increasingly sophisticated forgery techniques.",
        "legal_tag": "Legal & Trust",
        "legal_privacy_title": "Privacy Policy",
        "legal_privacy_desc": "How we collect, use, and protect your personal data.",
        "legal_badge_req": "Required",
        "legal_view_more": "View Details",
        "legal_terms_title": "Terms of Service",
        "legal_terms_desc": "Rules and conditions when using the CNN Detection app.",
        "legal_data_title": "Data Deletion",
        "legal_data_desc": "Request account and data deletion from the system.",
        "legal_badge_warn": "Usually Required",
        "legal_ai_title": "AI Policy",
        "legal_ai_desc": "How AI works, Deep Learning models, and analysis limitations.",
        "legal_badge_apple": "Highly rated by Apple",
        "legal_support_title": "Support & Contact",
        "legal_support_desc": "FAQs, guides, bug reporting, and support team contact info.",
        "legal_badge_rec": "Recommended",
        "footer_desc": "Advanced AI image detection app, using Deep Learning to detect Deepfakes. Supports Web, Android & iOS platforms.",
        "footer_col1": "Legal",
        "footer_col2": "Products",
        "footer_col3": "Support",
    }
};

function getLang() {
    return localStorage.getItem('app_lang') || 'vi';
}

function setLang(lang) {
    if (['vi', 'en'].includes(lang)) {
        localStorage.setItem('app_lang', lang);
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
    
    // Dịch các thẻ nội dung (innerHTML / value)
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

    // Dịch các placeholders (thẻ input, textarea)
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
        btn.innerText = lang === 'vi' ? 'EN' : 'VI';
        btn.title = lang === 'vi' ? 'Switch to English' : 'Chuyển sang Tiếng Việt';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Inject Language Toggle Button dynamically if container exists
    const headers = document.querySelectorAll('.site-header .site-nav, .landing-header');
    if (headers.length > 0) {
        const header = headers[0];
        const btn = document.createElement('button');
        btn.id = 'lang-toggle';
        btn.className = 'btn-lang-toggle';
        btn.onclick = () => {
            const currentLang = getLang();
            setLang(currentLang === 'vi' ? 'en' : 'vi');
            // Dispatch event so app.js can re-render dynamic strings if needed
            window.dispatchEvent(new Event('languageChanged'));
        };
        header.insertBefore(btn, header.firstChild);
        updateLangButton(getLang());
    }

    applyTranslations();
});
