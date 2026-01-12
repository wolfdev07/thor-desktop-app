"""Encryption utilities for database and sensitive data."""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from utils.logger import app_logger
from utils.keyring_manager import keyring_manager
from config.constants import KEY_DB_ENCRYPTION_KEY


class Encryption:
    """Handle encryption/decryption of sensitive data."""
    
    def __init__(self):
        self._cipher: Optional[Fernet] = None
        self._initialize_cipher()
    
    def _generate_key(self) -> bytes:
        """Generate a new encryption key.
        
        Returns:
            32-byte encryption key
        """
        return Fernet.generate_key()
    
    def _derive_key_from_device(self, salt: bytes) -> bytes:
        """Derive encryption key from device-specific data.
        
        Args:
            salt: Salt for key derivation
            
        Returns:
            Derived encryption key
        """
        from core.device_fingerprint import device_fingerprint
        
        # Get device fingerprint
        fp = device_fingerprint.generate()
        
        # Create seed from device-specific data
        seed = f"{fp['uuid']}{fp['cpu_id']}{fp['mac_hash']}".encode()
        
        # Derive key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(seed))
        return key
    
    def _initialize_cipher(self):
        """Initialize encryption cipher."""
        try:
            # Try to get existing key from keyring
            stored_key = keyring_manager.get(KEY_DB_ENCRYPTION_KEY)
            
            if stored_key:
                app_logger.debug("Using existing encryption key from keyring")
                key = stored_key.encode()
            else:
                app_logger.info("Generating new encryption key")
                
                # Generate salt
                salt = os.urandom(16)
                
                # Derive key from device fingerprint
                key = self._derive_key_from_device(salt)
                
                # Store key in keyring
                keyring_manager.set(KEY_DB_ENCRYPTION_KEY, key.decode())
                
                # Store salt separately (in plaintext file, it's ok)
                from config.settings import DATA_DIR
                salt_file = DATA_DIR / ".salt"
                with open(salt_file, 'wb') as f:
                    f.write(salt)
                
                app_logger.info("Encryption key generated and stored")
            
            self._cipher = Fernet(key)
            
        except Exception as e:
            app_logger.error(f"Failed to initialize cipher: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data.
        
        Args:
            data: Plain text to encrypt
            
        Returns:
            Base64-encoded encrypted data
        """
        try:
            encrypted = self._cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            app_logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted plain text
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            app_logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt binary data.
        
        Args:
            data: Binary data to encrypt
            
        Returns:
            Encrypted binary data
        """
        try:
            return self._cipher.encrypt(data)
        except Exception as e:
            app_logger.error(f"Binary encryption failed: {e}")
            raise
    
    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypt binary data.
        
        Args:
            encrypted_data: Encrypted binary data
            
        Returns:
            Decrypted binary data
        """
        try:
            return self._cipher.decrypt(encrypted_data)
        except Exception as e:
            app_logger.error(f"Binary decryption failed: {e}")
            raise


# Singleton instance
encryption = Encryption()
