// ============================================================
// ⚙️ FILE CẤU HÌNH FLUTTER APP
// ⚠️ Thêm file này vào .gitignore nếu chứa thông tin nhạy cảm
// ============================================================

class AppConfig {
  // ── BASE URLs ──────────────────────────────────────────────
  /// URL backend FastAPI (không có dấu / ở cuối)
  static const String apiBaseUrl = 'https://cnn-detection-api.onrender.com';

  /// URL frontend web
  static const String webBaseUrl = 'https://cnn-detection-api.onrender.com/frontend/';

  // ── OAUTH DEEP LINK ────────────────────────────────────────
  /// Scheme cho Deep Link callback sau Google OAuth
  /// Phải khớp với android:scheme trong AndroidManifest.xml
  static const String callbackScheme = 'phatgiaochatbot';

  // ── APP INFO ───────────────────────────────────────────────
  static const String appName = 'CNN Detection';
  static const String appVersion = '1.0.0';

  // ── COMPUTED ───────────────────────────────────────────────
  /// URL endpoint đăng nhập Google dành cho Flutter
  static String get googleLoginFlutterUrl =>
      '$apiBaseUrl/auth/google/login/flutter?callback_scheme=$callbackScheme';
}
