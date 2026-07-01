import 'dart:io';
import 'dart:math';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:http/http.dart' as http;
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'config.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ),
  );

  final prefs = await SharedPreferences.getInstance();
  final token = prefs.getString('access_token');

  runApp(PhatGiaoApp(initialToken: token));
}

class PhatGiaoApp extends StatelessWidget {
  final String? initialToken;
  
  static final List<Color> _brandColors = [
    const Color(0xFFB7791F),
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

  void _initWebView() async {
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setUserAgent("Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36")
      ..setBackgroundColor(const Color(0xFFFCFAF7))
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (progress) => setState(() => _loadingProgress = progress / 100),
          onPageStarted: (_) => setState(() { _isLoading = true; _hasError = false; }),
          onPageFinished: (_) {
            setState(() => _isLoading = false);
            if (_activeToken != null) {
              _controller.runJavaScript('''
                window.dispatchEvent(new CustomEvent('flutter_token_ready', { detail: { token: '$_activeToken' } }));
              ''');
            }
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

    // ✅ Bật hỗ trợ chọn file (ảnh) trên Android WebView
    if (Platform.isAndroid) {
      final androidController = _controller.platform as AndroidWebViewController;
      await androidController.setOnShowFileSelector(_androidFilePicker);
    }

    _setupAppCookie();
    _loadAppUrl(_activeToken);
  }

  /// Xử lý chọn file trên Android khi WebView gọi <input type="file">
  Future<List<String>> _androidFilePicker(FileSelectorParams params) async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.image,
        allowMultiple: params.mode == FileSelectorMode.openMultiple,
      );

      if (result != null && result.files.isNotEmpty) {
        final filePaths = result.files
            .where((file) => file.path != null)
            .map((file) => Uri.file(file.path!).toString())
            .toList();
        debugPrint('==> File picked: $filePaths');
        return filePaths;
      }
      return [];
    } catch (e) {
      debugPrint('==> File picker error: $e');
      return [];
    }
  }

  Future<void> _setupAppCookie() async {
    final domain = Uri.parse(AppConfig.webBaseUrl).host;
    await WebViewCookieManager().setCookie(
      WebViewCookie(name: 'viewappmobie', value: 'true', domain: domain, path: '/'),
    );
  }

  /// Load trang web chính
  void _loadAppUrl(String? token) {
    final url = token != null 
        ? '${AppConfig.webBaseUrl}/app.html'
        : AppConfig.webBaseUrl;
    _controller.loadRequest(Uri.parse(url));
  }

  NavigationDecision _handleNavigation(NavigationRequest request) {
    final url = request.url;
    final uri = Uri.tryParse(url);

    if (url.startsWith(AppConfig.webBaseUrl)) {
      return NavigationDecision.navigate;
    }

    if (uri != null) {
      final host = uri.host;
      if (host.contains('google.com') || host.contains('googleusercontent.com') || host.contains('gstatic.com') || host.contains('googleapis.com')) {
        return NavigationDecision.navigate;
      }
      for (final domain in _allowedDomains) {
        if (host == domain || host.endsWith('.$domain')) {
          return NavigationDecision.navigate;
        }
      }
    }

    if (url.startsWith('https://accounts.google.com') ||
        url.startsWith('https://dsc-2-f.vercel.app')) {
      return NavigationDecision.navigate;
    }
    
    _launchExternalUrl(url);
    return NavigationDecision.prevent;
  }

  Future<void> _launchExternalUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  /// Xử lý thông điệp từ JavaScript qua FlutterBridge
  void _handleWebMessage(JavaScriptMessage message) async {
    final data = message.message;
    debugPrint('==> Bridge received: $data');
    
    if (data == 'LOGOUT') {
      _processLogout();
    } else if (data.startsWith('GOOGLE_LOGIN:')) {
      // ✅ LUỒNG CLOUD-SYNC MỚI
      final sessionId = data.split(':')[1];
      _startCloudSyncGoogleLogin(sessionId);
    } else if (data == 'LOGIN_GOOGLE') {
      // (Fallback) Luồng cũ
      _startGoogleLogin();
    } else if (data.startsWith('TOKEN:')) {
      final token = data.substring(6);
      if (token.isNotEmpty) {
        debugPrint('==> 🎉 Login thành công, lưu token');
        await _saveToken(token);
      }
    } else if (data.startsWith('OPEN_URL:')) {
      // Mở URL bên ngoài (VNPay payment, etc.)
      final url = data.substring('OPEN_URL:'.length);
      debugPrint('==> Mở URL bên ngoài: $url');
      _launchExternalUrl(url);
    } else if (data.startsWith('DOWNLOAD_CSV:')) {
      // Xử lý tải file CSV từ WebView
      final csvData = data.substring('DOWNLOAD_CSV:'.length);
      await _saveCSVFile(csvData);
    }
  }

  /// Lưu file CSV xuống bộ nhớ thiết bị
  Future<void> _saveCSVFile(String csvData) async {
    try {
      // Parse JSON: {"filename": "...", "content": "..."}
      final parsed = jsonDecode(csvData);
      final filename = parsed['filename'] ?? 'export.csv';
      final content = parsed['content'] ?? '';

      // Lấy thư mục Downloads
      Directory? dir;
      if (Platform.isAndroid) {
        dir = Directory('/storage/emulated/0/Download');
        if (!await dir.exists()) {
          dir = await getExternalStorageDirectory();
        }
      } else {
        dir = await getApplicationDocumentsDirectory();
      }

      if (dir == null) {
        debugPrint('==> Không tìm được thư mục lưu file');
        return;
      }

      final file = File('${dir.path}/$filename');
      await file.writeAsString(content);
      debugPrint('==> ✅ CSV saved: ${file.path}');

      // Thông báo cho WebView biết đã lưu thành công
      _controller.runJavaScript('''
        if (typeof window.__onCSVSaved === 'function') {
          window.__onCSVSaved('${file.path}');
        } else {
          alert('Đã lưu file: ${file.path}');
        }
      ''');
    } catch (e) {
      debugPrint('==> Lỗi lưu CSV: $e');
      _controller.runJavaScript("alert('Lỗi lưu file CSV: $e');");
    }
  }

  /// Mở luồng Cloud-Sync mới (Hybrid Polling)
  Future<void> _startCloudSyncGoogleLogin(String sessionId) async {
    try {
      final url = '${AppConfig.apiBaseUrl}/auth/google/login/flutter?session_id=$sessionId';
      debugPrint('==> Mở Chrome Custom Tabs (Cloud Sync): $url');
      
      // App chỉ mở Tab. Chờ user đăng nhập xong web tự tắt hoặc user tự tắt.
      // Dùng callbackUrlScheme = none để app không cần bắt deep link,
      // việc lưu token sẽ do Frontend Web lo phần Polling ngầm.
      await FlutterWebAuth2.authenticate(
        url: url,
        callbackUrlScheme: 'none',
      );
    } catch (e) {
      debugPrint('==> Đã đóng Tab hoặc lỗi CCT: $e');
    }
  }

  /// Mở mobile_login.html trong Chrome Custom Tabs để đăng nhập Google (Cũ)
  Future<void> _startGoogleLogin() async {
    try {
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final url = '${AppConfig.webBaseUrl}/mobile_login.html?t=$timestamp';
      
      debugPrint('==> Mở Chrome Custom Tabs: $url');
      
      final result = await FlutterWebAuth2.authenticate(
        url: url,
        callbackUrlScheme: 'cnndetection',
      );
      
      debugPrint('==> Callback URL nhận được: $result');
      
      final callbackUri = Uri.parse(result);
      final token = callbackUri.queryParameters['token'];
      
      if (token != null && token.isNotEmpty) {
        debugPrint('==> 🎉 Google login thành công qua CCT, nhận token');
        await _saveToken(token);
        
        // Gửi token sang cho app.js xử lý bằng event
        await _controller.runJavaScript('''
          window.dispatchEvent(new CustomEvent('flutter_token_ready', { detail: { token: '$token' } }));
        ''');
      }
    } catch (e) {
      debugPrint('==> Google Login bị hủy hoặc lỗi: $e');
    }
  }

  Future<void> _processLogout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    
    await WebViewCookieManager().clearCookies();
    await _setupAppCookie();

    setState(() {
      _activeToken = null;
    });
    _loadAppUrl(null);
  }

  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
    setState(() => _activeToken = token);
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
// ERROR VIEW
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
            Icon(Icons.cloud_off_rounded, size: 80, color: colorScheme.primary.withOpacity(0.6)),
            const SizedBox(height: 24),
            Text('Mất kết nối Internet', style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold, color: colorScheme.onSurface)),
            const SizedBox(height: 12),
            Text('Không thể tải nội dung. Vui lòng kiểm tra lại đường truyền và thử lại.', textAlign: TextAlign.center, style: theme.textTheme.bodyMedium?.copyWith(color: colorScheme.onSurfaceVariant)),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Thử lại'),
              style: ElevatedButton.styleFrom(
                backgroundColor: colorScheme.primary,
                foregroundColor: colorScheme.onPrimary,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 15),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                elevation: 0,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
