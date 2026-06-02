// ============================================================
// ⚙️ FILE CẤU HÌNH FLUTTER APP
// ⚠️ Thêm file này vào .gitignore nếu chứa thông tin nhạy cảm
// ============================================================

class AppConfig {
  // ── BASE URLs ──────────────────────────────────────────────
  /// URL backend FastAPI (không có dấu / ở cuối)
  static const String apiBaseUrl = 'https://cnn-detection-api.onrender.com';

  /// URL frontend web
  static const String webBaseUrl = 'https://dsc-2-f.vercel.app';

  // ── APP INFO ───────────────────────────────────────────────
  static const String appName = 'CNN Detection';
  static const String appVersion = '1.0.0';
}
