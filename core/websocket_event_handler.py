"""WebSocket Event Handler - Delegates Heimdall WebSocket events."""
from typing import Optional, Set

from PySide6.QtWidgets import QSystemTrayIcon

from services.websocket_manager import WebSocketManager
from utils.logger import app_logger


class WebSocketEventHandler:
    """Handles WebSocket events from Heimdall and delegates to appropriate handlers."""
    
    def __init__(self, ws_manager: WebSocketManager, system_tray: QSystemTrayIcon):
        """Initialize WebSocket event handler.
        
        Args:
            ws_manager: WebSocket manager instance
            system_tray: System tray icon for notifications
        """
        self.ws_manager = ws_manager
        self.system_tray = system_tray
        self.active_enrollment_requests: Set[str] = set()
        
        # Event handlers to be set by main application
        self.on_fingerprint_enroll = None
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup WebSocket signal handlers."""
        self.ws_manager.connected.connect(self._on_connected)
        self.ws_manager.disconnected.connect(self._on_disconnected)
        self.ws_manager.checkin_received.connect(self._on_checkin)
        self.ws_manager.verify_access_received.connect(self._on_verify_access)
        self.ws_manager.fingerprint_enroll_received.connect(self._handle_fingerprint_enroll)
        
        app_logger.debug("WebSocket event handlers configured")
    
    def _on_connected(self):
        """Handle WebSocket connection established."""
        app_logger.info("✅ Connected to Heimdall WebSocket")
        self.system_tray.show_message(
            "Heimdall Conectado",
            "Conexión establecida con el servidor de eventos"
        )
    
    def _on_disconnected(self):
        """Handle WebSocket disconnection."""
        app_logger.warning("⚠️ Disconnected from Heimdall")
    
    def _on_checkin(self, data: dict):
        """Handle check-in event.
        
        Args:
            data: Check-in data from Heimdall
        """
        member_name = data.get('member_name', 'Unknown')
        app_logger.info(f"🏋️ Check-in: {member_name}")
        
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
        
        self.system_tray.show_message(
            "Verificación de Acceso",
            f"Verificando acceso de {member_name}..."
        )
    
    def _handle_fingerprint_enroll(self, enrollment_data: dict):
        """Handle fingerprint enrollment request from Heimdall.
        
        Prevents duplicate enrollments and delegates to external handler.
        
        Args:
            enrollment_data: Enrollment data including request_id, member_number, member_name
        """
        request_id = enrollment_data.get('request_id')
        member_number = enrollment_data.get('member_number')
        member_name = enrollment_data.get('member_name', 'Unknown')
        
        # Check for duplicate enrollment
        if member_number in self.active_enrollment_requests:
            app_logger.warning(
                f"⚠️ Duplicate enrollment request ignored | "
                f"Request: {request_id} | Member: {member_number}"
            )
            return
        
        # Mark member as actively enrolling
        self.active_enrollment_requests.add(member_number)
        
        app_logger.info(
            f"🔐 Fingerprint enrollment requested | "
            f"Request: {request_id} | Member: {member_number} ({member_name})"
        )
        
        # Show system notification
        self.system_tray.show_message(
            "Registro de Huella",
            f"Iniciando registro de huella para {member_name}"
        )
        
        # Delegate to external handler if configured
        if self.on_fingerprint_enroll:
            self.on_fingerprint_enroll(enrollment_data)
        else:
            app_logger.warning("No fingerprint enrollment handler configured")
    
    def clear_enrollment(self, member_number: str):
        """Clear enrollment tracking for a member.
        
        Args:
            member_number: Member number to remove from tracking
        """
        self.active_enrollment_requests.discard(member_number)
        app_logger.debug(f"Cleared enrollment tracking for member: {member_number}")
