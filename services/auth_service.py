"""Authentication service - handles API communication."""
import requests
from typing import Optional, Tuple
from requests.exceptions import RequestException, Timeout, ConnectionError

from config.settings import API_BASE_URL, API_DESKTOP_PATH
from config.constants import (
    ENDPOINT_LOGIN, ENDPOINT_REFRESH, ENDPOINT_LOGOUT,
    KEY_ACCESS_TOKEN, KEY_REFRESH_TOKEN, KEY_DEVICE_ID, KEY_USER_EMAIL
)
from core.device_fingerprint import device_fingerprint
from utils.keyring_manager import keyring_manager
from utils.logger import app_logger
from models import User, LoginResponse, RefreshResponse, ApiError


class AuthService:
    """Handle authentication with backend API."""
    
    def __init__(self):
        self.base_url = f"{API_BASE_URL}{API_DESKTOP_PATH}"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _handle_response(self, response: requests.Response) -> Tuple[bool, dict]:
        """Handle API response.
        
        Args:
            response: Requests response object
            
        Returns:
            Tuple of (success, data/error)
        """
        try:
            data = response.json()
        except ValueError:
            data = {'error': 'Invalid response from server'}
        
        if response.status_code in [200, 201]:
            return True, data
        else:
            error_msg = data.get('error', data.get('detail', 'Unknown error'))
            app_logger.error(f"API error [{response.status_code}]: {error_msg}")
            return False, {
                'error': error_msg,
                'status_code': response.status_code,
                'detail': data
            }
    
    def login(self, username: str, password: str) -> Tuple[bool, Optional[LoginResponse], Optional[str]]:
        """Login to the system.
        
        Args:
            username: User email
            password: User password
            
        Returns:
            Tuple of (success, LoginResponse/None, error_message/None)
        """
        try:
            # Generate device fingerprint
            fingerprint = device_fingerprint.generate()
            
            payload = {
                'username': username,
                'password': password,
                'fingerprint': fingerprint
            }
            
            app_logger.info(f"Attempting login for: {username}")
            
            response = self.session.post(
                f"{self.base_url}{ENDPOINT_LOGIN}",
                json=payload,
                timeout=10
            )
            
            success, data = self._handle_response(response)
            
            if success:
                # Parse response
                user_data = data['user']
                user = User(
                    id=user_data['id'],
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    user_type=user_data['user_type']
                )
                
                login_response = LoginResponse(
                    access_token=data['access_token'],
                    refresh_token=data['refresh_token'],
                    device_id=data['device_id'],
                    user=user
                )
                
                # Store credentials securely
                self._store_credentials(login_response)
                
                app_logger.info(f"Login successful for: {username}")
                return True, login_response, None
            else:
                error_msg = data.get('error', 'Login failed')
                return False, None, error_msg
                
        except Timeout:
            error_msg = "Connection timeout. Please check your internet connection."
            app_logger.error(error_msg)
            return False, None, error_msg
        except ConnectionError:
            error_msg = "Cannot connect to server. Please check your internet connection."
            app_logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Login error: {str(e)}"
            app_logger.error(error_msg)
            return False, None, error_msg
    
    def refresh_token(self) -> Tuple[bool, Optional[RefreshResponse], Optional[str]]:
        """Refresh access token.
        
        Returns:
            Tuple of (success, RefreshResponse/None, error_message/None)
        """
        try:
            refresh_token = keyring_manager.get(KEY_REFRESH_TOKEN)
            device_id = keyring_manager.get(KEY_DEVICE_ID)
            
            if not refresh_token or not device_id:
                error_msg = "No refresh token found. Please login again."
                app_logger.warning(error_msg)
                return False, None, error_msg
            
            payload = {
                'refresh_token': refresh_token,
                'device_id': device_id
            }
            
            app_logger.info("Refreshing access token")
            
            response = self.session.post(
                f"{self.base_url}{ENDPOINT_REFRESH}",
                json=payload,
                timeout=10
            )
            
            success, data = self._handle_response(response)
            
            if success:
                refresh_response = RefreshResponse(
                    access_token=data['access_token'],
                    refresh_token=data['refresh_token']
                )
                
                # Update stored tokens
                keyring_manager.set(KEY_ACCESS_TOKEN, refresh_response.access_token)
                keyring_manager.set(KEY_REFRESH_TOKEN, refresh_response.refresh_token)
                
                app_logger.info("Token refresh successful")
                return True, refresh_response, None
            else:
                error_msg = data.get('error', 'Token refresh failed')
                
                # If token is invalid, clear credentials
                if data.get('status_code') in [401, 403]:
                    app_logger.warning("Invalid refresh token, clearing credentials")
                    self.clear_credentials()
                
                return False, None, error_msg
                
        except Exception as e:
            error_msg = f"Token refresh error: {str(e)}"
            app_logger.error(error_msg)
            return False, None, error_msg
    
    def logout(self) -> Tuple[bool, Optional[str]]:
        """Logout from the system.
        
        Returns:
            Tuple of (success, error_message/None)
        """
        try:
            refresh_token = keyring_manager.get(KEY_REFRESH_TOKEN)
            device_id = keyring_manager.get(KEY_DEVICE_ID)
            
            if refresh_token and device_id:
                payload = {
                    'refresh_token': refresh_token,
                    'device_id': device_id
                }
                
                app_logger.info("Logging out")
                
                response = self.session.post(
                    f"{self.base_url}{ENDPOINT_LOGOUT}",
                    json=payload,
                    timeout=10
                )
                
                success, data = self._handle_response(response)
                
                if not success:
                    app_logger.warning(f"Logout API call failed: {data.get('error')}")
            
            # Always clear local credentials
            self.clear_credentials()
            app_logger.info("Logout successful")
            return True, None
            
        except Exception as e:
            error_msg = f"Logout error: {str(e)}"
            app_logger.error(error_msg)
            # Still clear credentials on error
            self.clear_credentials()
            return False, error_msg
    
    def _store_credentials(self, login_response: LoginResponse):
        """Store credentials securely.
        
        Args:
            login_response: Login response with tokens
        """
        keyring_manager.set(KEY_ACCESS_TOKEN, login_response.access_token)
        keyring_manager.set(KEY_REFRESH_TOKEN, login_response.refresh_token)
        keyring_manager.set(KEY_DEVICE_ID, login_response.device_id)
        keyring_manager.set(KEY_USER_EMAIL, login_response.user.email)
        
        app_logger.debug("Credentials stored in keyring")
    
    def clear_credentials(self):
        """Clear all stored credentials."""
        keys = [KEY_ACCESS_TOKEN, KEY_REFRESH_TOKEN, KEY_DEVICE_ID, KEY_USER_EMAIL]
        keyring_manager.clear_all(keys)
        app_logger.debug("Credentials cleared from keyring")
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in.
        
        Returns:
            True if valid tokens exist
        """
        access_token = keyring_manager.get(KEY_ACCESS_TOKEN)
        refresh_token = keyring_manager.get(KEY_REFRESH_TOKEN)
        device_id = keyring_manager.get(KEY_DEVICE_ID)
        
        return all([access_token, refresh_token, device_id])
    
    def get_current_user_email(self) -> Optional[str]:
        """Get current logged in user email.
        
        Returns:
            User email or None
        """
        return keyring_manager.get(KEY_USER_EMAIL)
    
    def make_authenticated_request(self, endpoint: str, method: str = 'GET', 
                                   data: dict = None, retry: bool = True) -> Tuple[bool, dict]:
        """Make authenticated API request.
        
        Args:
            endpoint: API endpoint (e.g., '/devices')
            method: HTTP method
            data: Request payload
            retry: Whether to retry with token refresh on 401
            
        Returns:
            Tuple of (success, response_data/error)
        """
        try:
            access_token = keyring_manager.get(KEY_ACCESS_TOKEN)
            device_id = keyring_manager.get(KEY_DEVICE_ID)
            
            if not access_token or not device_id:
                return False, {'error': 'Not authenticated'}
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Device-ID': device_id
            }
            
            response = self.session.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=data,
                timeout=10
            )
            
            # If unauthorized and retry enabled, refresh token and retry
            if response.status_code == 401 and retry:
                app_logger.info("Access token expired, refreshing...")
                success, _, error = self.refresh_token()
                
                if success:
                    # Retry request with new token
                    return self.make_authenticated_request(endpoint, method, data, retry=False)
                else:
                    return False, {'error': f'Authentication failed: {error}'}
            
            return self._handle_response(response)
            
        except Exception as e:
            error_msg = f"Request error: {str(e)}"
            app_logger.error(error_msg)
            return False, {'error': error_msg}


# Singleton instance
auth_service = AuthService()
