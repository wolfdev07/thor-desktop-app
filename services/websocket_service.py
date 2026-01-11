"""WebSocket service for real-time events."""
import asyncio
import json
from typing import Optional, Callable
from websockets.client import connect, WebSocketClientProtocol
from websockets.exceptions import WebSocketException

from config.settings import API_BASE_URL
from utils.keyring_manager import keyring_manager
from config.constants import KEY_ACCESS_TOKEN, KEY_DEVICE_ID
from utils.logger import app_logger


class WebSocketService:
    """WebSocket client for real-time communication with backend."""
    
    def __init__(self):
        self.ws: Optional[WebSocketClientProtocol] = None
        self.ws_url = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://')
        self.is_connected = False
        self.message_handler: Optional[Callable] = None
        self._running = False
    
    async def connect(self):
        """Connect to WebSocket server."""
        try:
            access_token = keyring_manager.get(KEY_ACCESS_TOKEN)
            device_id = keyring_manager.get(KEY_DEVICE_ID)
            
            if not access_token or not device_id:
                app_logger.error("Cannot connect to WebSocket: Not authenticated")
                return False
            
            # WebSocket URL with auth parameters
            url = f"{self.ws_url}/ws/events?token={access_token}&device_id={device_id}"
            
            app_logger.info(f"Connecting to WebSocket: {self.ws_url}")
            
            self.ws = await connect(url)
            self.is_connected = True
            app_logger.info("WebSocket connected")
            
            return True
            
        except WebSocketException as e:
            app_logger.error(f"WebSocket connection error: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            app_logger.error(f"Unexpected WebSocket error: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.ws:
            await self.ws.close()
            self.is_connected = False
            app_logger.info("WebSocket disconnected")
    
    async def listen(self):
        """Listen for incoming WebSocket messages."""
        if not self.ws or not self.is_connected:
            app_logger.warning("Cannot listen: WebSocket not connected")
            return
        
        self._running = True
        
        try:
            while self._running:
                message = await self.ws.recv()
                await self._handle_message(message)
        except WebSocketException as e:
            app_logger.error(f"WebSocket error during listen: {e}")
            self.is_connected = False
        except Exception as e:
            app_logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message.
        
        Args:
            message: Raw message string
        """
        try:
            data = json.loads(message)
            app_logger.debug(f"WebSocket message received: {data.get('type', 'unknown')}")
            
            if self.message_handler:
                self.message_handler(data)
            
        except json.JSONDecodeError:
            app_logger.error(f"Invalid JSON in WebSocket message: {message}")
    
    def set_message_handler(self, handler: Callable):
        """Set handler for incoming messages.
        
        Args:
            handler: Callback function for messages
        """
        self.message_handler = handler
    
    async def send(self, message: dict):
        """Send message to WebSocket server.
        
        Args:
            message: Message dictionary to send
        """
        if not self.ws or not self.is_connected:
            app_logger.warning("Cannot send: WebSocket not connected")
            return False
        
        try:
            await self.ws.send(json.dumps(message))
            app_logger.debug(f"WebSocket message sent: {message.get('type', 'unknown')}")
            return True
        except Exception as e:
            app_logger.error(f"Error sending WebSocket message: {e}")
            return False
    
    def stop(self):
        """Stop listening for messages."""
        self._running = False


# Singleton instance
websocket_service = WebSocketService()
