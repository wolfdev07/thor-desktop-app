"""WebView Manager - Manages WebView, Hardware Bridge, and Django integration."""
import json
from typing import Optional

from PySide6.QtWidgets import QSystemTrayIcon

from config.settings import DJANGO_WEB_URL
from ui.web_view import MainWebView
from bridge.hardware_bridge import HardwareBridge
from services.websocket_manager import WebSocketManager
from utils.logger import app_logger


class WebViewManager:
    """Manages WebView window, hardware bridge, and Django app integration."""
    
    def __init__(self, ws_manager: WebSocketManager, system_tray: QSystemTrayIcon):
        """Initialize WebView manager.
        
        Args:
            ws_manager: WebSocket manager for hardware bridge communication
            system_tray: System tray for notifications
        """
        self.ws_manager = ws_manager
        self.system_tray = system_tray
        
        self.web_view: Optional[MainWebView] = None
        self.hardware_bridge: Optional[HardwareBridge] = None
        
        self._initialize_hardware_bridge()
    
    def _initialize_hardware_bridge(self):
        """Initialize hardware bridge for fingerprint operations."""
        self.hardware_bridge = HardwareBridge(ws_manager=self.ws_manager)
        
        # Connect bridge notifications to system tray
        self.hardware_bridge.notification.connect(
            lambda title, msg: self.system_tray.show_message(title, msg)
        )
        
        app_logger.info("🌉 Hardware bridge initialized")
    
    def create_webview(self) -> MainWebView:
        """Create WebView window if not already created.
        
        Returns:
            MainWebView instance
        """
        if not self.web_view:
            self.web_view = MainWebView(
                base_url=DJANGO_WEB_URL,
                hardware_bridge=self.hardware_bridge
            )
            app_logger.info(f"🌍 WebView created - Loading: {DJANGO_WEB_URL}")
        
        return self.web_view
    
    def show_webview(self):
        """Show and focus WebView window."""
        if not self.web_view:
            self.create_webview()
        
        self.web_view.show()
        self.web_view.raise_()
        self.web_view.activateWindow()
        
        app_logger.info("🖥️  WebView window shown")
    
    def handle_enrollment_request(self, enrollment_data: dict):
        """Handle fingerprint enrollment request.
        
        Forwards enrollment request to Django app via JavaScript and
        initializes hardware bridge for the enrollment process.
        
        Args:
            enrollment_data: Enrollment data from Heimdall
        """
        request_id = enrollment_data.get('request_id')
        member_number = enrollment_data.get('member_number')
        member_name = enrollment_data.get('member_name', 'Unknown')
        
        # Forward event to Django app via JavaScript
        if self.web_view:
            self._inject_enrollment_event(enrollment_data)
        else:
            app_logger.warning("WebView not initialized - cannot forward enrollment request")
        
        # Initialize hardware bridge for this enrollment
        if self.hardware_bridge:
            self.hardware_bridge.iniciar_enrollment(
                request_id, member_number, member_name
            )
    
    def _inject_enrollment_event(self, enrollment_data: dict):
        """Inject enrollment event into Django app via JavaScript.
        
        Args:
            enrollment_data: Enrollment data to send to Django
        """
        enrollment_json = json.dumps(enrollment_data)
        
        js_code = f"""
        if (typeof window.onThorEnrollmentRequest === 'function') {{
            window.onThorEnrollmentRequest({enrollment_json});
        }} else {{
            console.warn('⚠️ Django app not ready - onThorEnrollmentRequest not defined');
        }}
        """
        
        self.web_view.execute_javascript(js_code)
        app_logger.debug("📤 Enrollment request forwarded to Django via JavaScript")
    
    def trigger_django_logout(self):
        """Trigger logout in Django app via JavaScript."""
        if not self.web_view:
            app_logger.warning("WebView not initialized - cannot trigger logout")
            return
        
        js_code = """
        if (typeof window.thorLogout === 'function') {
            window.thorLogout();
        } else {
            // Fallback: navigate to logout URL
            window.location.href = '/valhalla/api/v1/auth/logout';
        }
        """
        
        self.web_view.execute_javascript(js_code)
        app_logger.info("🔓 Logout request sent to Django via JavaScript")
    
    def reload_to_login(self):
        """Reload WebView to show login page."""
        if self.web_view:
            self.web_view.go_home()
            app_logger.debug("WebView reloaded to login page")
    
    def close(self):
        """Close WebView window."""
        if self.web_view:
            self.web_view.close()
            app_logger.debug("WebView closed")
