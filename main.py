"""Thor Desktop Agent - Main application entry point."""
import sys
import signal
import asyncio
from qasync import QEventLoop
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PySide6.QtCore import Qt

from config.settings import WINDOW_TITLE, APP_VERSION, DEV_MODE
from ui.login_window import LoginWindow
from ui.system_tray import SystemTray
from services.auth_service import auth_service
from services.websocket_manager import WebSocketManager
from utils.logger import app_logger
from utils.keyring_manager import keyring_manager
from models import LoginResponse


class ThorDesktopAgent:
    """Main application controller."""
    
    def __init__(self):
        self.app = None
        self.loop = None
        self.login_window = None
        self.system_tray = None
        self.ws_manager = None
        self.current_user = None
        
    def run(self):
        """Run the application."""
        # Create QApplication
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(WINDOW_TITLE)
        self.app.setApplicationVersion(APP_VERSION)
        
        # Don't quit when last window closes (we have system tray)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Setup async event loop for Qt
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        # Setup signal handlers for Ctrl+C
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Enable high DPI support (skip deprecated warning)
        # self.app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        
        app_logger.info(f"Starting {WINDOW_TITLE} v{APP_VERSION}")
        
        # Development mode: Clear all credentials on startup
        if DEV_MODE:
            app_logger.warning("🔧 DEV_MODE enabled: Clearing all saved credentials")
            keyring_manager.clear_all()
            app_logger.info("✅ Credentials cleared, fresh start required")
        
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager()
        self._setup_ws_handlers()
        
        # Initialize system tray
        self._init_system_tray()
        
        # Check if already logged in
        if auth_service.is_logged_in():
            app_logger.info("User already logged in, validating session...")
            
            # Try to refresh token to validate session
            success, _, error = auth_service.refresh_token()
            
            if success:
                # User is authenticated, show tray only
                email = auth_service.get_current_user_email()
                self._on_login_success_existing(email)
            else:
                # Session invalid, show login
                app_logger.warning(f"Session validation failed: {error}")
                self._show_login()
        else:
            # Not logged in, show login window
            self._show_login()
        
        # Run application with async loop
        with self.loop:
            exit_code = self.loop.run_forever()
        
        app_logger.info("Application shutting down")
        return exit_code
    
    def _setup_ws_handlers(self):
        """Setup WebSocket event handlers."""
        self.ws_manager.connected.connect(self._on_ws_connected)
        self.ws_manager.disconnected.connect(self._on_ws_disconnected)
        self.ws_manager.checkin_received.connect(self._on_checkin)
        self.ws_manager.verify_access_received.connect(self._on_verify_access)
    
    def _on_ws_connected(self):
        """Handle WebSocket connection."""
        app_logger.info("✅ Connected to Heimdall WebSocket")
        self.system_tray.show_message(
            "Heimdall Conectado",
            "Conexión establecida con el servidor de eventos"
        )
    
    def _on_ws_disconnected(self):
        """Handle WebSocket disconnection."""
        app_logger.warning("⚠️ Disconnected from Heimdall")
    
    def _on_checkin(self, data: dict):
        """Handle check-in event.
        
        Args:
            data: Check-in data
        """
        member_name = data.get('member_name', 'Unknown')
        app_logger.info(f"🏋️ Check-in: {member_name}")
        
        # Show notification
        self.system_tray.show_message(
            "Check-in Detectado",
            f"{member_name} ingresó al gimnasio"
        )
    
    def _on_verify_access(self, data: dict):
        """Handle verify access request.
        
        Args:
            data: Verify access request data
        """
        member_name = data.get('member_name', 'Unknown')
        app_logger.info(f"🔍 Verificación de acceso solicitada: {member_name}")
        
        # Show notification
        self.system_tray.show_message(
            "Verificación de Acceso",
            f"Verificando acceso de {member_name}..."
        )
    
    def _init_system_tray(self):
        """Initialize system tray icon."""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            app_logger.warning("System tray not available on this system")
            QMessageBox.critical(
                None,
                "Error",
                "No se puede detectar la bandeja del sistema.\n"
                "La aplicación no puede ejecutarse en segundo plano.",
            )
            sys.exit(1)
        
        # Create system tray
        self.system_tray = SystemTray()
        self.system_tray.show_requested.connect(self._on_show_requested)
        self.system_tray.logout_requested.connect(self._on_logout_requested)
        self.system_tray.quit_requested.connect(self._on_quit_requested)
        
        # Show tray
        self.system_tray.show()
    
    def _show_login(self):
        """Show login window."""
        if self.login_window is None:
            self.login_window = LoginWindow()
            self.login_window.login_successful.connect(self._on_login_success)
        
        self.login_window.show()
        self.login_window.raise_()
        self.login_window.activateWindow()
    
    def _on_login_success(self, response: LoginResponse):
        """Handle successful login.
        
        Args:
            response: Login response with user data
        """
        self.current_user = response.user
        
        app_logger.info(f"Login successful for user: {self.current_user.email}")
        
        # Update system tray
        self.system_tray.set_user(self.current_user.email)
        
        # Connect to Heimdall WebSocket
        app_logger.info("Connecting to Heimdall WebSocket...")
        self.ws_manager.connect()
        
        # Show notification
        self.system_tray.show_message(
            "Autenticación Exitosa",
            f"¡Bienvenido, {self.current_user.full_name}!\n"
            f"Conectando a servidor de eventos..."
        )
        
        # Close login window
        if self.login_window:
            self.login_window.close()
    
    def _on_login_success_existing(self, email: str):
        """Handle existing session validation.
        
        Args:
            email: User email from keyring
        """
        app_logger.info(f"Restored session for user: {email}")
        
        # Update system tray
        self.system_tray.set_user(email)
        
        # Connect to Heimdall WebSocket
        app_logger.info("Connecting to Heimdall WebSocket...")
        self.ws_manager.connect()
        
        # Show notification
        self.system_tray.show_message(
            "Sesión Restaurada",
            f"Bienvenido de nuevo.\nConectando a servidor de eventos..."
        )
    
    def _on_show_requested(self):
        """Handle show window request from tray."""
        app_logger.debug("Show window requested from tray")
        
        # For now, just show a message
        # In the future, this could show a main window
        QMessageBox.information(
            None,
            WINDOW_TITLE,
            f"Usuario: {auth_service.get_current_user_email() or 'No autenticado'}\n\n"
            "La aplicación está ejecutándose en segundo plano.\n"
            "Usa el menú del icono para gestionar la sesión."
        )
    
    def _on_logout_requested(self):
        """Handle logout request from tray."""
        app_logger.info("Logout requested from tray")
        
        # Confirm logout
        reply = QMessageBox.question(
            None,
            "Cerrar Sesión",
            "¿Estás seguro de que deseas cerrar sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Logout
            success, error = auth_service.logout()
            
            if success:
                app_logger.info("Logout successful")
                
                # Disconnect WebSocket
                if self.ws_manager:
                    self.ws_manager.disconnect()
                
                # Update tray
                self.system_tray.clear_user()
                
                # Show notification
                self.system_tray.show_message(
                    "Sesión Cerrada",
                    "Has cerrado sesión correctamente."
                )
                
                # Show login window again
                self._show_login()
            else:
                app_logger.error(f"Logout failed: {error}")
                QMessageBox.warning(
                    None,
                    "Error",
                    f"No se pudo cerrar sesión correctamente: {error}"
                )
    
    def _on_quit_requested(self):
        """Handle quit request from tray."""
        app_logger.info("Quit requested from tray")
        
        # Confirm quit
        reply = QMessageBox.question(
            None,
            "Salir",
            "¿Estás seguro de que deseas salir de la aplicación?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Quit application
            self._quit()
    
    def _quit(self):
        """Quit application."""
        app_logger.info("Quitting application")
        
        # Disconnect WebSocket
        if self.ws_manager:
            self.ws_manager.disconnect()
        
        # Hide tray
        if self.system_tray:
            self.system_tray.hide()
        
        # Close all windows
        if self.login_window:
            self.login_window.close()
        
        # Quit
        self.loop.stop()
    
    def _signal_handler(self, signum, frame):
        """Handle Unix signals (Ctrl+C)."""
        signal_name = signal.Signals(signum).name
        app_logger.warning(f"\n⚠️  Received {signal_name}, shutting down gracefully...")
        
        # Call quit from main thread
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._quit)
        else:
            sys.exit(0)


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
