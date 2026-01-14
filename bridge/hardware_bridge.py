"""
Hardware Bridge for QWebChannel

This bridge exposes Python methods to JavaScript running in QWebEngineView.
Allows the Django web app to access local hardware (fingerprint scanner, etc.)
without requiring a separate WebSocket server.

Usage in JavaScript:
    new QWebChannel(qt.webChannelTransport, function(channel) {
        var backend = channel.objects.backend;
        backend.capturar_huella(function(result) {
            console.log("Fingerprint captured:", result);
        });
    });
"""

import asyncio
import uuid
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from utils.logger import app_logger
from core.database import database, FingerprintEnrollment
from utils.keyring_manager import keyring_manager
from config.constants import KEY_DEVICE_ID
from bridge.zkteco_reader import get_reader

class HardwareBridge(QObject):
    """
    Bridge between JavaScript (Django web app) and Python (local hardware).
    
    All methods decorated with @Slot are callable from JavaScript.
    All signals can be listened to from JavaScript.
    """
    
    # Signals - JavaScript can subscribe to these events
    enrollment_progress = Signal(str, int, bool)  # (member_number, touch_count, success)
    enrollment_completed = Signal(str, str)  # (member_number, token)
    enrollment_cancelled = Signal(str)  # (member_number)
    fingerprint_verified = Signal(str, bool)  # (member_number, verified)
    notification = Signal(str, str)  # (title, message)
    touch_captured = Signal(int, bool, int)  # (touch_number, success, remaining)
    
    def __init__(self, ws_manager=None):
        """
        Initialize hardware bridge.
        
        Args:
            ws_manager: Optional WebSocketManager for Heimdall communication
        """
        super().__init__()
        self.ws_manager = ws_manager
        self._current_enrollment = None  # Stores active enrollment data
        self._touch_dialog = None  # Modal for touch capture (legacy)
        self._touch_count = 0  # Current successful touches
        self._touch_required = 4  # Required successful touches
        
        # ZKTeco fingerprint reader
        self._reader = get_reader()
        self._enrollment_in_progress = False
        
        # Cache immutable properties at init to make them constant for Qt
        from config.constants import APP_VERSION
        self._device_id = keyring_manager.get(KEY_DEVICE_ID) or str(uuid.uuid4())
        self._version = APP_VERSION
        
        app_logger.info("🌉 Hardware Bridge initialized")
        
        # Try to connect to fingerprint reader on startup
        QTimer.singleShot(1000, self._connect_fingerprint_reader)
    
    # ==================== PROPERTIES ====================
    
    @Property(str, constant=True)
    def device_id(self) -> str:
        """Get device ID (read-only constant property for JS)."""
        return self._device_id
    
    @Property(str, constant=True)
    def version(self) -> str:
        """Get application version (read-only constant property for JS)."""
        return self._version
    
    # ==================== FINGERPRINT ENROLLMENT ====================
    
    @Slot(str, str, str, result=bool)
    def iniciar_enrollment(self, request_id: str, member_number: str, member_name: str) -> bool:
        """
        Start fingerprint enrollment process.
        
        Args:
            request_id: Unique enrollment request ID
            member_number: Member's membership number
            member_name: Member's display name
            
        Returns:
            True if enrollment started, False if already in progress
            
        JavaScript usage:
            backend.iniciar_enrollment(req_id, member_num, name, function(started) {
                if (started) console.log("Enrollment started");
            });
        """
        if self._current_enrollment is not None:
            app_logger.warning(
                f"⚠️ Enrollment already in progress for member: "
                f"{self._current_enrollment.get('member_number')}"
            )
            return False
        
        self._current_enrollment = {
            'request_id': request_id,
            'member_number': member_number,
            'member_name': member_name,
            'touch_count': 0,
            'successful_touches': 0,
            'gym_id': 1  # TODO: Get from token
        }
        
        app_logger.info(
            f"🔐 Enrollment started | Request: {request_id} | "
            f"Member: {member_number} ({member_name})"
        )
        
        # Emit notification to JavaScript
        self.notification.emit(
            "Registro de Huella",
            f"Iniciando registro para {member_name}"
        )
        
        return True
    
    @Slot(bool, result=str)
    def registrar_toque(self, success: bool) -> str:
        """
        Register a fingerprint touch (simulated for now, real ZKTeco SDK later).
        
        Args:
            success: Whether the touch was successful (Verdadero/Falso simulation)
            
        Returns:
            JSON string with result: {"status": "progress|complete|error", "touch_count": N, "successful": N}
            
        JavaScript usage:
            backend.registrar_toque(true, function(result) {
                var data = JSON.parse(result);
                console.log("Touch registered:", data.touch_count);
            });
        """
        import json
        
        if self._current_enrollment is None:
            return json.dumps({
                'status': 'error',
                'message': 'No active enrollment'
            })
        
        enrollment = self._current_enrollment
        enrollment['touch_count'] += 1
        
        if success:
            enrollment['successful_touches'] += 1
        
        touch_num = enrollment['touch_count']
        successful = enrollment['successful_touches']
        member_number = enrollment['member_number']
        
        app_logger.info(
            f"{'✅' if success else '❌'} Touch {touch_num} - "
            f"{'SUCCESS' if success else 'FAILED'} | "
            f"Member: {member_number} | Progress: {successful}/4"
        )
        
        # Send progress to Heimdall if WebSocket is connected
        if self.ws_manager:
            self.ws_manager.send_enrollment_progress(
                request_id=enrollment['request_id'],
                member_number=member_number,
                touch_number=touch_num,
                success=success,
                gym_id=enrollment['gym_id']
            )
        
        # Emit signal to JavaScript
        self.enrollment_progress.emit(member_number, successful, success)
        
        # Check if enrollment complete (4 successful touches)
        if successful >= 4:
            return self._complete_enrollment()
        
        return json.dumps({
            'status': 'progress',
            'touch_count': touch_num,
            'successful_touches': successful,
            'remaining': 4 - successful
        })
    
    def _complete_enrollment(self) -> str:
        """Complete enrollment and save to database."""
        import json
        
        enrollment = self._current_enrollment
        member_number = enrollment['member_number']
        
        # Generate enrollment token
        enrollment_token = str(uuid.uuid4())
        
        # Save to database
        try:
            session = database.get_session()
            
            fingerprint = FingerprintEnrollment()
            fingerprint.membership_number = member_number
            fingerprint.enrollment_token = enrollment_token
            fingerprint.touch_count = 4
            
            session.add(fingerprint)
            session.commit()
            session.close()
            
            app_logger.info(
                f"🎉 Enrollment completed | Member: {member_number} | "
                f"Token: {enrollment_token[:8]}..."
            )
            
        except Exception as e:
            app_logger.error(f"Failed to save enrollment: {e}")
            return json.dumps({
                'status': 'error',
                'message': str(e)
            })
        
        # Send completion to Heimdall
        if self.ws_manager:
            self.ws_manager.send_enrollment_complete(
                request_id=enrollment['request_id'],
                member_number=member_number,
                enrollment_token=enrollment_token,
                gym_id=enrollment['gym_id'],
                device_id=self.device_id
            )
        
        # Emit signals
        self.enrollment_completed.emit(member_number, enrollment_token)
        self.notification.emit(
            "✅ Registro Exitoso",
            f"Huella registrada correctamente"
        )
        
        # Clear current enrollment
        self._current_enrollment = None
        
        return json.dumps({
            'status': 'complete',
            'enrollment_token': enrollment_token,
            'touch_count': 4
        })
    
    @Slot(result=bool)
    def cancelar_enrollment(self) -> bool:
        """
        Cancel current enrollment.
        
        Returns:
            True if enrollment was cancelled, False if no active enrollment
        """
        if self._current_enrollment is None:
            return False
        
        member_number = self._current_enrollment['member_number']
        
        app_logger.warning(f"❌ Enrollment cancelled | Member: {member_number}")
        
        self.enrollment_cancelled.emit(member_number)
        self.notification.emit(
            "Registro Cancelado",
            "El registro de huella fue cancelado"
        )
        
        self._current_enrollment = None
        return True
    
    # ==================== FINGERPRINT VERIFICATION ====================
    
    @Slot(str, result=str)
    def verificar_huella(self, member_number: str) -> str:
        """
        Verify fingerprint against stored template (simulated for now).
        
        Args:
            member_number: Member to verify
            
        Returns:
            JSON string: {"verified": true/false, "member_number": "...", "confidence": 0-100}
            
        JavaScript usage:
            backend.verificar_huella(member_num, function(result) {
                var data = JSON.parse(result);
                if (data.verified) console.log("Access granted!");
            });
        """
        import json
        
        app_logger.info(f"🔍 Verifying fingerprint for member: {member_number}")
        
        # TODO: Real ZKTeco SDK verification
        # For now, simulate verification by checking database
        try:
            session = database.get_session()
            enrollment = session.query(FingerprintEnrollment).filter_by(
                membership_number=member_number
            ).first()
            session.close()
            
            verified = enrollment is not None
            
            self.fingerprint_verified.emit(member_number, verified)
            
            return json.dumps({
                'verified': verified,
                'member_number': member_number,
                'confidence': 95 if verified else 0,
                'message': 'Fingerprint verified' if verified else 'No enrollment found'
            })
            
        except Exception as e:
            app_logger.error(f"Verification error: {e}")
            return json.dumps({
                'verified': False,
                'member_number': member_number,
                'confidence': 0,
                'error': str(e)
            })
    
    # ==================== UTILITY METHODS ====================
    
    @Slot(str, str)
    def mostrar_notificacion(self, title: str, message: str):
        """
        Show system tray notification (called from JavaScript).
        
        JavaScript usage:
            backend.mostrar_notificacion("Title", "Message");
        """
        app_logger.info(f"📢 Notificbrebeation: {title} - {message}")
        self.notification.emit(title, message)
    
    @Slot(result=str)
    def obtener_estado(self) -> str:
        """
        Get current bridge state (for debugging).
        
        Returns:
            JSON string with current state
        """
        import json
        
        return json.dumps({
            'device_id': self.device_id,
            'version': self.version,
            'has_enrollment': self._current_enrollment is not None,
            'websocket_connected': self.ws_manager.is_connected() if self.ws_manager else False
        })
    
    @Slot(str)
    def log_debug(self, message: str):
        """
        Log debug message from JavaScript.
        
        JavaScript usage:
            backend.log_debug("Something happened in JS");
        """
        app_logger.debug(f"🌐 [WebView] {message}")
    
    # ==================== TEST METHODS ====================
    
    @Slot(str, result=str)
    def test_modal_nativo(self, mensaje: str = "¡Comunicación exitosa!") -> str:
        """
        Show native Qt modal for testing (called from JavaScript).
        
        Args:
            mensaje: Message to display in modal
            
        Returns:
            JSON string with result
            
        JavaScript usage:
            backend.test_modal_nativo("Test message", function(resultJson) {
                const result = JSON.parse(resultJson);
                console.log(result);
            });
        """
        import json
        from PySide6.QtWidgets import QMessageBox
        
        app_logger.info(f"🧪 Test modal triggered: {mensaje}")
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("✅ Thor Desktop Agent - Test de Comunicación")
        msg_box.setText(mensaje)
        msg_box.setInformativeText(
            f"🔗 Bridge conectado correctamente\n"
            f"🖥️  Device ID: {self.device_id[:16]}...\n"
            f"📦 Version: {self.version}"
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        result = msg_box.exec()
        
        return json.dumps({
            'success': True,
            'message': mensaje,
            'device_id': self.device_id,
            'version': self.version,
            'clicked': 'OK'
        })
    
    @Slot(str, str, result=str)
    def test_confirmacion(self, titulo: str, pregunta: str) -> str:
        """
        Show Yes/No confirmation dialog (called from JavaScript).
        
        Args:
            titulo: Dialog title
            pregunta: Question to ask
            
        Returns:
            JSON string with result (clicked: 'Yes' or 'No')
            
        JavaScript usage:
            backend.test_confirmacion("Title", "Question?", function(resultJson) {
                const result = JSON.parse(resultJson);
                if (result.clicked === 'Yes') { ... }
            });
        """
        import json
        from PySide6.QtWidgets import QMessageBox
        
        app_logger.info(f"🧪 Test confirmation: {titulo} - {pregunta}")
        
        reply = QMessageBox.question(
            None,
            titulo,
            pregunta,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        clicked = 'Yes' if reply == QMessageBox.StandardButton.Yes else 'No'
        
        return json.dumps({
            'success': True,
            'clicked': clicked,
            'titulo': titulo,
            'pregunta': pregunta
        })
    
    @Slot(str, result=str)
    def test_input(self, prompt: str) -> str:
        """
        Show text input dialog (called from JavaScript).
        
        Args:
            prompt: Input prompt text
            
        Returns:
            JSON string with result (value: user input or empty string)
            
        JavaScript usage:
            backend.test_input("Enter your name:", function(resultJson) {
                const result = JSON.parse(resultJson);
                console.log('User entered:', result.value);
            });
        """
        import json
        from PySide6.QtWidgets import QInputDialog
        
        app_logger.info(f"🧪 Test input: {prompt}")
        
        text, ok = QInputDialog.getText(None, "Thor Desktop Agent", prompt)
        
        return json.dumps({
            'success': ok,
            'value': text if ok else '',
            'prompt': prompt
        })
    
    @Slot(int, result=str)
    def iniciar_captura_toques(self, toques_requeridos: int = 4) -> str:
        """
        Start fingerprint enrollment using ZKTeco ZK9500 reader.
        
        Replaces the old modal with True/False buttons. Now uses actual hardware
        to capture fingerprints. Emits touch_captured signal after each capture.
        
        Args:
            toques_requeridos: Number of successful touches required (default: 4)
            
        Returns:
            JSON string with initialization result
            
        JavaScript usage:
            // Listen to touch events
            backend.touch_captured.connect(function(touch_number, success, remaining) {
                console.log('Touch', touch_number, 'Success:', success, 'Remaining:', remaining);
            });
            
            // Start capture
            backend.iniciar_captura_toques(4, function(resultJson) {
                const result = JSON.parse(resultJson);
                console.log('Capture started:', result);
            });
        """
        import json
        
        # Check if enrollment already in progress
        if self._enrollment_in_progress:
            app_logger.warning("⚠️ Enrollment already in progress, rejecting duplicate request")
            return json.dumps({
                'success': False,
                'error': 'Ya hay una captura en progreso'
            })
        
        # Check if legacy enrollment is in progress (conflict prevention)
        if self._current_enrollment is not None:
            app_logger.warning(
                f"⚠️ Cannot start capture: enrollment in progress for "
                f"{self._current_enrollment.get('member_number')}"
            )
            return json.dumps({
                'success': False,
                'error': 'Hay un enrollment en progreso. Por favor cancela primero.'
            })
        
        # Check if reader is connected
        if not self._reader.is_connected:
            app_logger.error("❌ ZKTeco reader not connected")
            # Try to connect
            if not self._reader.connect():
                return json.dumps({
                    'success': False,
                    'error': 'No se pudo conectar al lector de huellas. Verifique la conexión USB.'
                })
        
        app_logger.info(f"🖐️ Starting ZKTeco enrollment: {toques_requeridos} touches required")
        
        self._touch_required = toques_requeridos
        self._touch_count = 0
        self._enrollment_in_progress = True
        
        # Start enrollment in background thread to prevent UI blocking
        # Use QTimer to call enrollment on main thread
        QTimer.singleShot(100, lambda: self._run_zkteco_enrollment(toques_requeridos))
        
        return json.dumps({
            'success': True,
            'toques_requeridos': toques_requeridos,
            'device': 'ZKTeco ZK9500',
            'message': 'Preparando lector de huellas. Espere la luz verde...'
        })
    
    def _run_zkteco_enrollment(self, toques_requeridos: int):
        """
        Run ZKTeco enrollment process (internal method).
        
        This runs the actual hardware capture and emits signals for each touch.
        """
        app_logger.info(f"🚀 Starting ZKTeco enrollment process...")
        
        def progress_callback(touch_number: int, success: bool, remaining: int):
            """Called after each touch capture."""
            app_logger.info(
                f"{'✅' if success else '❌'} Touch {touch_number}/{toques_requeridos} - "
                f"{'SUCCESS' if success else 'FAILED'} | Remaining: {remaining}"
            )
            
            # Emit signal to JavaScript
            self.touch_captured.emit(touch_number, success, remaining)
            
            # Process Qt events to keep UI responsive
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
        
        try:
            # Run enrollment (blocking until complete or cancelled)
            success, template = self._reader.enroll_fingerprint(
                progress_callback=progress_callback,
                required_touches=toques_requeridos,
                quality_threshold=50  # Minimum quality to accept
            )
            
            if success and template:
                app_logger.info(f"🎉 ZKTeco enrollment completed successfully")
                
                # Store template for later use (when saving to member)
                self._last_enrollment_template = template
                
                # Emit completion signal (touch_captured with final success)
                self.touch_captured.emit(toques_requeridos, True, 0)
                
                self.notification.emit(
                    "✅ Registro Exitoso",
                    f"Se capturaron {toques_requeridos} huellas correctamente"
                )
            else:
                app_logger.warning("❌ ZKTeco enrollment failed or cancelled")
                
                self.notification.emit(
                    "❌ Registro Fallido",
                    "No se pudo completar el registro de huella"
                )
        
        except Exception as e:
            app_logger.error(f"❌ Error during ZKTeco enrollment: {e}")
            
            self.notification.emit(
                "❌ Error",
                f"Error en el lector de huellas: {str(e)}"
            )
        
        finally:
            # Reset state
            self._enrollment_in_progress = False
            self._touch_count = 0
            
            app_logger.info("🏁 ZKTeco enrollment process finished")
    
    # ==================== PRIVATE LOGIC METHODS ====================
    
    def _show_test_modal(self, mensaje: str) -> dict:
        """
        Internal logic for showing test modal.
        
        Args:
            mensaje: Message to display
            
        Returns:
            dict with result data
        """
        from PySide6.QtWidgets import QMessageBox
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("✅ Thor Desktop Agent - Test de Comunicación")
        msg_box.setText(mensaje)
        msg_box.setInformativeText(
            f"🔗 Bridge conectado correctamente\n"
            f"🖥️  Device ID: {self.device_id[:16]}...\n"
            f"📦 Version: {self.version}"
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        msg_box.exec()
        
        return {
            'success': True,
            'message': mensaje,
            'device_id': self.device_id,
            'version': self.version,
            'clicked': 'OK'
        }
    
    def _show_confirmation_dialog(self, titulo: str, pregunta: str) -> dict:
        """
        Internal logic for showing confirmation dialog.
        
        Args:
            titulo: Dialog title
            pregunta: Question text
            
        Returns:
            dict with result data
        """
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            None,
            titulo,
            pregunta,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        clicked = 'Yes' if reply == QMessageBox.StandardButton.Yes else 'No'
        
        return {
            'success': True,
            'clicked': clicked,
            'titulo': titulo,
            'pregunta': pregunta
        }
    
    def _show_input_dialog(self, prompt: str) -> dict:
        """
        Internal logic for showing input dialog.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            dict with result data
        """
        from PySide6.QtWidgets import QInputDialog
        
        text, ok = QInputDialog.getText(None, "Thor Desktop Agent", prompt)
        
        return {
            'success': ok,
            'value': text if ok else '',
            'prompt': prompt
        }
    
    def _show_touch_capture_dialog(self) -> dict:
        """
        Internal logic for showing touch capture dialog with True/False buttons.
        
        Shows a persistent modal that remains open until required touches are captured.
        Emits touch_captured signal after each button press.
        
        Returns:
            dict with capture result
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar
        from PySide6.QtCore import Qt
        
        app_logger.info(f"🖐️ Starting touch capture: {self._touch_required} touches required")
        
        # Create custom dialog
        dialog = QDialog()
        dialog.setWindowTitle("🖐️ Captura de Toques - Thor Desktop Agent")
        dialog.setModal(True)
        dialog.setMinimumWidth(500)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        
        # Layout
        layout = QVBoxLayout()
        
        # Title label
        title_label = QLabel(f"<h2>Captura de Toques Biométricos</h2>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Progress label
        progress_label = QLabel(f"<b>Progreso:</b> 0 / {self._touch_required} toques exitosos")
        progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_label.setStyleSheet("font-size: 14pt; padding: 10px;")
        layout.addWidget(progress_label)
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setMaximum(self._touch_required)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%v / %m toques")
        layout.addWidget(progress_bar)
        
        # Status label
        status_label = QLabel("Esperando toque...")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("font-size: 12pt; padding: 15px; color: #666;")
        layout.addWidget(status_label)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # True button
        btn_verdadero = QPushButton("✅ VERDADERO\n(Toque Exitoso)")
        btn_verdadero.setMinimumHeight(80)
        btn_verdadero.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        
        # False button
        btn_falso = QPushButton("❌ FALSO\n(Toque Fallido)")
        btn_falso.setMinimumHeight(80)
        btn_falso.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        
        button_layout.addWidget(btn_verdadero)
        button_layout.addWidget(btn_falso)
        layout.addLayout(button_layout)
        
        # Cancel button
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("padding: 10px; font-size: 11pt;")
        layout.addWidget(btn_cancelar)
        
        dialog.setLayout(layout)
        
        # Store dialog reference
        self._touch_dialog = dialog
        
        # Button handlers
        def handle_touch(success: bool):
            """Handle touch button press."""
            # Ignore if already completed
            if self._touch_count >= self._touch_required:
                app_logger.debug(f"⚠️ Ignoring touch after completion (count: {self._touch_count})")
                return
            
            if success:
                self._touch_count += 1
                app_logger.info(f"✅ Touch {self._touch_count}/{self._touch_required} - SUCCESS")
            else:
                app_logger.info(f"❌ Touch attempt - FAILED")
            
            remaining = self._touch_required - self._touch_count
            
            # Update UI
            progress_bar.setValue(self._touch_count)
            progress_label.setText(f"<b>Progreso:</b> {self._touch_count} / {self._touch_required} toques exitosos")
            
            if success:
                status_label.setText(f"✅ Toque exitoso! Faltan {remaining} más")
                status_label.setStyleSheet("font-size: 12pt; padding: 15px; color: #10b981; font-weight: bold;")
            else:
                status_label.setText(f"❌ Toque fallido. Intenta de nuevo ({remaining} restantes)")
                status_label.setStyleSheet("font-size: 12pt; padding: 15px; color: #ef4444; font-weight: bold;")
            
            # Emit signal to JavaScript
            self.touch_captured.emit(self._touch_count, success, remaining)
            
            # Check if completed
            if self._touch_count >= self._touch_required:
                app_logger.info(f"🎉 Capture completed: {self._touch_count} successful touches")
                status_label.setText("🎉 ¡Captura completada exitosamente!")
                status_label.setStyleSheet("font-size: 12pt; padding: 15px; color: #10b981; font-weight: bold;")
                
                # Disable buttons to prevent additional clicks
                btn_verdadero.setEnabled(False)
                btn_falso.setEnabled(False)
                btn_cancelar.setText("Cerrar")
                
                # Close dialog after 1 second
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, dialog.accept)
        
        def handle_cancel():
            """Handle cancel button."""
            app_logger.info("❌ Touch capture cancelled by user")
            dialog.reject()
        
        # Connect buttons
        btn_verdadero.clicked.connect(lambda: handle_touch(True))
        btn_falso.clicked.connect(lambda: handle_touch(False))
        btn_cancelar.clicked.connect(handle_cancel)
        
        # Show dialog (blocks until closed)
        result = dialog.exec()
        
        # Cleanup
        self._touch_dialog = None
        completed = result == QDialog.DialogCode.Accepted
        
        return {
            'success': True,
            'completado': completed,
            'toques_exitosos': self._touch_count,
            'toques_requeridos': self._touch_required,
            'cancelado': not completed
        }
    
    # ==================== ZKTECO READER METHODS ====================
    
    def _connect_fingerprint_reader(self):
        """Connect to ZKTeco fingerprint reader on startup."""
        app_logger.info("🔌 Attempting to connect to ZKTeco ZK9500 reader...")
        
        if self._reader.connect(timeout=5):
            app_logger.info("✅ ZKTeco reader connected successfully")
            
            # Get device info
            info = self._reader.get_device_info()
            app_logger.info(f"📱 Device info: {info}")
            
            self.notification.emit(
                "Lector de Huellas",
                "ZKTeco ZK9500 conectado y listo"
            )
        else:
            app_logger.warning(
                "⚠️ Could not connect to ZKTeco reader on startup. "
                "Will retry when enrollment starts."
            )
    
    @Slot(result=str)
    def reconnect_reader(self) -> str:
        """
        Manually reconnect to fingerprint reader (callable from JavaScript).
        
        Returns:
            JSON string with connection result
        """
        import json
        
        app_logger.info("🔄 Manual reconnection requested...")
        
        # Disconnect first if already connected
        if self._reader.is_connected:
            self._reader.disconnect()
        
        # Try to connect
        if self._reader.connect(timeout=5):
            info = self._reader.get_device_info()
            
            return json.dumps({
                'success': True,
                'connected': True,
                'device_info': info,
                'message': 'Lector conectado correctamente'
            })
        else:
            return json.dumps({
                'success': False,
                'connected': False,
                'error': 'No se pudo conectar al lector de huellas',
                'message': 'Verifique que el lector esté conectado por USB'
            })
    
    @Slot(result=str)
    def get_reader_status(self) -> str:
        """
        Get fingerprint reader status (callable from JavaScript).
        
        Returns:
            JSON string with reader status
        """
        import json
        
        if self._reader.is_connected:
            info = self._reader.get_device_info()
            return json.dumps({
                'connected': True,
                'device_info': info,
                'enrollment_in_progress': self._enrollment_in_progress
            })
        else:
            return json.dumps({
                'connected': False,
                'error': 'Reader not connected',
                'enrollment_in_progress': self._enrollment_in_progress
            })
