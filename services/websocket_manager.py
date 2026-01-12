"""WebSocket manager for Qt integration."""
import asyncio
from qasync import QEventLoop
from PySide6.QtCore import QObject, Signal

from services.websocket_service import heimdall_client
from utils.logger import app_logger


class WebSocketManager(QObject):
    """Manage WebSocket connection with Qt event loop integration."""
    
    # Signals for UI updates
    connected = Signal()
    disconnected = Signal()
    checkin_received = Signal(dict)
    payment_received = Signal(dict)
    verify_access_received = Signal(dict)
    enroll_biometric_received = Signal(dict)
    fingerprint_enroll_received = Signal(dict)  # Emits full enrollment data
    notification_received = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = heimdall_client
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup event handlers for Heimdall events."""
        
        async def handle_checkin(data):
            """Handle check-in event."""
            app_logger.info(f"🏋️ Check-in: {data['data']}")
            self.checkin_received.emit(data['data'])
        
        async def handle_payment(data):
            """Handle payment event."""
            app_logger.info(f"💳 Payment: {data['data']}")
            self.payment_received.emit(data['data'])
        
        async def handle_verify_access(data):
            """Handle verify access request."""
            app_logger.info(f"🔍 Verify access request: {data['data']}")
            self.verify_access_received.emit(data['data'])
            
            # TODO: Integrate with ZKTeco for real fingerprint verification
            # For now, auto-grant access
            request_id = data['data']['request_id']
            member_id = data['data']['member_id']
            
            await self.client.notify_access_granted(
                request_id=request_id,
                member_id=member_id,
                method="fingerprint"
            )
        
        async def handle_enroll(data):
            """Handle biometric enrollment request."""
            app_logger.info(f"👆 Enroll request: {data['data']}")
            self.enroll_biometric_received.emit(data['data'])
            
            # TODO: Integrate with ZKTeco for real enrollment
            # For now, just acknowledge
        
        async def handle_fingerprint_enroll(data):
            """Handle fingerprint enrollment request (simulated ZKTeco)."""
            enrollment_data = data.get('data', {})
            request_id = enrollment_data.get('request_id')
            member_number = enrollment_data.get('member_number')
            member_name = enrollment_data.get('member_name', 'Unknown')
            
            app_logger.info(
                f"🔐 Fingerprint enrollment request | "
                f"Request: {request_id} | Member: {member_number} ({member_name})"
            )
            
            # Emit signal with full data
            self.fingerprint_enroll_received.emit(enrollment_data)
        
        async def handle_notification(data):
            """Handle general notification."""
            app_logger.info(f"🔔 Notification: {data['data']}")
            self.notification_received.emit(data['data'])
        
        # Register handlers
        self.client.on("checkin", handle_checkin)
        self.client.on("payment", handle_payment)
        self.client.on("verify_access", handle_verify_access)
        self.client.on("enroll_biometric", handle_enroll)
        self.client.on("fingerprint_enroll", handle_fingerprint_enroll)
        self.client.on("notification", handle_notification)
    
    async def connect_async(self):
        """Connect to Heimdall (async)."""
        # Check if token is still valid, refresh if needed
        from services.auth_service import auth_service
        
        # Try to refresh token first to ensure it's fresh
        app_logger.info("Refreshing token before connecting to Heimdall...")
        success, _, error = auth_service.refresh_token()
        
        if not success:
            app_logger.error(f"Failed to refresh token: {error}")
            return False
        
        # Now connect with fresh token
        success = await self.client.connect()
        if success:
            self.connected.emit()
        else:
            app_logger.error("Failed to connect to Heimdall after token refresh")
        return success
    
    async def disconnect_async(self):
        """Disconnect from Heimdall (async)."""
        await self.client.disconnect()
        self.disconnected.emit()
    
    async def send_enrollment_progress_async(self, request_id: str, member_number: str, 
                                            touch_number: int, success: bool, gym_id: int):
        """Send enrollment progress to Heimdall (async)."""
        await self.client.notify_enrollment_progress(
            request_id, member_number, touch_number, success, gym_id
        )
    
    async def send_enrollment_complete_async(self, request_id: str, member_number: str, 
                                            enrollment_token: str, gym_id: int, device_id: str):
        """Send enrollment complete to Heimdall (async)."""
        await self.client.notify_enrollment_complete(
            request_id, member_number, enrollment_token, gym_id, device_id
        )
    
    def connect(self):
        """Connect to Heimdall (sync wrapper for Qt)."""
        loop = asyncio.get_event_loop()
        loop.create_task(self.connect_async())
    
    def disconnect(self):
        """Disconnect from Heimdall (sync wrapper for Qt)."""
        loop = asyncio.get_event_loop()
        loop.create_task(self.disconnect_async())
    
    def send_enrollment_progress(self, request_id: str, member_number: str, 
                                 touch_number: int, success: bool, gym_id: int):
        """Send enrollment progress to Heimdall (sync wrapper for Qt)."""
        loop = asyncio.get_event_loop()
        loop.create_task(
            self.send_enrollment_progress_async(request_id, member_number, touch_number, success, gym_id)
        )
    
    def send_enrollment_complete(self, request_id: str, member_number: str, 
                                enrollment_token: str, gym_id: int, device_id: str):
        """Send enrollment complete to Heimdall (sync wrapper for Qt)."""
        loop = asyncio.get_event_loop()
        loop.create_task(
            self.send_enrollment_complete_async(request_id, member_number, enrollment_token, gym_id, device_id)
        )
