"""Thor Desktop Agent - Main application entry point.

Clean architecture main orchestrator using:
- ApplicationController: Qt lifecycle and signals
- SessionManager: Authentication and session
- WebSocketEventHandler: Heimdall event delegation
- WebViewManager: Django WebView integration
"""
import sys

from ui.system_tray import SystemTray
from services.websocket_manager import WebSocketManager
from core.application_controller import ApplicationController
from core.session_manager import SessionManager
from core.websocket_event_handler import WebSocketEventHandler
from core.webview_manager import WebViewManager
from utils.logger import app_logger


class ThorDesktopAgent:
    """Main application orchestrator - delegates to specialized managers."""
    
    def __init__(self):
        """Initialize Thor Desktop Agent."""
        # Core controllers
        self.app_controller = ApplicationController()
        
        # Services and UI (initialized in run())
        self.system_tray = None
        self.ws_manager = None
        self.session_manager = None
        self.ws_event_handler = None
        self.webview_manager = None
        
    def run(self) -> int:
        """Run the Thor Desktop Agent application.
        
        Returns:
            Exit code
        """
        # Initialize Qt application and event loop
        app, loop = self.app_controller.initialize()
        
        # Setup signal handlers for graceful shutdown
        self.app_controller.setup_signal_handlers(self._quit)
        
        # Check system tray support
        if not self.app_controller.check_system_tray_support():
            return 1
        
        # Initialize components
        self._initialize_components()
        
        # Show WebView with Django app
        app_logger.info("🌐 Starting in WebView mode - Django handles authentication")
        self.webview_manager.show_webview()
        
        # Restore existing session if available
        self.session_manager.restore_existing_session()
        
        # Run event loop
        exit_code = self.app_controller.run_event_loop()
        
        app_logger.info("Application shutting down")
        return exit_code
    
    def _initialize_components(self):
        """Initialize all application components."""
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager()
        
        # Initialize system tray
        self.system_tray = SystemTray()
        self.system_tray.show_requested.connect(self._on_show_requested)
        self.system_tray.logout_requested.connect(self._on_logout_requested)
        self.system_tray.quit_requested.connect(self._on_quit_requested)
        self.system_tray.show()
        
        # Initialize session manager
        self.session_manager = SessionManager(self.ws_manager, self.system_tray)
        
        # Initialize WebSocket event handler
        self.ws_event_handler = WebSocketEventHandler(self.ws_manager, self.system_tray)
        self.ws_event_handler.on_fingerprint_enroll = self._on_fingerprint_enroll
        
        # Initialize WebView manager
        self.webview_manager = WebViewManager(self.ws_manager, self.system_tray)
        
        app_logger.debug("All components initialized")
    
    def _on_fingerprint_enroll(self, enrollment_data: dict):
        """Handle fingerprint enrollment request.
        
        Args:
            enrollment_data: Enrollment data from Heimdall
        """
        self.webview_manager.handle_enrollment_request(enrollment_data)
    
    def _on_show_requested(self):
        """Handle show window request from system tray."""
        app_logger.debug("Show window requested from tray")
        self.webview_manager.show_webview()
    
    def _on_logout_requested(self):
        """Handle logout request from system tray."""
        app_logger.info("Logout requested from tray")
        
        # Confirm with user
        if not self.session_manager.confirm_logout():
            return
        
        # Trigger Django logout
        self.webview_manager.trigger_django_logout()
        
        # Perform local logout
        self.session_manager.logout(
            on_success=self.webview_manager.reload_to_login
        )
    
    def _on_quit_requested(self):
        """Handle quit request from system tray."""
        app_logger.info("Quit requested from tray")
        
        # Confirm with user
        if self.session_manager.confirm_quit():
            self._quit()
    
    def _quit(self):
        """Quit application gracefully."""
        app_logger.info("Quitting application")
        
        # Disconnect WebSocket
        if self.ws_manager:
            self.ws_manager.disconnect()
        
        # Hide system tray
        if self.system_tray:
            self.system_tray.hide()
        
        # Close WebView
        if self.webview_manager:
            self.webview_manager.close()
        
        # Stop event loop
        self.app_controller.stop_event_loop()


def main():
    """Main entry point."""
    try:
        agent = ThorDesktopAgent()
        sys.exit(agent.run())
    except Exception as e:
        app_logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
