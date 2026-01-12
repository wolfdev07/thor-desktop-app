"""Fingerprint enrollment dialog for ZKTeco simulation."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from utils.logger import app_logger


class FingerprintEnrollDialog(QDialog):
    """Dialog for fingerprint enrollment simulation."""
    
    # Signals
    enrollment_response = Signal(bool)  # True = success touch, False = failed touch
    enrollment_completed = Signal(str)  # membership_number when complete
    enrollment_cancelled = Signal()
    
    def __init__(self, membership_number: str, parent=None):
        super().__init__(parent)
        self.membership_number = membership_number
        self.touch_count = 0
        self.required_touches = 4
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Registro de Huella Digital")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMinimumHeight(300)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("🔐 Registro de Huella Digital")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Member info
        member_label = QLabel(f"Socio: {self.membership_number}")
        member_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        member_font = QFont()
        member_font.setPointSize(12)
        member_label.setFont(member_font)
        layout.addWidget(member_label)
        
        # Instructions
        self.instruction_label = QLabel(
            "Por favor, coloque su dedo en el sensor\n"
            "Simule la lectura presionando 'Verdadero'"
        )
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.required_touches)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(f"Lecturas: 0/{self.required_touches}")
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Spacer
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.false_button = QPushButton("❌ Falso")
        self.false_button.setMinimumHeight(50)
        self.false_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.false_button.clicked.connect(self._on_false_clicked)
        
        self.true_button = QPushButton("✅ Verdadero")
        self.true_button.setMinimumHeight(50)
        self.true_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.true_button.clicked.connect(self._on_true_clicked)
        
        button_layout.addWidget(self.false_button)
        button_layout.addWidget(self.true_button)
        
        layout.addLayout(button_layout)
        
        # Cancel button
        cancel_button = QPushButton("Cancelar")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #7f8c8d;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
        """)
        cancel_button.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(cancel_button)
        
        self.setLayout(layout)
        
        app_logger.info(f"Fingerprint enrollment dialog opened for member: {self.membership_number}")
    
    def _on_true_clicked(self):
        """Handle true button click (successful fingerprint read)."""
        self.touch_count += 1
        
        app_logger.info(f"✅ Touch {self.touch_count}/{self.required_touches} recorded")
        
        # Update progress
        self.progress_bar.setValue(self.touch_count)
        self.progress_bar.setFormat(f"Lecturas: {self.touch_count}/{self.required_touches}")
        
        # Update status
        if self.touch_count < self.required_touches:
            self.status_label.setText(f"✅ Lectura exitosa. Levante y vuelva a colocar el dedo.")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.status_label.setText("🎉 ¡Registro completado exitosamente!")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 14px; font-weight: bold;")
            
            # Disable buttons
            self.true_button.setEnabled(False)
            self.false_button.setEnabled(False)
        
        # Emit response signal
        self.enrollment_response.emit(True)
        
        # Check if completed
        if self.touch_count >= self.required_touches:
            app_logger.info(f"🎉 Enrollment completed for member: {self.membership_number}")
            self.enrollment_completed.emit(self.membership_number)
            
            # Close dialog after 2 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self.accept)
    
    def _on_false_clicked(self):
        """Handle false button click (failed fingerprint read)."""
        app_logger.warning(f"❌ Failed fingerprint read attempt")
        
        # Update status
        self.status_label.setText("❌ Lectura fallida. Intente de nuevo.")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        # Emit response signal
        self.enrollment_response.emit(False)
        
        # Don't increment counter on failed reads
    
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        app_logger.info("Enrollment cancelled by user")
        self.enrollment_cancelled.emit()
        self.reject()
    
    def update_server_response(self, success: bool, message: str = ""):
        """Update UI based on server response.
        
        Args:
            success: Whether server accepted the touch
            message: Optional message from server
        """
        if success:
            app_logger.debug(f"Server confirmed touch {self.touch_count}")
        else:
            app_logger.warning(f"Server rejected touch: {message}")
            self.status_label.setText(f"⚠️ Servidor: {message}")
            self.status_label.setStyleSheet("color: #e67e22; font-weight: bold;")
