"""Thor Desktop Agent - Main application entry point."""
import sys
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PySide6.QtCore import Qt

from config.settings import WINDOW_TITLE, APP_VERSION
from ui.login_window import LoginWindow
from ui.system_tray import SystemTray
from services.auth_service import auth_service
from utils.logger import app_logger
from models import LoginResponse


class ThorDesktopAgent:
    """Main application controller."""
    
    def __init__(self):
        self.app = None
        self.login_window = None
        self.system_tray = None
        self.current_user = None
        
    def run(self):
        """Run the application."""
        # Create QApplication
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(WINDOW_TITLE)
        self.app.setApplicationVersion(APP_VERSION)
        
        # Enable high DPI support
        self.app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        
        app_logger.info(f"Starting {WINDOW_TITLE} v{APP_VERSION}")
        
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
        
        # Run application
        exit_code = self.app.exec()
        
        app_logger.info("Application shutting down")
        return exit_code
    
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
        
        # Show notification
        self.system_tray.show_message(
            "Autenticación Exitosa",
            f"¡Bienvenido, {self.current_user.full_name}!\n"
            f"La aplicación seguirá ejecutándose en segundo plano."
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
        
        # Show notification
        self.system_tray.show_message(
            "Sesión Restaurada",
            f"Bienvenido de nuevo.\nLa aplicación está ejecutándose en segundo plano."
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
        
        # Hide tray
        if self.system_tray:
            self.system_tray.hide()
        
        # Close all windows
        if self.login_window:
            self.login_window.close()
        
        # Quit
        self.app.quit()


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
