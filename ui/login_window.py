"""Login window UI."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QIcon

from config.settings import WINDOW_TITLE, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from services.auth_service import auth_service
from utils.logger import app_logger
from models import LoginResponse


class LoginWorker(QThread):
    """Worker thread for login to prevent UI freezing."""
    
    finished = Signal(bool, object, str)  # success, response, error
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
    
    def run(self):
        """Execute login in background."""
        success, response, error = auth_service.login(self.username, self.password)
        self.finished.emit(success, response, error or "")


class LoginWindow(QWidget):
    """Login window for authentication."""
    
    login_successful = Signal(LoginResponse)
    
    def __init__(self):
        super().__init__()
        self.login_worker = None
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle(f"{WINDOW_TITLE} - Login")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title_label = QLabel("Thor Desktop Agent")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Ingresa tus credenciales")
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666;")
        layout.addWidget(subtitle_label)
        
        layout.addSpacing(20)
        
        # Username field
        username_label = QLabel("Usuario (Email):")
        username_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("usuario@ejemplo.com")
        self.username_input.setMinimumHeight(35)
        self.username_input.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(self.username_input)
        
        # Password field
        password_label = QLabel("Contraseña:")
        password_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Ingresa tu contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(35)
        self.password_input.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(self.password_input)
        
        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Recordar credenciales")
        layout.addWidget(self.remember_checkbox)
        
        layout.addSpacing(10)
        
        # Login button
        self.login_button = QPushButton("Iniciar Sesión")
        self.login_button.setMinimumHeight(40)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.login_button.clicked.connect(self._on_login_clicked)
        layout.addWidget(self.login_button)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Spacer
        layout.addStretch()
        
        # Info label
        info_label = QLabel("Thor Desktop Agent v1.0")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
        
        # Center window
        self._center_window()
        
        # Focus on username
        self.username_input.setFocus()
    
    def _center_window(self):
        """Center window on screen."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
    
    def _on_login_clicked(self):
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        # Validate inputs
        if not username:
            self._show_error("Por favor ingresa tu usuario")
            self.username_input.setFocus()
            return
        
        if not password:
            self._show_error("Por favor ingresa tu contraseña")
            self.password_input.setFocus()
            return
        
        # Disable UI during login
        self._set_loading(True)
        self._show_status("Iniciando sesión...", "info")
        
        # Start login in background thread
        self.login_worker = LoginWorker(username, password)
        self.login_worker.finished.connect(self._on_login_finished)
        self.login_worker.start()
    
    def _on_login_finished(self, success: bool, response: LoginResponse, error: str):
        """Handle login completion.
        
        Args:
            success: Whether login was successful
            response: Login response object
            error: Error message if failed
        """
        self._set_loading(False)
        
        if success:
            app_logger.info(f"Login successful for: {response.user.email}")
            self._show_status(f"¡Bienvenido, {response.user.full_name}!", "success")
            
            # Emit signal to notify main application
            self.login_successful.emit(response)
            
            # Close login window
            self.close()
        else:
            app_logger.error(f"Login failed: {error}")
            self._show_error(error)
    
    def _set_loading(self, loading: bool):
        """Set UI loading state.
        
        Args:
            loading: Whether to show loading state
        """
        self.username_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self.remember_checkbox.setEnabled(not loading)
        self.login_button.setEnabled(not loading)
        
        if loading:
            self.login_button.setText("Cargando...")
        else:
            self.login_button.setText("Iniciar Sesión")
    
    def _show_status(self, message: str, status_type: str = "info"):
        """Show status message.
        
        Args:
            message: Status message
            status_type: Type of status (info, success, error)
        """
        colors = {
            'info': '#2196F3',
            'success': '#4CAF50',
            'error': '#F44336'
        }
        
        color = colors.get(status_type, colors['info'])
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def _show_error(self, message: str):
        """Show error message.
        
        Args:
            message: Error message
        """
        self._show_status(message, "error")
        
        # Also show dialog for critical errors
        if "connect" in message.lower() or "timeout" in message.lower():
            QMessageBox.critical(
                self,
                "Error de Conexión",
                f"{message}\n\nVerifica tu conexión a internet y que el servidor esté disponible.",
                QMessageBox.StandardButton.Ok
            )
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Cancel login if in progress
        if self.login_worker and self.login_worker.isRunning():
            self.login_worker.terminate()
            self.login_worker.wait()
        
        event.accept()
