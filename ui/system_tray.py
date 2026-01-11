"""System tray icon and menu."""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal

from config.settings import WINDOW_TITLE
from utils.logger import app_logger


class SystemTray(QObject):
    """System tray icon manager."""
    
    show_requested = Signal()
    logout_requested = Signal()
    quit_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = None
        self.user_email = None
        self._init_tray()
    
    def _init_tray(self):
        """Initialize system tray icon."""
        # Create tray icon (using default icon for now)
        self.tray_icon = QSystemTrayIcon(parent=self.parent())
        
        # Set icon (you can replace with custom icon)
        # For now using default Qt icon
        from PySide6.QtWidgets import QApplication, QStyle
        icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        
        # Set tooltip
        self.tray_icon.setToolTip(WINDOW_TITLE)
        
        # Create context menu
        self._create_menu()
        
        # Connect signals
        self.tray_icon.activated.connect(self._on_activated)
        
        app_logger.info("System tray initialized")
    
    def _create_menu(self):
        """Create context menu for tray icon."""
        menu = QMenu()
        
        # User info action (disabled, just for display)
        self.user_action = QAction("No autenticado", menu)
        self.user_action.setEnabled(False)
        menu.addAction(self.user_action)
        
        menu.addSeparator()
        
        # Show window action
        show_action = QAction("Mostrar", menu)
        show_action.triggered.connect(self.show_requested.emit)
        menu.addAction(show_action)
        
        # Logout action
        self.logout_action = QAction("Cerrar Sesión", menu)
        self.logout_action.triggered.connect(self.logout_requested.emit)
        self.logout_action.setEnabled(False)
        menu.addAction(self.logout_action)
        
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Salir", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
    
    def _on_activated(self, reason):
        """Handle tray icon activation.
        
        Args:
            reason: Activation reason
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()
    
    def show(self):
        """Show tray icon."""
        if self.tray_icon:
            self.tray_icon.show()
            app_logger.debug("System tray shown")
    
    def hide(self):
        """Hide tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
            app_logger.debug("System tray hidden")
    
    def set_user(self, email: str):
        """Update tray menu with user info.
        
        Args:
            email: User email
        """
        self.user_email = email
        if self.user_action:
            self.user_action.setText(f"Usuario: {email}")
        if self.logout_action:
            self.logout_action.setEnabled(True)
        
        app_logger.debug(f"Tray updated for user: {email}")
    
    def clear_user(self):
        """Clear user info from tray menu."""
        self.user_email = None
        if self.user_action:
            self.user_action.setText("No autenticado")
        if self.logout_action:
            self.logout_action.setEnabled(False)
        
        app_logger.debug("Tray user info cleared")
    
    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.MessageIcon.Information):
        """Show notification message.
        
        Args:
            title: Notification title
            message: Notification message
            icon: Notification icon
        """
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon, 3000)
