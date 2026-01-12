"""Secure credential storage using system keyring."""
import keyring
from typing import Optional
from config.settings import KEYRING_SERVICE_NAME
from utils.logger import app_logger


class KeyringManager:
    """Manage secure credential storage."""
    
    def __init__(self, service_name: str = KEYRING_SERVICE_NAME):
        self.service_name = service_name
    
    def set(self, key: str, value: str) -> bool:
        """Store a credential securely.
        
        Args:
            key: Credential key
            value: Credential value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            keyring.set_password(self.service_name, key, value)
            app_logger.debug(f"Stored credential: {key}")
            return True
        except Exception as e:
            app_logger.error(f"Failed to store credential {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve a credential.
        
        Args:
            key: Credential key
            
        Returns:
            Credential value or None if not found
        """
        try:
            value = keyring.get_password(self.service_name, key)
            if value:
                app_logger.debug(f"Retrieved credential: {key}")
            return value
        except Exception as e:
            app_logger.error(f"Failed to retrieve credential {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a credential.
        
        Args:
            key: Credential key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            keyring.delete_password(self.service_name, key)
            app_logger.debug(f"Deleted credential: {key}")
            return True
        except keyring.errors.PasswordDeleteError:
            app_logger.warning(f"Credential not found: {key}")
            return False
        except Exception as e:
            app_logger.error(f"Failed to delete credential {key}: {e}")
            return False
    
    def clear_all(self, keys: Optional[list[str]] = None) -> bool:
        """Clear multiple credentials.
        
        Args:
            keys: List of credential keys to delete. 
                  If None, deletes all known credentials.
            
        Returns:
            True if all successful, False otherwise
        """
        from config.constants import (
            KEY_ACCESS_TOKEN, KEY_REFRESH_TOKEN, 
            KEY_DEVICE_ID, KEY_USER_EMAIL
        )
        
        if keys is None:
            # Delete all known credentials
            keys = [
                KEY_ACCESS_TOKEN,
                KEY_REFRESH_TOKEN,
                KEY_DEVICE_ID,
                KEY_USER_EMAIL
            ]
        
        success = True
        for key in keys:
            if not self.delete(key):
                success = False
        
        app_logger.info(f"Cleared {len(keys)} credentials")
        return success


# Singleton instance
keyring_manager = KeyringManager()
