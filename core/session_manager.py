"""Session Manager - Handles user authentication and session lifecycle."""
from typing import Optional, Callable

from PySide6.QtWidgets import QMessageBox

from services.auth_service import auth_service
from services.websocket_manager import WebSocketManager
from ui.system_tray import SystemTray
from utils.logger import app_logger


class SessionManager:
    """Manages user session, authentication, and WebSocket connectivity."""
    
    def __init__(self, ws_manager: WebSocketManager, system_tray: SystemTray):
        """Initialize session manager.
        
        Args:
            ws_manager: WebSocket manager for Heimdall connection
            system_tray: System tray for user status updates
        """
        self.ws_manager = ws_manager
        self.system_tray = system_tray
        self.current_user_email: Optional[str] = None
    
    def restore_existing_session(self) -> bool:
        """Restore existing session if valid.
        
        Returns:
            True if session was restored successfully, False otherwise
        """
        if not auth_service.is_logged_in():
            app_logger.info("No saved session - user will authenticate via Django")
            return False
        
        app_logger.info("User already logged in, validating session...")
        
        # Validate session by refreshing token
        success, _, error = auth_service.refresh_token()
        
        if not success:
            app_logger.warning(f"Session validation failed: {error}")
            app_logger.info("User will authenticate via Django login page")
            return False
        
        # Session is valid
        email = auth_service.get_current_user_email()
        self.current_user_email = email
        
        app_logger.info(f"✅ Session valid for: {email}")
        
        # Update system tray
        self.system_tray.set_user(email)
        
        # Auto-connect to Heimdall
        self._connect_to_heimdall()
        
        return True
    
    def logout(self, on_success: Optional[Callable] = None) -> bool:
        """Logout current user.
        
        Args:
            on_success: Optional callback to execute on successful logout
            
        Returns:
            True if logout was successful, False otherwise
        """
        # Perform logout
        success, error = auth_service.logout()
        
        if not success:
            app_logger.error(f"Logout failed: {error}")
            QMessageBox.warning(
                None,
                "Error",
                f"No se pudo cerrar sesión correctamente: {error}"
            )
            return False
        
        app_logger.info("Logout successful")
        
        # Disconnect from Heimdall
        self.ws_manager.disconnect()
        
        # Clear user from tray
        self.system_tray.clear_user()
        self.current_user_email = None
        
        # Show notification
        self.system_tray.show_message(
            "Sesión Cerrada",
            "Has cerrado sesión correctamente."
        )
        
        # Execute success callback
        if on_success:
            on_success()
        
        return True
    
    def _connect_to_heimdall(self):
        """Connect to Heimdall WebSocket server."""
        app_logger.info("Auto-connecting to Heimdall WebSocket...")
        self.ws_manager.connect()
    
    def confirm_logout(self) -> bool:
        """Show confirmation dialog for logout.
        
        Returns:
            True if user confirmed logout, False otherwise
        """
        reply = QMessageBox.question(
            None,
            "Cerrar Sesión",
            "¿Estás seguro de que deseas cerrar sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def confirm_quit(self) -> bool:
        """Show confirmation dialog for quitting application.
        
        Returns:
            True if user confirmed quit, False otherwise
        """
        reply = QMessageBox.question(
            None,
            "Salir",
            "¿Estás seguro de que deseas salir de la aplicación?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
