import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'config.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Thiết lập giao diện hệ thống (Status Bar)
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ),
  );

  // Lấy token đã lưu (nếu có)
  final prefs = await SharedPreferences.getInstance();
  final token = prefs.getString('access_token');

  runApp(PhatGiaoApp(initialToken: token));
}

class PhatGiaoApp extends StatelessWidget {
  final String? initialToken;
  
  static final List<Color> _brandColors = [
    const Color(0xFFB7791F), // Vàng Phật Giáo
    const Color(0xFF1565C0), 
    const Color(0xFF2E7D32),
    const Color(0xFFC62828), 
    const Color(0xFF6A1B9A),
    const Color(0xFF37474F),
  ];

  PhatGiaoApp({super.key, this.initialToken});

  final Color _primaryColor = _brandColors[Random().nextInt(_brandColors.length)];

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConfig.appName,
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: _primaryColor),
        useMaterial3: true,
      ),
      home: WebViewScreen(token: initialToken),
    );
  }
}

// ============================================================
// MAIN WEBVIEW SCREEN
// ============================================================
class WebViewScreen extends StatefulWidget {
  final String? token;
  const WebViewScreen({super.key, required this.token});

  @override
  State<WebViewScreen> createState() => _WebViewScreenState();
}

class _WebViewScreenState extends State<WebViewScreen> {
  late final WebViewController _controller;
  bool _isLoading = true;
  bool _hasError = false;
  double _loadingProgress = 0;
  String? _activeToken;

  /// Danh sách domain được phép điều hướng trong WebView
  static const _allowedDomains = [
    'accounts.google.com',
    'accounts.youtube.com',
    'ssl.gstatic.com',
    'www.gstatic.com',
    'lh3.googleusercontent.com',
    'fonts.googleapis.com',
    'fonts.gstatic.com',
    'cdnjs.cloudflare.com',
    'cdn.jsdelivr.net',
  ];

  @override
  void initState() {
    super.initState();
    _activeToken = widget.token;
    _initWebView();
  }

  // --- WebView Initialization ---

  void _initWebView() {
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFFFCFAF7))
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (progress) => setState(() => _loadingProgress = progress / 100),
          onPageStarted: (_) => setState(() { _isLoading = true; _hasError = false; }),
          onPageFinished: (_) {
            setState(() => _isLoading = false);
            if (_activeToken != null) _injectTokenToWeb(_activeToken!);
          },
          onWebResourceError: (error) {
            debugPrint('WebView Error: ${error.description}');
            if (error.isForMainFrame ?? true) {
              setState(() { _isLoading = false; _hasError = true; });
            }
          },
          onNavigationRequest: _handleNavigation,
        ),
      )
      ..addJavaScriptChannel('FlutterBridge', onMessageReceived: _handleWebMessage);

    _setupAppCookie();
    _loadAppUrl(_activeToken);
  }

  // --- Helper Methods ---

  /// Thiết lập cookie định danh để Web nhận biết môi trường App
  Future<void> _setupAppCookie() async {
    final domain = Uri.parse(AppConfig.webBaseUrl).host;
    await WebViewCookieManager().setCookie(
      WebViewCookie(name: 'viewappmobie', value: 'true', domain: domain, path: '/'),
    );
  }

  /// Load trang web chính với token (nếu có)
  void _loadAppUrl(String? token) {
    final url = token != null 
        ? '${AppConfig.webBaseUrl}?token=$token' 
        : AppConfig.webBaseUrl;
    _controller.loadRequest(Uri.parse(url));
  }

  /// Cho phép điều hướng đến các domain cần thiết (web app + Google OAuth)
  NavigationDecision _handleNavigation(NavigationRequest request) {
    final url = request.url;
    final uri = Uri.tryParse(url);

    // ✅ Cho phép URL của web app
    if (url.startsWith(AppConfig.webBaseUrl)) {
      return NavigationDecision.navigate;
    }

    // ✅ Cho phép Google OAuth và các resource cần thiết
    if (uri != null) {
      final host = uri.host;
      for (final domain in _allowedDomains) {
        if (host == domain || host.endsWith('.$domain')) {
          return NavigationDecision.navigate;
        }
      }
    }

    // ✅ Cho phép các URL chứa callback hoặc token
    if (url.contains('callback') || url.contains('token=')) {
      return NavigationDecision.navigate;
    }

    debugPrint('==> Đã chặn điều hướng ngoài: ${request.url}');
    return NavigationDecision.prevent;
  }

  /// Xử lý các thông điệp gửi từ JavaScript qua FlutterBridge
  void _handleWebMessage(JavaScriptMessage message) async {
    final data = message.message;
    debugPrint('==> Bridge received: $data');
    
    if (data == 'LOGOUT') {
      _processLogout();
    } else if (data.startsWith('TOKEN:')) {
      // Web đã đăng nhập Google thành công, lưu token
      final token = data.substring(6); // Bỏ prefix 'TOKEN:'
      if (token.isNotEmpty) {
        debugPrint('==> 🎉 Google login thành công, lưu token');
        await _saveToken(token);
      }
    }
  }

  // --- Core Logic ---

  Future<void> _processLogout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    
    await WebViewCookieManager().clearCookies();
    await _setupAppCookie(); // Re-set mobile identifier after clear

    setState(() => _activeToken = null);
    _loadAppUrl(null);
  }

  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
    setState(() => _activeToken = token);
  }

  Future<void> _injectTokenToWeb(String token) async {
    await _controller.runJavaScript('''
      try {
        localStorage.setItem('access_token', '$token');
        window.dispatchEvent(new CustomEvent('flutter_token_ready', { detail: { token: '$token' } }));
        console.log('[Flutter] Token injected');
      } catch(e) {}
    ''');
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (await _controller.canGoBack()) {
          _controller.goBack();
        } else if (context.mounted) {
           SystemNavigator.pop();
        }
      },
      child: Scaffold(
        backgroundColor: const Color(0xFFFCFAF7),
        body: Stack(
          children: [
            if (!_hasError) WebViewWidget(controller: _controller) else _ErrorView(onRetry: () => _controller.reload()),
            if (_isLoading && !_hasError) _buildProgressBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressBar() {
    return Positioned(
      top: 0, left: 0, right: 0,
      child: LinearProgressIndicator(
        value: _loadingProgress,
        backgroundColor: Colors.transparent,
        color: const Color(0xFFB7791F),
        minHeight: 3,
      ),
    );
  }
}

// ============================================================
// ERROR VIEW - Hiển thị khi mất kết nối
// ============================================================
class _ErrorView extends StatelessWidget {
  final VoidCallback onRetry;
  const _ErrorView({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.cloud_off_rounded,
              size: 80,
              color: colorScheme.primary.withOpacity(0.6),
            ),
            const SizedBox(height: 24),
            Text(
              'Mất kết nối Internet',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Không thể tải nội dung. Vui lòng kiểm tra lại đường truyền và thử lại.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Thử lại'),
              style: ElevatedButton.styleFrom(
                backgroundColor: colorScheme.primary,
                foregroundColor: colorScheme.onPrimary,
                padding: const EdgeInsets.symmetric(
                    horizontal: 32, vertical: 15),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                elevation: 0,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
