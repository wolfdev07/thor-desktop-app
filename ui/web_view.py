"""
Main WebView Window

Qt WebEngine-based browser window that loads the Django application.
Provides native-like experience with full hardware access via QWebChannel bridge.
"""

from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from utils.logger import app_logger
from config.settings import DEV_MODE


class CustomWebPage(QWebEnginePage):
    """Custom web page to handle console messages, navigation, and permissions."""
    
    def __init__(self, parent=None):
        """Initialize custom web page."""
        super().__init__(parent)
        
        # Connect feature permission signal
        self.featurePermissionRequested.connect(self._on_feature_permission_requested)
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """Forward JavaScript console messages to Python logger."""
        level_map = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARNING",
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR"
        }
        
        log_level = level_map.get(level, "INFO")
        app_logger.debug(f"🌐 [JS-{log_level}] {message} (Line: {lineNumber})")
    
    @Slot(QUrl, 'QWebEnginePage::Feature')
    def _on_feature_permission_requested(self, origin: QUrl, feature):
        """Handle permission requests for hardware features (camera, microphone, etc.).
        
        Args:
            origin: URL requesting the permission
            feature: Feature being requested (camera, microphone, geolocation, etc.)
        """
        # Feature types from QWebEnginePage.Feature enum
        feature_names = {
            QWebEnginePage.Feature.MediaAudioCapture: "🎤 Microphone",
            QWebEnginePage.Feature.MediaVideoCapture: "📷 Camera",
            QWebEnginePage.Feature.MediaAudioVideoCapture: "🎥 Camera + Microphone",
            QWebEnginePage.Feature.Geolocation: "📍 Geolocation",
            QWebEnginePage.Feature.DesktopVideoCapture: "🖥️  Desktop Capture",
            QWebEnginePage.Feature.DesktopAudioVideoCapture: "🖥️  Desktop Capture + Audio",
        }
        
        feature_name = feature_names.get(feature, f"Unknown Feature ({feature})")
        
        # Auto-grant permissions for media capture (camera/microphone)
        if feature in [
            QWebEnginePage.Feature.MediaAudioCapture,
            QWebEnginePage.Feature.MediaVideoCapture,
            QWebEnginePage.Feature.MediaAudioVideoCapture,
        ]:
            app_logger.info(f"✅ Granting permission: {feature_name} for {origin.toString()}")
            self.setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
        elif feature == QWebEnginePage.Feature.Geolocation:
            # Grant geolocation if in dev mode
            if DEV_MODE:
                app_logger.info(f"✅ Granting permission: {feature_name} (DEV_MODE)")
                self.setFeaturePermission(
                    origin,
                    feature,
                    QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
                )
            else:
                app_logger.warning(f"❌ Denying permission: {feature_name} (Production)")
                self.setFeaturePermission(
                    origin,
                    feature,
                    QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
                )
        else:
            # Deny other permissions by default
            app_logger.warning(f"❌ Denying permission: {feature_name}")
            self.setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
            )


class MainWebView(QMainWindow):
    """
    Main application window with embedded Chromium browser.
    
    Features:
    - Loads Django app (localhost:8000 in dev, production URL in prod)
    - QWebChannel bridge for JavaScript ↔ Python communication
    - Hardware access (fingerprint scanner) from web pages
    - Configurable security settings (F12, right-click, navigation)
    """
    
    def __init__(self, base_url: str, hardware_bridge=None, parent=None):
        """
        Initialize web view window.
        
        Args:
            base_url: URL to load (e.g., "http://localhost:8000")
            hardware_bridge: HardwareBridge instance for QWebChannel
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.base_url = base_url
        self.hardware_bridge = hardware_bridge
        
        self._init_ui()
        self._setup_webengine()
        self._setup_bridge()
        self._load_app()
    
    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Thor Desktop Agent")
        self.resize(1280, 720)
        
        # Create web view
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)
        
        # Use custom page for console logging
        self.custom_page = CustomWebPage(self.web_view)
        self.web_view.setPage(self.custom_page)
        
        app_logger.info("🖥️  WebView window initialized")
    
    def _setup_webengine(self):
        """Configure WebEngine settings."""
        settings = self.web_view.settings()
        
        # Enable required features
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, DEV_MODE)
        
        # Development vs Production settings
        if DEV_MODE:
            # Development: Enable DevTools, allow insecure content
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
            app_logger.info("🔧 WebEngine in DEV mode - DevTools enabled")
        else:
            # Production: Disable DevTools, context menu, etc.
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
            self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            app_logger.info("🔒 WebEngine in PROD mode - Security hardened")
        
        # Enable WebChannel for Python ↔ JavaScript bridge
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
    
    def _setup_bridge(self):
        """Setup QWebChannel bridge for hardware access."""
        if not self.hardware_bridge:
            app_logger.warning("⚠️  No hardware bridge provided - hardware features disabled")
            return
        
        # Create and register channel
        self.channel = QWebChannel()
        self.channel.registerObject("backend", self.hardware_bridge)
        
        # Attach channel to page
        self.custom_page.setWebChannel(self.channel)
        
        app_logger.info("🌉 QWebChannel bridge registered - JavaScript can access 'backend' object")
    
    def _load_app(self):
        """Load the Django application."""
        url = QUrl(self.base_url)
        
        app_logger.info(f"🌍 Loading Django app: {self.base_url}")
        self.web_view.setUrl(url)
        
        # Connect signals
        self.web_view.loadStarted.connect(self._on_load_started)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.loadProgress.connect(self._on_load_progress)
    
    @Slot()
    def _on_load_started(self):
        """Handle page load start."""
        app_logger.debug("🔄 Page loading started...")
    
    @Slot(bool)
    def _on_load_finished(self, success: bool):
        """Handle page load completion."""
        if success:
            app_logger.info("✅ Page loaded successfully")
            self._inject_qwebchannel_script()
        else:
            app_logger.error("❌ Page load failed")
    
    @Slot(int)
    def _on_load_progress(self, progress: int):
        """Handle page load progress."""
        if progress % 25 == 0:  # Log every 25%
            app_logger.debug(f"📊 Loading progress: {progress}%")
    
    def _inject_qwebchannel_script(self):
        """Initialize QWebChannel bridge (script already loaded by Django base.html)."""
        init_script = """
        (function() {
            // Verify QWebChannel is loaded (from Django's base.html)
            if (typeof QWebChannel !== 'function') {
                console.error('[Thor] ❌ QWebChannel not loaded - ensure base.html has qrc:///qtwebchannel/qwebchannel.js');
                return;
            }
            
            // Verify qt transport is available
            if (typeof qt === 'undefined' || !qt.webChannelTransport) {
                console.warn('[Thor] ⚠️ qt.webChannelTransport not available - running outside Thor');
                return;
            }
            
            console.log('[Thor] 🔌 Initializing bridge...');
            
            // Initialize QWebChannel
            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.thorBridge = channel.objects.backend;
                
                console.log('[Thor] ✅ Bridge connected');
                console.log('[Thor] 📱 Device ID:', window.thorBridge.device_id);
                console.log('[Thor] 📦 Version:', window.thorBridge.version);
                
                // Dispatch thor-ready event on BOTH window and document
                var eventDetail = {
                    detail: { 
                        bridge: window.thorBridge,
                        deviceId: window.thorBridge.device_id,
                        version: window.thorBridge.version
                    },
                    bubbles: true,
                    cancelable: false
                };
                
                var windowEvent = new CustomEvent('thor-ready', eventDetail);
                var documentEvent = new CustomEvent('thor-ready', eventDetail);
                
                window.dispatchEvent(windowEvent);
                document.dispatchEvent(documentEvent);
                
                console.log('[Thor] 📡 thor-ready event dispatched');
            });
        })();
        """
        
        self.custom_page.runJavaScript(init_script)
        app_logger.debug("🔌 QWebChannel initialization executed")
    
    def navigate_to(self, path: str):
        """
        Navigate to a specific path within the Django app.
        
        Args:
            path: Relative path (e.g., "/enrollment")
        """
        url = f"{self.base_url}{path}"
        app_logger.info(f"🧭 Navigating to: {url}")
        self.web_view.setUrl(QUrl(url))
    
    def reload(self):
        """Reload current page."""
        app_logger.info("🔄 Reloading page...")
        self.web_view.reload()
    
    def go_home(self):
        """Navigate to base URL."""
        self.navigate_to("/")
    
    def execute_javascript(self, script: str):
        """
        Execute JavaScript code in the page context.
        
        Args:
            script: JavaScript code to execute
        """
        self.custom_page.runJavaScript(script)
    
    def closeEvent(self, event):
        """Handle window close event."""
        app_logger.info("🔴 WebView window closing...")
        event.accept()
