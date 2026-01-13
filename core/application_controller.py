"""Application Controller - Manages Qt application lifecycle and initialization."""
import signal
import asyncio
from typing import Optional

from qasync import QEventLoop
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox
from PySide6.QtCore import Qt

from config.settings import WINDOW_TITLE, APP_VERSION, DEV_MODE
from utils.logger import app_logger
from utils.keyring_manager import keyring_manager


class ApplicationController:
    """Manages Qt application initialization and lifecycle."""
    
    def __init__(self):
        """Initialize application controller."""
        self.app: Optional[QApplication] = None
        self.loop: Optional[QEventLoop] = None
        self._quit_callback = None
        
    def initialize(self) -> tuple[QApplication, QEventLoop]:
        """Initialize Qt application and async event loop.
        
        Returns:
            Tuple of (QApplication, QEventLoop)
        """
        # Create QApplication
        self.app = QApplication([])
        self.app.setApplicationName(WINDOW_TITLE)
        self.app.setApplicationVersion(APP_VERSION)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Setup async event loop for Qt
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        app_logger.info(f"Starting {WINDOW_TITLE} v{APP_VERSION}")
        
        # Development mode: Clear credentials on startup
        if DEV_MODE:
            self._clear_dev_credentials()
        
        return self.app, self.loop
    
    def setup_signal_handlers(self, quit_callback):
        """Setup Unix signal handlers for graceful shutdown.
        
        Args:
            quit_callback: Function to call when signal is received
        """
        self._quit_callback = quit_callback
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        app_logger.debug("Signal handlers configured")
    
    def check_system_tray_support(self) -> bool:
        """Check if system tray is available.
        
        Returns:
            True if system tray is supported, False otherwise
        """
        if not QSystemTrayIcon.isSystemTrayAvailable():
            app_logger.error("System tray not available on this system")
            QMessageBox.critical(
                None,
                "Error",
                "No se puede detectar la bandeja del sistema.\n"
                "La aplicación no puede ejecutarse en segundo plano.",
            )
            return False
        return True
    
    def run_event_loop(self) -> int:
        """Run Qt event loop.
        
        Returns:
            Exit code
        """
        with self.loop:
            return self.loop.run_forever()
    
    def stop_event_loop(self):
        """Stop Qt event loop."""
        if self.loop and self.loop.is_running():
            self.loop.stop()
            app_logger.info("Event loop stopped")
    
    def _clear_dev_credentials(self):
        """Clear all credentials in development mode."""
        app_logger.warning("🔧 DEV_MODE enabled: Clearing all saved credentials")
        keyring_manager.clear_all()
        app_logger.info("✅ Credentials cleared, fresh start required")
    
    def _signal_handler(self, signum, frame):
        """Handle Unix signals (Ctrl+C).
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        app_logger.warning(f"\n⚠️  Received {signal_name}, shutting down gracefully...")
        
        if self._quit_callback and self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._quit_callback)
