"""Device fingerprinting for authentication."""
import platform
import uuid
import hashlib
from typing import Dict, Optional
from getmac import get_mac_address
import cpuinfo
from utils.logger import app_logger


class DeviceFingerprint:
    """Generate unique device fingerprint for authentication."""
    
    @staticmethod
    def get_cpu_id() -> str:
        """Get CPU identifier.
        
        Returns:
            CPU brand/model string
        """
        try:
            cpu_info = cpuinfo.get_cpu_info()
            return cpu_info.get('brand_raw', cpu_info.get('brand', 'Unknown'))
        except Exception as e:
            app_logger.warning(f"Failed to get CPU info: {e}")
            return "Unknown"
    
    @staticmethod
    def get_mac_hash() -> str:
        """Get hashed MAC address for privacy.
        
        Returns:
            MD5 hash of MAC address
        """
        try:
            mac = get_mac_address()
            if mac:
                return hashlib.md5(mac.encode()).hexdigest()
            return "Unknown"
        except Exception as e:
            app_logger.warning(f"Failed to get MAC address: {e}")
            return "Unknown"
    
    @staticmethod
    def get_system_uuid() -> str:
        """Get system UUID.
        
        Returns:
            System UUID string
        """
        try:
            # Get MAC-based UUID
            return str(uuid.getnode())
        except Exception as e:
            app_logger.warning(f"Failed to get system UUID: {e}")
            return str(uuid.uuid4())
    
    @staticmethod
    def get_os_info() -> tuple[str, str]:
        """Get operating system information.
        
        Returns:
            Tuple of (OS name, OS version)
        """
        try:
            os_name = platform.system()
            os_version = platform.release()
            return os_name, os_version
        except Exception as e:
            app_logger.warning(f"Failed to get OS info: {e}")
            return "Unknown", "Unknown"
    
    @staticmethod
    def get_device_name() -> str:
        """Get device/computer name.
        
        Returns:
            Device name
        """
        try:
            return platform.node()
        except Exception as e:
            app_logger.warning(f"Failed to get device name: {e}")
            return "Unknown"
    
    @classmethod
    def generate(cls) -> Dict[str, str]:
        """Generate complete device fingerprint.
        
        Returns:
            Dictionary with fingerprint data
        """
        os_name, os_version = cls.get_os_info()
        
        fingerprint = {
            'uuid': cls.get_system_uuid(),
            'cpu_id': cls.get_cpu_id(),
            'mac_hash': cls.get_mac_hash(),
            'os': os_name,
            'os_version': os_version,
            'device_name': cls.get_device_name(),
        }
        
        app_logger.info(f"Generated fingerprint for device: {fingerprint['device_name']}")
        app_logger.debug(f"Fingerprint details: {fingerprint}")
        
        return fingerprint


# Singleton instance
device_fingerprint = DeviceFingerprint()
