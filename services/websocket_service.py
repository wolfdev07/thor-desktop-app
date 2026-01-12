"""WebSocket service for Heimdall real-time events."""
import asyncio
import json
from typing import Optional, Callable, Dict, Any
from websockets.client import connect, WebSocketClientProtocol
from websockets.exceptions import WebSocketException, ConnectionClosed

from config.settings import HEIMDALL_WS_URL, HEIMDALL_WS_ENDPOINT, HEIMDALL_HEARTBEAT_INTERVAL
from utils.keyring_manager import keyring_manager
from config.constants import KEY_ACCESS_TOKEN
from utils.logger import app_logger


class HeimdallWebSocketClient:
    """WebSocket client for Heimdall real-time communication."""
    
    def __init__(self):
        self.ws: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_running = False
        self._handlers: Dict[str, Callable] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._listen_task: Optional[asyncio.Task] = None
        
    def on(self, event_type: str, handler: Callable):
        """Register event handler.
        
        Args:
            event_type: Event type to handle (e.g., 'verify_access', 'enroll_biometric')
            handler: Async callback function
        """
        self._handlers[event_type] = handler
        app_logger.debug(f"Registered handler for event: {event_type}")
    
    async def connect(self) -> bool:
        """Connect to Heimdall WebSocket.
        
        Returns:
            True if connected successfully
        """
        try:
            access_token = keyring_manager.get(KEY_ACCESS_TOKEN)
            
            if not access_token:
                app_logger.error("Cannot connect to Heimdall: No access token")
                return False
            
            # Decode token to check expiration (without verification)
            import jwt
            from datetime import datetime, timezone
            
            try:
                payload = jwt.decode(access_token, options={"verify_signature": False})
                exp = payload.get('exp', 0)
                now_ts = datetime.now(timezone.utc).timestamp()
                
                app_logger.debug(f"Token exp: {exp}, now: {now_ts}, diff: {exp - now_ts} seconds")
                
                # If token expires in less than 1 minute, it's too close
                if exp - now_ts < 60:
                    app_logger.warning(f"Access token expired or expiring soon (expires in {int(exp - now_ts)}s)")
                    return False
                
                app_logger.info(f"✅ Token valid for {int((exp - now_ts) / 60)} more minutes")
            
            except Exception as e:
                app_logger.error(f"Could not decode token: {e}")
                import traceback
                app_logger.error(traceback.format_exc())
            
            # Build WebSocket URL
            url = f"{HEIMDALL_WS_URL}{HEIMDALL_WS_ENDPOINT}?token={access_token}"
            
            app_logger.info(f"Connecting to Heimdall: {HEIMDALL_WS_URL}")
            
            # Connect to WebSocket
            self.ws = await connect(url)
            self.is_connected = True
            self.is_running = True
            
            app_logger.info("✅ Connected to Heimdall WebSocket")
            
            # Start background tasks
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._listen_task = asyncio.create_task(self._listen_loop())
            
            return True
            
        except WebSocketException as e:
            app_logger.error(f"WebSocket connection error: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            app_logger.error(f"Unexpected connection error: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Heimdall WebSocket."""
        self.is_running = False
        
        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._listen_task:
            self._listen_task.cancel()
        
        # Close WebSocket connection
        if self.ws:
            await self.ws.close()
            self.is_connected = False
            app_logger.info("Disconnected from Heimdall")
    
    async def _listen_loop(self):
        """Listen for incoming messages."""
        if not self.ws:
            return
        
        try:
            while self.is_running:
                message = await self.ws.recv()
                await self._handle_message(message)
        
        except ConnectionClosed:
            app_logger.warning("Heimdall connection closed")
            self.is_connected = False
            # TODO: Implement auto-reconnect
        
        except Exception as e:
            app_logger.error(f"Error in listen loop: {e}")
            self.is_connected = False
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message.
        
        Args:
            message: Raw JSON message string
        """
        try:
            data = json.loads(message)
            event_type = data.get("type")
            
            app_logger.debug(f"📨 Received event: {event_type}")
            
            # Handle welcome message
            if event_type == "system" and data.get("action") == "welcome":
                app_logger.info(f"✅ Heimdall welcome: {data.get('message')}")
                connection_id = data.get("connection_id")
                gym_id = data.get("gym_id")
                app_logger.info(f"Connected as desktop_app | Connection: {connection_id} | Gym: {gym_id}")
                return
            
            # Handle pong
            if event_type == "pong":
                app_logger.debug("💓 Heartbeat acknowledged")
                return
            
            # Call registered handler
            if event_type in self._handlers:
                await self._handlers[event_type](data)
            else:
                app_logger.debug(f"No handler for event: {event_type}")
        
        except json.JSONDecodeError:
            app_logger.error(f"Invalid JSON message: {message}")
        except Exception as e:
            app_logger.error(f"Error handling message: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat (ping)."""
        try:
            while self.is_running:
                await asyncio.sleep(HEIMDALL_HEARTBEAT_INTERVAL)
                
                if self.is_connected:
                    await self.send_action("ping")
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            app_logger.error(f"Error in heartbeat loop: {e}")
    
    async def send_action(self, action: str, data: Dict[str, Any] = None):
        """Send action to Heimdall.
        
        Args:
            action: Action name (e.g., 'ping', 'access_granted')
            data: Optional action data
        """
        if not self.ws or not self.is_connected:
            app_logger.warning(f"Cannot send action {action}: Not connected")
            return False
        
        try:
            message = {"action": action}
            if data:
                message.update(data)
            
            await self.ws.send(json.dumps(message))
            app_logger.debug(f"📤 Sent action: {action}")
            return True
        
        except Exception as e:
            app_logger.error(f"Error sending action {action}: {e}")
            return False
    
    async def notify_access_granted(self, request_id: str, member_id: int, 
                                   method: str = "fingerprint", template_matched: str = None):
        """Notify Heimdall that access was granted.
        
        Args:
            request_id: Request ID from verify_access event
            member_id: Member ID
            method: Authentication method (default: 'fingerprint')
            template_matched: Template ID that matched (optional)
        """
        data = {
            "request_id": request_id,
            "member_id": member_id,
            "method": method
        }
        
        if template_matched:
            data["template_matched"] = template_matched
        
        await self.send_action("access_granted", data)
        app_logger.info(f"✅ Access granted for member {member_id}")
    
    async def notify_access_denied(self, request_id: str, member_id: int, reason: str):
        """Notify Heimdall that access was denied.
        
        Args:
            request_id: Request ID from verify_access event
            member_id: Member ID
            reason: Denial reason
        """
        await self.send_action("access_denied", {
            "request_id": request_id,
            "member_id": member_id,
            "reason": reason
        })
        app_logger.warning(f"❌ Access denied for member {member_id}: {reason}")
    
    async def notify_biometric_enrolled(self, request_id: str, member_id: int, 
                                       template_id: str, finger_index: int):
        """Notify Heimdall that biometric was enrolled.
        
        Args:
            request_id: Request ID from enroll_biometric event
            member_id: Member ID
            template_id: New template ID
            finger_index: Finger index (0-9)
        """
        await self.send_action("biometric_enrolled", {
            "request_id": request_id,
            "member_id": member_id,
            "template_id": template_id,
            "finger_index": finger_index
        })
        app_logger.info(f"👆 Biometric enrolled for member {member_id}")
    
    async def send_device_status(self, status: Dict[str, Any]):
        """Send device status to Heimdall.
        
        Args:
            status: Device status dictionary
        """
        await self.send_action("device_status", {"status": status})


# Singleton instance
heimdall_client = HeimdallWebSocketClient()

