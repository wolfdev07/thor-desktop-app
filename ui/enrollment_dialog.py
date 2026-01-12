"""Fingerprint Enrollment Dialog - Simulates 4-touch biometric enrollment."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from utils.logger import app_logger


class EnrollmentDialog(QDialog):
    """
    Dialog to simulate fingerprint enrollment with 4-touch process.
    
    Simulates ZKTeco fingerprint scanner behavior:
    - User must press "Verdadero" 4 times (successful scans)
    - Each press sends progress to Heimdall
    - After 4 successful touches → saves to local DB
    - "Falso" simulates failed scan (doesn't count toward 4)
    """
    
    # Signals
    touch_registered = Signal(bool)  # True = Verdadero, False = Falso
    enrollment_completed = Signal(str)  # Emits enrollment_token when done
    enrollment_cancelled = Signal()
    
    def __init__(self, member_number: str, member_name: str, request_id: str, parent=None):
        super().__init__(parent)
        
        self.member_number = member_number
        self.member_name = member_name
        self.request_id = request_id
        self.touch_count = 0
        self.successful_touches = 0
        
        self._setup_ui()
        self._connect_signals()
        
        app_logger.info(
            f"📱 Enrollment dialog opened | Member: {member_number} ({member_name}) | "
            f"Request: {request_id}"
        )
    
    def _setup_ui(self):
        """Setup UI components."""
        self.setWindowTitle("Registro de Huella Digital")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("🖐️ Registro de Huella Digital")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Member info
        member_info = QLabel(f"Socio: {self.member_name}\nNúmero: {self.member_number}")
        member_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        member_font = QFont()
        member_font.setPointSize(12)
        member_info.setFont(member_font)
        member_info.setStyleSheet("color: #555; padding: 10px;")
        layout.addWidget(member_info)
        
        # Instructions
        self.instructions = QLabel(
            "Simula el escaneo de huella presionando el botón VERDADERO 4 veces.\n"
            "Presiona FALSO para simular un escaneo fallido."
        )
        self.instructions.setWordWrap(True)
        self.instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instructions.setStyleSheet("padding: 15px; background-color: #f0f0f0; border-radius: 8px;")
        layout.addWidget(self.instructions)
        
        # Progress label
        self.progress_label = QLabel("Escaneos exitosos: 0 / 4")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_font = QFont()
        progress_font.setPointSize(14)
        progress_font.setBold(True)
        self.progress_label.setFont(progress_font)
        self.progress_label.setStyleSheet("color: #2196F3; padding: 10px;")
        layout.addWidget(self.progress_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(4)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m escaneos")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 8px;
                text-align: center;
                height: 30px;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Spacer
        layout.addStretch()
        
        # Buttons container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(15)
        
        # Falso button (simulates failed scan)
        self.falso_btn = QPushButton("❌ FALSO")
        self.falso_btn.setMinimumHeight(60)
        self.falso_btn.setMinimumWidth(150)
        falso_font = QFont()
        falso_font.setPointSize(14)
        falso_font.setBold(True)
        self.falso_btn.setFont(falso_font)
        self.falso_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #a01208;
            }
        """)
        button_layout.addWidget(self.falso_btn)
        
        # Verdadero button (simulates successful scan)
        self.verdadero_btn = QPushButton("✅ VERDADERO")
        self.verdadero_btn.setMinimumHeight(60)
        self.verdadero_btn.setMinimumWidth(150)
        verdadero_font = QFont()
        verdadero_font.setPointSize(14)
        verdadero_font.setBold(True)
        self.verdadero_btn.setFont(verdadero_font)
        self.verdadero_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #367c39;
            }
        """)
        button_layout.addWidget(self.verdadero_btn)
        
        layout.addWidget(button_container)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect button signals."""
        self.verdadero_btn.clicked.connect(self._on_verdadero_clicked)
        self.falso_btn.clicked.connect(self._on_falso_clicked)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
    
    def _on_verdadero_clicked(self):
        """Handle successful touch (Verdadero button)."""
        self.touch_count += 1
        self.successful_touches += 1
        
        app_logger.info(
            f"👆 Touch {self.touch_count} - SUCCESS ✅ | "
            f"Member: {self.member_number} | "
            f"Progress: {self.successful_touches}/4"
        )
        
        # Update UI
        self.progress_bar.setValue(self.successful_touches)
        self.progress_label.setText(f"Escaneos exitosos: {self.successful_touches} / 4")
        
        # Update instructions
        if self.successful_touches < 4:
            remaining = 4 - self.successful_touches
            self.instructions.setText(
                f"✅ Escaneo {self.successful_touches} registrado correctamente.\n"
                f"Faltan {remaining} escaneo{'s' if remaining > 1 else ''} más..."
            )
            self.instructions.setStyleSheet(
                "padding: 15px; background-color: #e8f5e9; "
                "border-radius: 8px; color: #2e7d32;"
            )
        else:
            self.instructions.setText(
                "🎉 ¡Registro completado exitosamente!\n"
                "La huella ha sido registrada."
            )
            self.instructions.setStyleSheet(
                "padding: 15px; background-color: #c8e6c9; "
                "border-radius: 8px; color: #1b5e20; font-weight: bold;"
            )
            
            # Disable buttons
            self.verdadero_btn.setEnabled(False)
            self.falso_btn.setEnabled(False)
        
        # Emit signal
        self.touch_registered.emit(True)
        
        # Check if enrollment complete
        if self.successful_touches >= 4:
            self._complete_enrollment()
    
    def _on_falso_clicked(self):
        """Handle failed touch (Falso button)."""
        self.touch_count += 1
        
        app_logger.warning(
            f"👆 Touch {self.touch_count} - FAILED ❌ | "
            f"Member: {self.member_number} | "
            f"Progress: {self.successful_touches}/4"
        )
        
        # Update instructions (visual feedback only)
        self.instructions.setText(
            "❌ Escaneo fallido. Por favor, intenta de nuevo.\n"
            f"Progreso actual: {self.successful_touches} / 4"
        )
        self.instructions.setStyleSheet(
            "padding: 15px; background-color: #ffebee; "
            "border-radius: 8px; color: #c62828;"
        )
        
        # Emit signal
        self.touch_registered.emit(False)
    
    def _complete_enrollment(self):
        """Complete enrollment after 4 successful touches."""
        import uuid
        
        # Generate enrollment token
        enrollment_token = str(uuid.uuid4())
        
        app_logger.info(
            f"🎉 Enrollment completed | Member: {self.member_number} | "
            f"Token: {enrollment_token[:8]}... | Touches: {self.successful_touches}/4"
        )
        
        # Emit completion signal
        self.enrollment_completed.emit(enrollment_token)
        
        # Close dialog after a short delay
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, self.accept)  # Close after 2 seconds
    
    def _on_cancel_clicked(self):
        """Handle cancellation."""
        app_logger.warning(
            f"❌ Enrollment cancelled | Member: {self.member_number} | "
            f"Progress: {self.successful_touches}/4"
        )
        
        self.enrollment_cancelled.emit()
        self.reject()
    
    def update_progress_from_server(self, touch_number: int, success: bool):
        """
        Update progress based on server response.
        Called when Heimdall confirms touch was received.
        
        Args:
            touch_number: Touch number confirmed by server
            success: Whether touch was successful
        """
        app_logger.debug(
            f"📥 Server confirmed touch {touch_number} | "
            f"Success: {success} | Member: {self.member_number}"
        )
        
        # Could add visual feedback here (e.g., checkmark animation)
