"""
🌙 AI Deepfake Detector - Professional Dark Mode
✨ Dashboard-style Interface với Typography hiện đại
🚀 Bố cục 3 vùng: Sidebar - Main Canvas - Results Panel
"""

import os
import sys
import torch
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageEnhance
import torchvision.transforms as transforms
import numpy as np
import threading
from datetime import datetime
import time
import math


class ProfessionalDarkGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🌙 AI Detector Pro - Dark Mode")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#121212')
        self.root.resizable(True, True)
        
        # Language & Variables
        self.setup_language_texts()
        self.setup_variables()
        
        # Professional Dark Theme
        self.setup_dark_theme()
        
        # Create Professional Dashboard
        self.create_dashboard_layout()
        
        # Load default model - phải khớp với giá trị mặc định của dropdown
        self.on_model_changed()  # Sẽ load model dựa trên giá trị dropdown hiện tại
    
    def setup_language_texts(self):
        """Thiết lập ngôn ngữ tiếng Việt chuyên nghiệp"""
        self.texts = {
            'app_name': 'AI DETECTOR PRO',
            'tagline': 'Hệ Thống Phát Hiện Ảnh Giả Mạo Chuyên Nghiệp',
            'dashboard': 'Dashboard',
            'history': 'Lịch Sử', 
            'settings': 'Cài Đặt',
            'model_select': 'Chọn Mô Hình AI',
            'upload': 'Tải Ảnh Lên',
            'browse_file': '📁 Chọn Tập Tin',
            'drag_drop': '⬇ Kéo thả ảnh vào đây ⬇',
            'analysis': '🔍 PHÂN TÍCH',
            'results': 'KẾT QUẢ',
            'status': 'Trạng Thái',
            'probability': 'Xác Suất',
            'verdict': 'Kết Luận',
            'metadata': 'Thông Tin',
            'real': 'THẬT',
            'fake': 'GIẢ',
            'uncertain': 'KHÔNG RÕ',
            'ready': 'Sẵn sàng',
            'analyzing': 'Đang phân tích...',
            'complete': 'Hoàn thành',
            'cpu_mode': 'CPU',
            'gpu_mode': 'GPU'
        }
    
    def setup_variables(self):
        """Thiết lập biến"""
        self.model = None
        self.model_type = 'enhanced'  # Phải khớp với dropdown default
        self.model_loaded = False
        self.current_image_path = None
        self.current_fft_image = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.history = []
        self.animation_running = True
        
    def setup_dark_theme(self):
        """🎨 Professional Dark Theme Colors"""
        self.colors = {
            # Dark Mode Backgrounds
            'bg_primary': '#121212',        # Main background
            'bg_secondary': '#1E1E2E',      # Container background  
            'bg_tertiary': '#252535',       # Card background
            'bg_surface': '#2D2D40',        # Surface elements
            'bg_elevated': '#363649',       # Elevated surfaces
            
            # Professional Accents
            'accent_primary': '#00E5FF',    # Cyan Neon (main)
            'accent_success': '#00E676',    # Green Neon (success)
            'accent_danger': '#FF1744',     # Red Neon (danger)
            'accent_warning': '#FFAB00',    # Amber Neon (warning)
            'accent_info': '#2979FF',       # Blue Neon (info)
            
            # Typography
            'text_primary': '#FFFFFF',      # White text
            'text_secondary': '#B3B3B3',   # Light grey
            'text_muted': '#666666',        # Dark grey
            'text_disabled': '#404040',     # Very dark grey
            
            # Borders & Dividers
            'border_primary': '#333333',
            'border_secondary': '#404040',
            'divider': '#2A2A2A'
        }
        
        # Setup modern TTK styles
        self.setup_professional_styles()
        
    def setup_professional_styles(self):
        """Thiết lập styles chuyên nghiệp"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern Dropdown/Combobox Style
        style.configure('Dark.TCombobox',
                       fieldbackground=self.colors['bg_tertiary'],
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       arrowcolor=self.colors['accent_primary'],
                       borderwidth=1,
                       relief='flat')
        
        # Professional Button Style  
        style.configure('Pro.TButton',
                       background=self.colors['accent_primary'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat',
                       padding=(20, 12))
        
        style.map('Pro.TButton',
                 background=[('active', self.colors['accent_info'])])
        
    def create_dashboard_layout(self):
        """🏗️ Tạo bố cục dashboard chuyên nghiệp 3 vùng"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Top Navigation Bar
        self.create_top_navigation(main_container)
        
        # Content area with 3 columns
        content_frame = tk.Frame(main_container, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Left Sidebar (Settings)
        self.create_left_sidebar(content_frame)
        
        # Main Canvas (Image Preview)
        self.create_main_canvas(content_frame)
        
        # Right Panel (Results)
        self.create_right_panel(content_frame)
        
    def create_top_navigation(self, parent):
        """🔝 Tạo thanh navigation trên cùng"""
        nav_frame = tk.Frame(parent, bg=self.colors['bg_secondary'], height=70)
        nav_frame.pack(fill=tk.X, padx=20, pady=(20, 20))
        nav_frame.pack_propagate(False)
        
        # Left side - Logo & App name
        left_nav = tk.Frame(nav_frame, bg=self.colors['bg_secondary'])
        left_nav.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=15)
        
        # Logo & Title
        title_frame = tk.Frame(left_nav, bg=self.colors['bg_secondary'])
        title_frame.pack(side=tk.LEFT)
        
        app_logo = tk.Label(title_frame,
                           text="🌙",
                           bg=self.colors['bg_secondary'],
                           fg=self.colors['accent_primary'],
                           font=('Inter', 24, 'bold'))
        app_logo.pack(side=tk.LEFT, padx=(0, 10))
        
        app_title = tk.Label(title_frame,
                           text=self.texts['app_name'],
                           bg=self.colors['bg_secondary'],
                           fg=self.colors['text_primary'],
                           font=('Inter', 18, 'bold'))
        app_title.pack(side=tk.LEFT)
        
        app_subtitle = tk.Label(title_frame,
                              text=self.texts['tagline'],
                              bg=self.colors['bg_secondary'],
                              fg=self.colors['text_secondary'],
                              font=('Inter', 10))
        app_subtitle.pack(side=tk.LEFT, padx=(10, 0))
        
        # Right side - Device info & Toggle
        right_nav = tk.Frame(nav_frame, bg=self.colors['bg_secondary'])
        right_nav.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=15)
        
        # Device toggle
        device_frame = tk.Frame(right_nav, bg=self.colors['bg_secondary'])
        device_frame.pack(side=tk.RIGHT)
        
        device_label = tk.Label(device_frame,
                              text=f"{self.texts['gpu_mode' if self.device == 'cuda' else 'cpu_mode']}:",
                              bg=self.colors['bg_secondary'],
                              fg=self.colors['text_secondary'],
                              font=('Inter', 11))
        device_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status indicator
        self.device_indicator = tk.Canvas(device_frame, width=12, height=12,
                                        bg=self.colors['bg_secondary'], highlightthickness=0)
        self.device_indicator.pack(side=tk.LEFT)
        
        color = self.colors['accent_success'] if self.device == 'cuda' else self.colors['accent_warning']
        self.device_indicator.create_oval(2, 2, 10, 10, fill=color, outline='')
        
        device_text = torch.cuda.get_device_name(0) if self.device == 'cuda' else 'Intel CPU'
        device_name = tk.Label(device_frame,
                             text=device_text,
                             bg=self.colors['bg_secondary'],
                             fg=color,
                             font=('Inter', 11, 'bold'))
        device_name.pack(side=tk.LEFT, padx=(8, 0))
        
    def create_left_sidebar(self, parent):
        """📋 Tạo sidebar bên trái (Settings)"""
        sidebar_width = 280
        sidebar = tk.Frame(parent, bg=self.colors['bg_tertiary'], width=sidebar_width)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        sidebar.pack_propagate(False)
        
        # Sidebar header
        sidebar_header = tk.Frame(sidebar, bg=self.colors['bg_tertiary'], height=50)
        sidebar_header.pack(fill=tk.X, padx=20, pady=(20, 10))
        sidebar_header.pack_propagate(False)
        
        tk.Label(sidebar_header,
                text=self.texts['settings'],
                bg=self.colors['bg_tertiary'],
                fg=self.colors['text_primary'],
                font=('Inter', 16, 'bold')).pack(anchor='w', pady=10)
        
        # Model Selection Section
        self.create_model_selection_section(sidebar)
        
        # Upload Section  
        self.create_upload_section(sidebar)
        
        # History Section
        self.create_history_section(sidebar)
        
    def create_model_selection_section(self, parent):
        """🧠 Section chọn model AI"""
        section = tk.Frame(parent, bg=self.colors['bg_tertiary'])
        section.pack(fill=tk.X, padx=20, pady=(10, 20))
        
        # Section title
        tk.Label(section,
                text=self.texts['model_select'],
                bg=self.colors['bg_tertiary'],
                fg=self.colors['text_secondary'],
                font=('Inter', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Modern Dropdown
        self.model_var = tk.StringVar(value='Enhanced Dual-Stream (Mới nhất)')
        
        models = [
            'ResNet50 Đơn Luồng',
            'CNN Hai Luồng', 
            'ResNet Hai Luồng',
            'Enhanced Dual-Stream (Mới nhất)',
            'Custom (Gemini + Điện thoại)'
        ]
        
        model_combo = ttk.Combobox(section, 
                                  textvariable=self.model_var,
                                  values=models,
                                  state='readonly',
                                  style='Dark.TCombobox',
                                  font=('Inter', 11))
        model_combo.pack(fill=tk.X, pady=(0, 10))
        model_combo.bind('<<ComboboxSelected>>', self.on_model_changed)
        
        # Model info
        self.model_info_label = tk.Label(section,
                                       text="AUC: 99.39% • Độ chính xác cao nhất",
                                       bg=self.colors['bg_tertiary'],
                                       fg=self.colors['accent_success'],
                                       font=('Inter', 10))
        self.model_info_label.pack(anchor='w')
        
    def create_upload_section(self, parent):
        """📁 Section upload file"""
        section = tk.Frame(parent, bg=self.colors['bg_tertiary'])
        section.pack(fill=tk.X, padx=20, pady=(10, 20))
        
        # Section title
        tk.Label(section,
                text=self.texts['upload'],
                bg=self.colors['bg_tertiary'],
                fg=self.colors['text_secondary'],
                font=('Inter', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Browse button
        self.browse_btn = self.create_pro_button(section,
                                               self.texts['browse_file'],
                                               self.colors['accent_primary'],
                                               self.select_image)
        self.browse_btn.pack(fill=tk.X)
        
    def create_history_section(self, parent):
        """📜 Section lịch sử"""
        section = tk.Frame(parent, bg=self.colors['bg_tertiary'])
        section.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))
        
        # Section title
        tk.Label(section,
                text=self.texts['history'],
                bg=self.colors['bg_tertiary'],
                fg=self.colors['text_secondary'],
                font=('Inter', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # History list container
        history_container = tk.Frame(section, bg=self.colors['bg_surface'])
        history_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollable history list
        self.history_frame = tk.Frame(history_container, bg=self.colors['bg_surface'])
        self.history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Placeholder
        tk.Label(self.history_frame,
                text="Chưa có lịch sử phân tích",
                bg=self.colors['bg_surface'],
                fg=self.colors['text_muted'],
                font=('Inter', 10)).pack(pady=20)
        
    def create_main_canvas(self, parent):
        """🖼️ Tạo main canvas để hiển thị ảnh"""
        canvas_frame = tk.Frame(parent, bg=self.colors['bg_secondary'])
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Canvas header
        header = tk.Frame(canvas_frame, bg=self.colors['bg_secondary'], height=50)
        header.pack(fill=tk.X, padx=20, pady=(20, 0))
        header.pack_propagate(False)
        
        tk.Label(header,
                text="🔬 VÙNG PHÂN TÍCH CHÍNH",
                bg=self.colors['bg_secondary'],
                fg=self.colors['text_primary'],
                font=('Inter', 16, 'bold')).pack(anchor='w', pady=10)
        
        # Image display area
        display_area = tk.Frame(canvas_frame, bg=self.colors['bg_secondary'])
        display_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))
        
        # RGB Image Panel
        rgb_panel = tk.Frame(display_area, bg=self.colors['bg_tertiary'])
        rgb_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))
        
        rgb_title = tk.Label(rgb_panel,
                           text="📷 Hình Ảnh RGB (Miền Không Gian)",
                           bg=self.colors['bg_tertiary'],
                           fg=self.colors['accent_info'],
                           font=('Inter', 12, 'bold'))
        rgb_title.pack(pady=(15, 10))
        
        # RGB Display with drag & drop styling
        self.rgb_display = tk.Frame(rgb_panel, bg=self.colors['bg_surface'], 
                                   relief='solid', bd=2, highlightcolor=self.colors['border_primary'])
        self.rgb_display.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        self.rgb_label = tk.Label(self.rgb_display,
                                text=self.texts['drag_drop'],
                                bg=self.colors['bg_surface'],
                                fg=self.colors['text_muted'],
                                font=('Inter', 14),
                                cursor='hand2')
        self.rgb_label.pack(fill=tk.BOTH, expand=True)
        self.rgb_label.bind('<Button-1>', lambda e: self.select_image())
        
        # Configure drag & drop styling
        self.configure_drag_drop_style(self.rgb_display)
        
        # FFT Panel
        fft_panel = tk.Frame(display_area, bg=self.colors['bg_tertiary'])
        fft_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(7, 0))
        
        fft_title = tk.Label(fft_panel,
                           text="📊 Phổ FFT (Miền Tần Số)",
                           bg=self.colors['bg_tertiary'],
                           fg=self.colors['accent_primary'],
                           font=('Inter', 12, 'bold'))
        fft_title.pack(pady=(15, 10))
        
        # FFT Display
        self.fft_display = tk.Frame(fft_panel, bg=self.colors['bg_surface'],
                                   relief='solid', bd=2, highlightcolor=self.colors['border_primary'])
        self.fft_display.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        self.fft_label = tk.Label(self.fft_display,
                                text="Phổ tần số sẽ hiển thị ở đây",
                                bg=self.colors['bg_surface'],
                                fg=self.colors['text_muted'],
                                font=('Inter', 12))
        self.fft_label.pack(fill=tk.BOTH, expand=True)
        
    def create_right_panel(self, parent):
        """📊 Tạo panel bên phải (Results & Controls)"""
        panel_width = 320
        panel = tk.Frame(parent, bg=self.colors['bg_tertiary'], width=panel_width)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)
        
        # Panel header
        header = tk.Frame(panel, bg=self.colors['bg_tertiary'], height=50)
        header.pack(fill=tk.X, padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        tk.Label(header,
                text=self.texts['results'],
                bg=self.colors['bg_tertiary'],
                fg=self.colors['text_primary'],
                font=('Inter', 16, 'bold')).pack(anchor='w', pady=10)
        
        # Analysis Button (Large)
        self.analysis_btn = self.create_pro_button(panel,
                                                 self.texts['analysis'],
                                                 self.colors['accent_success'],
                                                 self.analyze_image,
                                                 large=True)
        self.analysis_btn.pack(fill=tk.X, padx=20, pady=(0, 20))
        self.analysis_btn.config(state='disabled')
        
        # Results Display
        self.create_results_display(panel)
        
        # Metadata Display
        self.create_metadata_display(panel)
        
    def create_results_display(self, parent):
        """📈 Tạo display kết quả với donut chart"""
        results_frame = tk.Frame(parent, bg=self.colors['bg_surface'])
        results_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Status
        status_frame = tk.Frame(results_frame, bg=self.colors['bg_surface'])
        status_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        tk.Label(status_frame,
                text=self.texts['status'] + ':',
                bg=self.colors['bg_surface'],
                fg=self.colors['text_secondary'],
                font=('Inter', 11)).pack(side=tk.LEFT)
        
        self.status_label = tk.Label(status_frame,
                                   text=self.texts['ready'],
                                   bg=self.colors['bg_surface'],
                                   fg=self.colors['accent_primary'],
                                   font=('Inter', 11, 'bold'))
        self.status_label.pack(side=tk.RIGHT)
        
        # Probability Display (Circular Progress)
        prob_frame = tk.Frame(results_frame, bg=self.colors['bg_surface'])
        prob_frame.pack(pady=(10, 15))
        
        # Create circular progress canvas
        self.prob_canvas = tk.Canvas(prob_frame, width=120, height=120,
                                   bg=self.colors['bg_surface'], highlightthickness=0)
        self.prob_canvas.pack()
        
        self.draw_circular_progress(0)  # Initialize empty
        
        # Verdict Badge
        self.verdict_frame = tk.Frame(results_frame, bg=self.colors['bg_surface'])
        self.verdict_frame.pack(fill=tk.X, padx=15, pady=(10, 15))
        
        self.verdict_label = tk.Label(self.verdict_frame,
                                    text="---",
                                    bg=self.colors['bg_surface'],
                                    fg=self.colors['text_muted'],
                                    font=('Inter', 14, 'bold'))
        self.verdict_label.pack()
        
    def create_metadata_display(self, parent):
        """📋 Tạo display metadata"""
        meta_frame = tk.Frame(parent, bg=self.colors['bg_surface'])
        meta_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Title
        tk.Label(meta_frame,
                text=self.texts['metadata'],
                bg=self.colors['bg_surface'],
                fg=self.colors['text_secondary'],
                font=('Inter', 12, 'bold')).pack(anchor='w', padx=15, pady=(15, 10))
        
        # Metadata items
        self.metadata_container = tk.Frame(meta_frame, bg=self.colors['bg_surface'])
        self.metadata_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        self.metadata_items = {}
        metadata_fields = [
            ('filename', '📁 Tên tập tin:', '---'),
            ('dimensions', '📐 Kích thước:', '---'),
            ('filesize', '💾 Dung lượng:', '---'),
            ('format', '🖼️ Định dạng:', '---'),
            ('analysis_time', '⏱️ Thời gian:', '---')
        ]
        
        for key, label, default in metadata_fields:
            item_frame = tk.Frame(self.metadata_container, bg=self.colors['bg_surface'])
            item_frame.pack(fill=tk.X, pady=3)
            
            tk.Label(item_frame,
                    text=label,
                    bg=self.colors['bg_surface'],
                    fg=self.colors['text_muted'],
                    font=('Inter', 10),
                    width=12, anchor='w').pack(side=tk.LEFT)
            
            value_label = tk.Label(item_frame,
                                 text=default,
                                 bg=self.colors['bg_surface'],
                                 fg=self.colors['text_secondary'],
                                 font=('Inter', 10, 'bold'),
                                 anchor='w')
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.metadata_items[key] = value_label
            
    def configure_drag_drop_style(self, widget):
        """🎨 Cấu hình style drag & drop"""
        def on_drag_enter(event):
            widget.config(bg=self.colors['bg_elevated'], 
                         highlightcolor=self.colors['accent_primary'])
            
        def on_drag_leave(event):
            widget.config(bg=self.colors['bg_surface'],
                         highlightcolor=self.colors['border_primary'])
        
        widget.bind('<Enter>', on_drag_enter)
        widget.bind('<Leave>', on_drag_leave)
        
    def create_pro_button(self, parent, text, color, command, large=False):
        """🔘 Tạo button chuyên nghiệp"""
        height = 50 if large else 40
        font_size = 14 if large else 11
        
        btn = tk.Button(parent,
                       text=text,
                       bg=color,
                       fg='white',
                       font=('Inter', font_size, 'bold'),
                       relief='flat',
                       bd=0,
                       padx=20,
                       pady=height//4,
                       cursor='hand2',
                       command=command)
        
        # Hover effects
        def on_enter(e):
            if btn['state'] != 'disabled':
                btn.config(bg=self.lighten_color(color))
        
        def on_leave(e):
            if btn['state'] != 'disabled':
                btn.config(bg=color)
                
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def draw_circular_progress(self, percentage):
        """🎯 Vẽ circular progress cho xác suất"""
        self.prob_canvas.delete("all")
        
        # Background circle
        self.prob_canvas.create_oval(10, 10, 110, 110,
                                   outline=self.colors['border_secondary'],
                                   width=8, fill='')
        
        if percentage > 0:
            # Determine color based on percentage (percentage = fake probability)
            fake_prob = percentage
            real_prob = 100 - percentage
            
            if fake_prob < 30:  # Low fake probability = Real image
                color = self.colors['accent_success']
                label = self.texts['real']
                display_percentage = real_prob  # Show real probability
            elif fake_prob < 70:  # Medium fake probability = Uncertain
                color = self.colors['accent_warning']
                label = self.texts['uncertain']
                display_percentage = max(fake_prob, real_prob)  # Show higher probability
            else:  # High fake probability = Fake image
                color = self.colors['accent_danger']
                label = self.texts['fake']
                display_percentage = fake_prob  # Show fake probability
            
            # Progress arc
            extent = int(360 * percentage / 100)
            self.prob_canvas.create_arc(10, 10, 110, 110,
                                      start=90, extent=-extent,
                                      outline=color, width=8,
                                      style='arc')
            
            # Center text - show dominant probability
            self.prob_canvas.create_text(60, 50,
                                       text=f"{display_percentage:.1f}%",
                                       fill=color,
                                       font=('Inter', 16, 'bold'))
            
            # Dynamic label based on what we're showing
            if fake_prob < 30:
                prob_label = "Xác suất thật"
            elif fake_prob < 70:
                prob_label = "Độ tin cậy"
            else:
                prob_label = "Xác suất giả"
                
            self.prob_canvas.create_text(60, 70,
                                       text=prob_label,
                                       fill=self.colors['text_secondary'],
                                       font=('Inter', 9))
            
            # Update verdict
            self.verdict_label.config(text=label, fg=color)
        else:
            # Empty state
            self.prob_canvas.create_text(60, 60,
                                       text="---%",
                                       fill=self.colors['text_muted'],
                                       font=('Inter', 16, 'bold'))
    
    def lighten_color(self, color, amount=20):
        """Làm sáng màu"""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, c + amount) for c in rgb)
        return '#%02x%02x%02x' % rgb
    
    # Model & Analysis Methods
    def on_model_changed(self, event=None):
        """Xử lý khi thay đổi model"""
        selected = self.model_var.get()
        
        if 'Đơn Luồng' in selected:
            model_type = 'single'
            info = "AUC: ~95% • Tốc độ nhanh"
            color = self.colors['accent_warning']
        elif 'CNN Hai Luồng' in selected:
            model_type = 'dual_stream'
            info = "AUC: 99.14% • Cân bằng tốc độ/độ chính xác"
            color = self.colors['accent_info']
        elif 'Custom' in selected:
            model_type = 'custom'
            info = "🎨 Train với Gemini + Ảnh điện thoại"
            color = self.colors['accent_warning']
        elif 'Enhanced' in selected:
            model_type = 'enhanced'
            info = "🚀 Mới nhất • SRM + Attention • Phát hiện Gemini/DALL-E"
            color = self.colors['accent_success']
        else:
            model_type = 'dual_resnet'
            info = "AUC: 99.39% • Độ chính xác cao"
            color = self.colors['accent_success']
            
        self.model_info_label.config(text=info, fg=color)
        self.load_model_async(model_type)
    
    def load_model_async(self, model_type):
        """Load model bất đồng bộ"""
        self.model_loaded = False
        self.status_label.config(text="Đang tải model...", 
                               fg=self.colors['accent_warning'])
        
        def load_model():
            try:
                if model_type == 'single':
                    # Load single-stream ResNet model
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from networks.resnet import resnet50
                    
                    model_path = os.path.join('weights', 'blur_jpg_prob0.5.pth')
                    if not os.path.exists(model_path):
                        raise FileNotFoundError(f"Model file not found: {model_path}")
                    
                    self.model = resnet50(num_classes=1)
                    state_dict = torch.load(model_path, map_location=self.device, weights_only=False)
                    self.model.load_state_dict(state_dict['model'])
                    
                elif model_type == 'dual_stream':
                    # Load dual-stream CNN model
                    from networks.dual_stream_cnn import DualStreamCNN
                    
                    model_path = os.path.join('weights', 'dual_stream', 'best_model.pth')
                    self.model = DualStreamCNN(num_classes=1)
                    
                    if os.path.exists(model_path):
                        state_dict = torch.load(model_path, map_location=self.device, weights_only=False)
                        self.model.load_state_dict(state_dict['model'])
                
                elif model_type == 'dual_resnet':
                    # Load dual-stream ResNet model
                    from networks.dual_stream_resnet import DualStreamResNet
                    
                    model_path = os.path.join('weights', 'dual_stream_resnet', 'best_model.pth')
                    self.model = DualStreamResNet(num_classes=1, pretrained=False)
                    
                    if os.path.exists(model_path):
                        state_dict = torch.load(model_path, map_location=self.device, weights_only=False)
                        self.model.load_state_dict(state_dict['model'])
                
                elif model_type == 'enhanced':
                    # Load Enhanced Dual-Stream model (mới nhất)
                    from networks.enhanced_dual_stream import EnhancedDualStreamCNN
                    
                    model_path = os.path.join('weights', 'enhanced', 'best_model.pth')
                    self.model = EnhancedDualStreamCNN(num_classes=1)
                    
                    if os.path.exists(model_path):
                        state_dict = torch.load(model_path, map_location=self.device, weights_only=False)
                        if 'model' in state_dict:
                            self.model.load_state_dict(state_dict['model'])
                        else:
                            self.model.load_state_dict(state_dict)
                    else:
                        print(f"⚠️ Model chưa được train: {model_path}")
                        print("💡 Sẽ sử dụng model chưa train (random weights)")
                
                elif model_type == 'custom':
                    # Load Custom model (trained với Gemini + Điện thoại)
                    from networks.enhanced_dual_stream import EnhancedDualStreamCNN
                    
                    model_path = os.path.join('weights', 'custom', 'best_model.pth')
                    self.model = EnhancedDualStreamCNN(num_classes=1)
                    
                    if os.path.exists(model_path):
                        state_dict = torch.load(model_path, map_location=self.device, weights_only=False)
                        if 'model' in state_dict:
                            self.model.load_state_dict(state_dict['model'])
                        else:
                            self.model.load_state_dict(state_dict)
                        print(f"✓ Loaded custom model (acc: {state_dict.get('best_acc', 'N/A')}%)")
                    else:
                        raise FileNotFoundError(
                            "Chưa có model custom!\n"
                            "Hãy train trước:\n"
                            "1. Đặt ảnh vào dataset/custom/train/REAL và FAKE\n"
                            "2. Chạy: python train_custom.py"
                        )
                
                # Move model to device
                if self.device == 'cuda' and torch.cuda.is_available():
                    self.model.cuda()
                
                self.model.eval()
                self.model_type = model_type
                self.model_loaded = True
                
                # Update UI on main thread
                self.root.after(0, self.on_model_loaded)
                
            except Exception as e:
                self.root.after(0, lambda: self.on_model_error(str(e)))
        
        threading.Thread(target=load_model, daemon=True).start()
    
    def on_model_loaded(self):
        """Xử lý khi model được tải thành công"""
        self.status_label.config(text=self.texts['ready'],
                               fg=self.colors['accent_success'])
        
        if self.current_image_path:
            self.analysis_btn.config(state='normal',
                                   bg=self.colors['accent_success'])
    
    def on_model_error(self, error_msg):
        """Xử lý lỗi khi tải model"""
        self.status_label.config(text="Lỗi tải model",
                               fg=self.colors['accent_danger'])
        messagebox.showerror("Lỗi", f"Không thể tải model: {error_msg}")
    
    def select_image(self):
        """Chọn file ảnh"""
        file_path = filedialog.askopenfilename(
            title="Chọn hình ảnh để phân tích",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.current_image_path = file_path
            self.load_image_display(file_path)
            
            if self.model_loaded:
                self.analysis_btn.config(state='normal',
                                       bg=self.colors['accent_success'])
    
    def load_image_display(self, file_path):
        """Hiển thị ảnh và FFT"""
        try:
            # Load image
            image = Image.open(file_path)
            
            # Display RGB image
            rgb_display = image.copy()
            rgb_display.thumbnail((400, 400), Image.Resampling.LANCZOS)
            rgb_photo = ImageTk.PhotoImage(rgb_display)
            
            self.rgb_label.config(image=rgb_photo, text="")
            self.rgb_label.image = rgb_photo
            
            # Generate FFT display
            self.generate_fft_display(image)
            
            # Update metadata
            self.update_metadata(file_path, image)
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải ảnh: {str(e)}")
    
    def generate_fft_display(self, image):
        """Tạo hiển thị FFT"""
        try:
            # Convert to grayscale và resize
            gray = image.convert('L').resize((224, 224), Image.Resampling.LANCZOS)
            gray_array = np.array(gray, dtype=np.float32) / 255.0
            
            # Compute FFT
            fft = np.fft.fft2(gray_array)
            fft_shift = np.fft.fftshift(fft)
            magnitude = np.abs(fft_shift)
            magnitude_log = np.log1p(magnitude)
            
            # Normalize
            magnitude_norm = (magnitude_log - magnitude_log.min()) / (magnitude_log.max() - magnitude_log.min())
            magnitude_norm = (magnitude_norm * 255).astype(np.uint8)
            
            # Create colorful FFT
            fft_colored = self.apply_fft_colormap(magnitude_norm)
            
            # Display
            fft_display = fft_colored.copy()
            fft_display.thumbnail((400, 400), Image.Resampling.LANCZOS)
            fft_photo = ImageTk.PhotoImage(fft_display)
            
            self.fft_label.config(image=fft_photo, text="")
            self.fft_label.image = fft_photo
            
        except Exception as e:
            print(f"FFT generation error: {e}")
            self.fft_label.config(text=f"Lỗi tạo FFT: {str(e)[:20]}...")
    
    def apply_fft_colormap(self, magnitude):
        """Áp dụng colormap cho FFT"""
        colored = np.zeros((magnitude.shape[0], magnitude.shape[1], 3), dtype=np.uint8)
        
        # Cyan colormap for dark theme
        colored[:, :, 0] = magnitude * 0.3  # Red
        colored[:, :, 1] = magnitude * 0.8  # Green  
        colored[:, :, 2] = magnitude        # Blue (full cyan)
        
        return Image.fromarray(colored, mode='RGB')
    
    def update_metadata(self, file_path, image):
        """Cập nhật metadata"""
        try:
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            metadata = {
                'filename': os.path.basename(file_path),
                'dimensions': f"{image.width} × {image.height}",
                'filesize': f"{file_size_mb:.2f} MB" if file_size_mb >= 1 else f"{file_size//1024} KB",
                'format': image.format or 'Unknown'
            }
            
            for key, value in metadata.items():
                if key in self.metadata_items:
                    self.metadata_items[key].config(text=str(value))
                    
        except Exception as e:
            print(f"Metadata update error: {e}")
    
    def analyze_image(self):
        """Phân tích ảnh"""
        if not self.current_image_path or not self.model_loaded:
            messagebox.showwarning("Cảnh báo", "Vui lòng tải model và chọn ảnh trước.")
            return
        
        # Disable button during analysis
        self.analysis_btn.config(state='disabled', bg=self.colors['text_disabled'])
        self.status_label.config(text=self.texts['analyzing'],
                               fg=self.colors['accent_warning'])
        
        def analyze():
            try:
                start_time = time.time()
                
                # DEBUG: Print model info
                print(f"[DEBUG] Model type: {self.model_type}")
                print(f"[DEBUG] Model loaded: {self.model_loaded}")
                print(f"[DEBUG] Image path: {self.current_image_path}")
                
                # Load and preprocess image
                image = Image.open(self.current_image_path)
                
                if self.model_type == 'single':
                    # Single stream preprocessing
                    transform = transforms.Compose([
                        transforms.Resize((224, 224)),
                        transforms.ToTensor(),
                        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                    ])
                    
                    rgb_tensor = transform(image.convert('RGB')).unsqueeze(0)
                    if self.device == 'cuda':
                        rgb_tensor = rgb_tensor.cuda()
                    
                    with torch.no_grad():
                        outputs = self.model(rgb_tensor)
                        probability = torch.sigmoid(outputs).item() * 100
                        
                else:
                    # Dual stream preprocessing
                    # Enhanced, custom và dual_stream cần 224x224, dual_resnet cần 32x32
                    if self.model_type in ['dual_stream', 'enhanced', 'custom']:
                        image_size = (224, 224)
                    else:
                        image_size = (32, 32)
                    
                    print(f"[DEBUG] Image size: {image_size}")
                    
                    rgb_transform = transforms.Compose([
                        transforms.Resize(image_size),
                        transforms.ToTensor(),
                        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                    ])
                    
                    rgb_tensor = rgb_transform(image.convert('RGB')).unsqueeze(0)
                    fft_tensor = self.prepare_fft_tensor(image)
                    
                    print(f"[DEBUG] RGB tensor shape: {rgb_tensor.shape}")
                    print(f"[DEBUG] FFT tensor shape: {fft_tensor.shape}")
                    
                    if self.device == 'cuda':
                        rgb_tensor = rgb_tensor.cuda()
                        fft_tensor = fft_tensor.cuda()
                    
                    with torch.no_grad():
                        outputs = self.model(rgb_tensor, fft_tensor)
                        probability = torch.sigmoid(outputs).item() * 100
                        print(f"[DEBUG] Raw output: {outputs.item():.4f}")
                        print(f"[DEBUG] Probability: {probability:.1f}%")
                
                analysis_time = time.time() - start_time
                
                # Update UI
                self.root.after(0, lambda: self.display_results(probability, analysis_time))
                
            except Exception as e:
                self.root.after(0, lambda: self.on_analysis_error(str(e)))
        
        threading.Thread(target=analyze, daemon=True).start()
    
    def prepare_fft_tensor(self, image):
        """Chuẩn bị FFT tensor"""
        # Enhanced, custom và dual_stream cần 224, dual_resnet cần 32
        size = 224 if self.model_type in ['dual_stream', 'enhanced', 'custom'] else 32
        gray = image.convert('L').resize((size, size), Image.Resampling.LANCZOS)
        gray_array = np.array(gray, dtype=np.float32) / 255.0
        
        # Compute FFT
        fft = np.fft.fft2(gray_array)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)
        magnitude_log = np.log1p(magnitude)
        
        # Normalize
        magnitude_norm = (magnitude_log - magnitude_log.min()) / (magnitude_log.max() - magnitude_log.min())
        
        if self.model_type == 'dual_resnet':
            # dual_resnet: 3 channels 32x32
            fft_tensor = torch.from_numpy(magnitude_norm).unsqueeze(0).repeat(3, 1, 1).unsqueeze(0)
        elif self.model_type in ['enhanced', 'custom']:
            # enhanced/custom: 1 channel 224x224
            fft_tensor = torch.from_numpy(magnitude_norm).unsqueeze(0).unsqueeze(0)
        else:
            # dual_stream: 1 channel 224x224
            fft_tensor = torch.from_numpy(magnitude_norm).unsqueeze(0).unsqueeze(0)
        
        return fft_tensor.float()
    
    def display_results(self, probability, analysis_time):
        """Hiển thị kết quả"""
        # Debug info - print to console
        fake_prob = probability
        real_prob = 100 - probability
        print(f"🔍 Model Output: {probability:.2f}% fake probability")
        print(f"📊 Real: {real_prob:.1f}% | Fake: {fake_prob:.1f}%")
        
        # Determine final classification
        if fake_prob < 30:
            classification = "REAL"
            confidence = real_prob
        elif fake_prob < 70:
            classification = "UNCERTAIN" 
            confidence = max(fake_prob, real_prob)
        else:
            classification = "FAKE"
            confidence = fake_prob
            
        print(f"🎯 Final: {classification} ({confidence:.1f}% confidence)")
        
        # Update circular progress
        self.draw_circular_progress(probability)
        
        # Update analysis time
        self.metadata_items['analysis_time'].config(text=f"{analysis_time:.2f}s")
        
        # Update status with detailed info
        status_text = f"{self.texts['complete']} | Real: {real_prob:.1f}% | Fake: {fake_prob:.1f}%"
        self.status_label.config(text=status_text,
                               fg=self.colors['accent_success'])
        
        # Add to history
        self.add_to_history(probability)
        
        # Re-enable button
        self.analysis_btn.config(state='normal', bg=self.colors['accent_success'])
    
    def on_analysis_error(self, error_msg):
        """Xử lý lỗi phân tích"""
        self.status_label.config(text="Lỗi phân tích", fg=self.colors['accent_danger'])
        self.analysis_btn.config(state='normal', bg=self.colors['accent_success'])
        messagebox.showerror("Lỗi", f"Phân tích thất bại: {error_msg}")
    
    def add_to_history(self, probability):
        """Thêm vào lịch sử"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        filename = os.path.basename(self.current_image_path) if self.current_image_path else "Unknown"
        
        result = self.texts['fake'] if probability >= 70 else self.texts['uncertain'] if probability >= 30 else self.texts['real']
        color = self.colors['accent_danger'] if probability >= 70 else self.colors['accent_warning'] if probability >= 30 else self.colors['accent_success']
        
        # Clear placeholder if first item
        if not self.history:
            for widget in self.history_frame.winfo_children():
                widget.destroy()
        
        # Add history item
        history_item = tk.Frame(self.history_frame, bg=self.colors['bg_elevated'])
        history_item.pack(fill=tk.X, pady=2, padx=5)
        
        # Filename
        tk.Label(history_item,
                text=filename[:20] + "..." if len(filename) > 20 else filename,
                bg=self.colors['bg_elevated'],
                fg=self.colors['text_primary'],
                font=('Inter', 10, 'bold')).pack(anchor='w', padx=10, pady=(5, 0))
        
        # Result & time
        result_frame = tk.Frame(history_item, bg=self.colors['bg_elevated'])
        result_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        tk.Label(result_frame,
                text=result,
                bg=self.colors['bg_elevated'],
                fg=color,
                font=('Inter', 9, 'bold')).pack(side=tk.LEFT)
        
        tk.Label(result_frame,
                text=f"{probability:.1f}%",
                bg=self.colors['bg_elevated'],
                fg=self.colors['text_secondary'],
                font=('Inter', 9)).pack(side=tk.RIGHT)
        
        self.history.append({
            'time': timestamp,
            'file': filename,
            'result': result,
            'probability': probability
        })
        
        # Keep only last 10
        if len(self.history) > 10:
            self.history.pop(0)


def main():
    """Chạy ứng dụng Professional Dark Mode GUI"""
    root = tk.Tk()
    app = ProfessionalDarkGUI(root)
    
    # Handle window closing
    def on_closing():
        app.animation_running = False
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()