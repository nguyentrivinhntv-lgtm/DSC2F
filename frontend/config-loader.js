// ===== LOAD SITE CONFIG FROM API =====
(async function loadSiteConfig() {
    try {
        const API = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) ? 'http://localhost:8000' : 'https://cnn-detection-api.onrender.com';
        window.API_BASE_URL = API; // Export globally for other scripts
        const res = await fetch(`${API}/site-config`);
        if (!res.ok) return;
        const c = await res.json();
        window.siteConfig = c;

        // Apply colors
        const root = document.documentElement.style;
        if (c.color_primary) {
            root.setProperty('--primary', c.color_primary);
            root.setProperty('--glow-primary', c.color_primary + '40');
        }
        if (c.color_accent) {
            root.setProperty('--accent', c.color_accent);
            root.setProperty('--glow-accent', c.color_accent + '33');
        }
        if (c.color_primary && c.color_accent) {
            root.setProperty('--gradient', `linear-gradient(135deg, ${c.color_primary}, ${c.color_accent})`);
        }
        if (c.color_bg) {
            root.setProperty('--bg', c.color_bg);
        }
        if (c.color_bg2) {
            root.setProperty('--bg2', c.color_bg2);
        }
        if (c.color_bg3) {
            root.setProperty('--bg3', c.color_bg3);
        }
        if (c.color_bg || c.color_bg2 || c.color_bg3) {
            const bg1 = c.color_bg || '#f7f9fc';
            const bg2 = c.color_bg2 || '#eff3f9';
            const bg3 = c.color_bg3 || '#e2e8f0';
            document.body.style.background = `linear-gradient(180deg, ${bg1} 0%, ${bg2} 50%, ${bg3} 100%)`;
        }
        if (c.color_text) {
            root.setProperty('--text', c.color_text);
        }

        // Apply text content (Only works on Landing Page index.html)
        const applyTextConfig = () => {
            const isEn = typeof getLang === 'function' && getLang() === 'en';
            const setText = (id, val, valEn) => {
                const el = document.getElementById(id);
                if (!el) return;
                const finalVal = (isEn && valEn) ? valEn : val;
                if (finalVal) el.textContent = finalVal;
            };

            setText('lp-site-name', c.site_name, null); // No en for site name
            setText('lp-site-slogan', c.site_slogan, null);
            setText('lp-hero-line1', c.hero_title_line1, c.hero_title_line1_en);
            setText('lp-hero-line2', c.hero_title_line2, c.hero_title_line2_en);
            setText('lp-hero-cta', c.hero_cta_text, c.hero_cta_text_en);
            setText('lp-f1-title', c.feature1_title, c.feature1_title_en);
            setText('lp-f1-desc', c.feature1_desc, c.feature1_desc_en);
            setText('lp-f2-title', c.feature2_title, c.feature2_title_en);
            setText('lp-f2-desc', c.feature2_desc, c.feature2_desc_en);
            setText('lp-f3-title', c.feature3_title, c.feature3_title_en);
            setText('lp-f3-desc', c.feature3_desc, c.feature3_desc_en);
            setText('lp-s1-title', c.step1_title, c.step1_title_en);
            setText('lp-s1-desc', c.step1_desc, c.step1_desc_en);
            setText('lp-s2-title', c.step2_title, c.step2_title_en);
            setText('lp-s2-desc', c.step2_desc, c.step2_desc_en);
            setText('lp-s3-title', c.step3_title, c.step3_title_en);
            setText('lp-s3-desc', c.step3_desc, c.step3_desc_en);
            setText('lp-footer', c.footer_text, c.footer_text_en);

            const heroDescEl = document.getElementById('lp-hero-desc');
            if (heroDescEl) {
                const descVal = (isEn && c.hero_desc_en) ? c.hero_desc_en : c.hero_desc;
                if (descVal) heroDescEl.textContent = descVal;
            }
        };
        applyTextConfig();
        window.addEventListener('languageChanged', applyTextConfig);

        // Apply section visibility (Only works on Landing Page)
        const toggleSection = (id, val) => { const el = document.getElementById(id); if (el) el.style.display = val === '0' ? 'none' : ''; };
        toggleSection('section-stats', c.show_stats);
        toggleSection('section-marquee', c.show_marquee);
        toggleSection('features', c.show_features);
        toggleSection('section-howitworks', c.show_howitworks);
        toggleSection('section-cta', c.show_cta);

        // Apply logo (Works on all pages that have .brand-icon img)
        if (c.logo_url) {
            document.querySelectorAll('.brand-icon, .site-brand i, .sidebar-brand i').forEach(icon => {
                if(icon.tagName.toLowerCase() === 'i') {
                    // Replace icon with image
                    const parent = icon.parentElement;
                    const img = document.createElement('img');
                    img.src = c.logo_url;
                    img.style.width = '100%';
                    img.style.height = '100%';
                    img.style.maxHeight = '40px';
                    img.style.objectFit = 'contain';
                    img.style.borderRadius = 'inherit';
                    parent.insertBefore(img, icon);
                    icon.style.display = 'none';
                } else if(icon.classList.contains('brand-icon')) {
                    icon.innerHTML = `<img src="${c.logo_url}" alt="Logo" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;">`;
                }
            });
        }
    } catch (e) {
        console.log('Site config not available, using defaults.');
    }
})();
