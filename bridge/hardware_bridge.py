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
from PySide6.QtCore import QObject, Signal, Slot, Property
from utils.logger import app_logger
from core.database import database, FingerprintEnrollment
from utils.keyring_manager import keyring_manager
from config.constants import KEY_DEVICE_ID


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
    
    def __init__(self, ws_manager=None):
        """
        Initialize hardware bridge.
        
        Args:
            ws_manager: Optional WebSocketManager for Heimdall communication
        """
        super().__init__()
        self.ws_manager = ws_manager
        self._current_enrollment = None  # Stores active enrollment data
        self._device_id = None
        
        app_logger.info("🌉 Hardware Bridge initialized")
    
    # ==================== PROPERTIES ====================
    
    @Property(str)
    def device_id(self) -> str:
        """Get device ID (read-only property for JS)."""
        if not self._device_id:
            self._device_id = keyring_manager.get(KEY_DEVICE_ID) or "unknown"
        return self._device_id
    
    @Property(str)
    def version(self) -> str:
        """Get application version."""
        from config.constants import APP_VERSION
        return APP_VERSION
    
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
        app_logger.info(f"📢 Notification: {title} - {message}")
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
