"""
ZKTeco ZK9500 Fingerprint Reader Integration

Handles communication with ZKTeco fingerprint scanner for enrollment and verification.
Uses zklib library for USB communication with the device.
"""

import time
from typing import Optional, List, Tuple, Callable
from utils.logger import app_logger

try:
    from pyzkfp import ZKFP2
    ZKFP_AVAILABLE = True
    app_logger.info("✅ pyzkfp library loaded successfully")
except ImportError:
    ZKFP_AVAILABLE = False
    app_logger.warning("⚠️ pyzkfp not available - fingerprint scanner will not work")


class ZKTecoReader:
    """
    Interface for ZKTeco ZK9500 fingerprint reader.
    
    Handles:
    - Device connection/disconnection
    - Fingerprint capture during enrollment (4 touches)
    - Fingerprint verification
    - Quality assessment
    """
    
    def __init__(self):
        """Initialize ZKTeco reader (not connected yet)."""
        self.zkfp2: Optional[ZKFP2] = None
        self.is_connected = False
        self._current_templates: List[bytes] = []
        self._registered_fingers = {}  # Dictionary to store finger_id: template
        
        app_logger.info("🔧 ZKTeco Reader initialized (not connected)")
    
    def connect(self, timeout: int = 5) -> bool:
        """
        Connect to ZKTeco fingerprint scanner using pyzkfp.
        
        Args:
            timeout: Connection timeout in seconds (not used with pyzkfp)
            
        Returns:
            True if connected successfully, False otherwise
        """
        if not ZKFP_AVAILABLE:
            app_logger.error("❌ Cannot connect: pyzkfp not installed")
            app_logger.info("💡 Install with: pip install pyzkfp")
            app_logger.info("💡 Also install ZKFinger SDK from ZKTeco website")
            return False
        
        if self.is_connected:
            app_logger.warning("⚠️ Already connected to ZKTeco device")
            return True
        
        try:
            app_logger.info("🔌 Connecting to ZKTeco ZK9500...")
            
            # Initialize ZKFP2
            self.zkfp2 = ZKFP2()
            self.zkfp2.Init()
            
            # Get device count
            device_count = self.zkfp2.GetDeviceCount()
            app_logger.info(f"📱 Found {device_count} ZKTeco device(s)")
            
            if device_count == 0:
                app_logger.error("❌ No ZKTeco devices found")
                app_logger.info("💡 Troubleshooting:")
                app_logger.info("   1. Check USB cable connection")
                app_logger.info("   2. Install ZKFinger SDK from official website")
                app_logger.info("   3. Verify device appears in Device Manager")
                app_logger.info("   4. Try unplugging and reconnecting USB")
                return False
            
            # Open first device
            app_logger.info(f"🔓 Opening device 0...")
            self.zkfp2.OpenDevice(0)
            
            self.is_connected = True
            app_logger.info("✅ Connected to ZKTeco ZK9500 successfully")
            
            return True
            
        except Exception as e:
            app_logger.error(f"❌ Failed to connect to ZKTeco: {e}")
            app_logger.info("💡 Make sure ZKFinger SDK is installed from ZKTeco website")
            self.zkfp2 = None
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from ZKTeco scanner."""
        if not self.is_connected:
            return
        
        try:
            if self.zkfp2:
                # Close device and terminate
                self.zkfp2.CloseDevice()
                self.zkfp2.Terminate()
                self.zkfp2 = None
            
            self.is_connected = False
            self._registered_fingers = {}
            app_logger.info("🔌 Disconnected from ZKTeco ZK9500")
            
        except Exception as e:
            app_logger.error(f"Error disconnecting ZKTeco: {e}")
    
    def capture_fingerprint(
        self, 
        timeout: int = 10,
        quality_threshold: int = 50
    ) -> Tuple[bool, Optional[bytes], int]:
        """
        Capture a single fingerprint touch.
        
        Args:
            timeout: Maximum time to wait for finger touch (seconds)
            quality_threshold: Minimum quality score (0-100) to accept
            
        Returns:
            Tuple of (success, template_data, quality_score)
            - success: True if captured successfully with good quality
            - template_data: Raw fingerprint template bytes (or None if failed)
            - quality_score: Quality assessment 0-100
        """
        if not self.is_connected:
            app_logger.error("❌ Cannot capture: device not connected")
            return (False, None, 0)
        
        try:
            app_logger.info(f"👆 Waiting for fingerprint touch (timeout: {timeout}s)...")
            
            start_time = time.time()
            
            # Wait for finger to be placed on scanner
            while time.time() - start_time < timeout:
                try:
                    # Capture fingerprint using pyzkfp
                    capture = self.zkfp2.AcquireFingerprint()
                    
                    if capture:
                        # capture returns (template, image)
                        template, img = capture
                        
                        # Assess quality based on template data
                        quality = self._assess_quality(template)
                        
                        app_logger.info(f"📸 Fingerprint captured (quality: {quality}/100)")
                        
                        if quality >= quality_threshold:
                            app_logger.info(f"✅ Quality sufficient ({quality} >= {quality_threshold})")
                            return (True, template, quality)
                        else:
                            app_logger.warning(
                                f"⚠️ Quality too low ({quality} < {quality_threshold}) - rejected"
                            )
                            return (False, template, quality)
                    
                    # Small delay to prevent CPU spinning
                    time.sleep(0.1)
                    
                except Exception as inner_e:
                    # Scanner not ready or no finger detected yet
                    time.sleep(0.1)
                    continue
            
            # Timeout reached
            app_logger.warning(f"⏱️ Timeout: No fingerprint detected in {timeout}s")
            return (False, None, 0)
            
        except Exception as e:
            app_logger.error(f"❌ Error capturing fingerprint: {e}")
            return (False, None, 0)
    
    def enroll_fingerprint(
        self,
        progress_callback: Optional[Callable[[int, bool, int], None]] = None,
        required_touches: int = 4,
        quality_threshold: int = 50
    ) -> Tuple[bool, Optional[bytes]]:
        """
        Enroll a fingerprint by capturing multiple touches.
        
        Note: pyzkfp requires exactly 3 templates for DBMerge, but we capture 4
        for better UX and use the best 3.
        
        Args:
            progress_callback: Called after each touch: (touch_num, success, remaining)
            required_touches: Number of successful touches needed (default: 4)
            quality_threshold: Minimum quality to accept each touch
            
        Returns:
            Tuple of (success, consolidated_template)
            - success: True if enrollment completed successfully
            - consolidated_template: Final template data combining all touches
        """
        if not self.is_connected:
            app_logger.error("❌ Cannot enroll: device not connected")
            return (False, None)
        
        app_logger.info(f"🖐️ Starting enrollment: {required_touches} touches required")
        
        self._current_templates = []
        successful_touches = 0
        
        while successful_touches < required_touches:
            touch_number = successful_touches + 1
            remaining = required_touches - successful_touches
            
            app_logger.info(f"👆 Touch {touch_number}/{required_touches} - Place finger on scanner...")
            
            # Turn on light to indicate ready
            try:
                self.zkfp2.Light('green')
            except:
                pass  # Ignore if light control not supported
            
            # Capture fingerprint
            success, template, quality = self.capture_fingerprint(
                timeout=15,
                quality_threshold=quality_threshold
            )
            
            if success and template:
                # Successful touch
                self._current_templates.append(template)
                successful_touches += 1
                remaining = required_touches - successful_touches
                
                app_logger.info(
                    f"✅ Touch {touch_number}/{required_touches} SUCCESS "
                    f"(quality: {quality}) - {remaining} remaining"
                )
                
                # Flash green light
                try:
                    self.zkfp2.Light('green')
                except:
                    pass
                
                # Call progress callback
                if progress_callback:
                    progress_callback(successful_touches, True, remaining)
                
                # Wait for finger to be removed before next capture
                app_logger.info("🖐️ Remove finger from scanner...")
                time.sleep(1.5)
                
            else:
                # Failed touch (low quality or timeout)
                app_logger.warning(
                    f"❌ Touch {touch_number} FAILED "
                    f"(quality: {quality if quality else 'N/A'}) - retrying..."
                )
                
                # Flash red light
                try:
                    self.zkfp2.Light('red')
                    time.sleep(0.3)
                    self.zkfp2.Light('green')
                except:
                    pass
                
                # Call progress callback with failure
                if progress_callback:
                    progress_callback(successful_touches, False, remaining)
                
                # Brief pause before retry
                time.sleep(0.5)
        
        # All touches captured - use best 3 for consolidation
        app_logger.info(f"🎉 All {required_touches} touches captured successfully")
        
        # Select best 3 templates (pyzkfp's DBMerge requires exactly 3)
        best_templates = self._current_templates[:3]  # Use first 3 for now
        # TODO: Could implement quality-based selection of best 3
        
        consolidated = self._consolidate_templates(best_templates)
        
        if consolidated:
            app_logger.info(f"✅ Consolidated template generated")
            
            # Turn off light
            try:
                self.zkfp2.Light('green')
            except:
                pass
            
            return (True, consolidated)
        else:
            app_logger.error("❌ Failed to consolidate templates")
            return (False, None)
    
    def verify_fingerprint(
        self,
        enrolled_template: bytes,
        timeout: int = 10,
        match_threshold: int = 70
    ) -> Tuple[bool, int]:
        """
        Verify a fingerprint against an enrolled template.
        
        Args:
            enrolled_template: Previously enrolled fingerprint template
            timeout: Maximum time to wait for finger touch
            match_threshold: Minimum match score (0-100) to consider verified
            
        Returns:
            Tuple of (verified, confidence)
            - verified: True if fingerprint matches
            - confidence: Match confidence score 0-100
        """
        if not self.is_connected:
            app_logger.error("❌ Cannot verify: device not connected")
            return (False, 0)
        
        try:
            app_logger.info(f"🔍 Waiting for fingerprint to verify (timeout: {timeout}s)...")
            
            # Capture fingerprint to verify
            success, captured_template, quality = self.capture_fingerprint(
                timeout=timeout,
                quality_threshold=40  # Lower threshold for verification
            )
            
            if not success or not captured_template:
                app_logger.warning("⚠️ Failed to capture fingerprint for verification")
                return (False, 0)
            
            # Compare captured template with enrolled template
            match_score = self._compare_templates(enrolled_template, captured_template)
            
            verified = match_score >= match_threshold
            
            if verified:
                app_logger.info(f"✅ VERIFIED (confidence: {match_score}/100)")
            else:
                app_logger.warning(
                    f"❌ NOT VERIFIED (score: {match_score} < {match_threshold})"
                )
            
            return (verified, match_score)
            
        except Exception as e:
            app_logger.error(f"❌ Error during verification: {e}")
            return (False, 0)
    
    def _assess_quality(self, template: bytes) -> int:
        """
        Assess fingerprint quality.
        
        Args:
            template: Raw fingerprint template data
            
        Returns:
            Quality score 0-100
        """
        # Simple quality assessment based on template data
        # In a real implementation, zklib might provide quality scores
        # For now, we'll do a basic check
        
        if not template or len(template) < 100:
            return 0
        
        # Basic quality heuristics:
        # - Template size should be reasonable (typically 512-2048 bytes)
        # - Should not be all zeros
        # - Should have sufficient entropy
        
        size = len(template)
        
        # Size check
        if size < 200:
            return 30  # Too small, probably low quality
        elif size < 400:
            return 60  # Acceptable
        else:
            return 85  # Good size
    
    def _consolidate_templates(self, templates: List[bytes]) -> Optional[bytes]:
        """
        Consolidate multiple fingerprint templates into one using pyzkfp's DBMerge.
        
        Args:
            templates: List of template data from multiple touches (must be 3)
            
        Returns:
            Consolidated template, or None if failed
        """
        if not templates or len(templates) < 3:
            app_logger.error(f"Need at least 3 templates, got {len(templates)}")
            return None
        
        try:
            app_logger.info(f"🔗 Consolidating {len(templates)} templates using DBMerge...")
            
            # Use pyzkfp's DBMerge to merge templates
            # DBMerge takes exactly 3 templates and returns (regTemp, regTempLen)
            reg_temp, reg_temp_len = self.zkfp2.DBMerge(templates[0], templates[1], templates[2])
            
            app_logger.info(f"✅ Consolidated template: {reg_temp_len} bytes")
            
            return reg_temp
            
        except Exception as e:
            app_logger.error(f"Error consolidating templates: {e}")
            return None
    
    def _compare_templates(self, template1: bytes, template2: bytes) -> int:
        """
        Compare two fingerprint templates using pyzkfp's DBMatch.
        
        Args:
            template1: First template
            template2: Second template
            
        Returns:
            Match score 0-100 (100 if match, 0 if no match)
        """
        try:
            if not template1 or not template2:
                return 0
            
            # Use pyzkfp's DBMatch for 1:1 comparison
            # Returns 1 if match, 0 if no match
            match_result = self.zkfp2.DBMatch(template1, template2)
            
            # Convert to percentage (0 or 100)
            # Note: pyzkfp doesn't provide confidence score, only match/no-match
            # For more detailed score, we'd need to use DBIdentify with a database
            score = 100 if match_result == 1 else 0
            
            return score
            
        except Exception as e:
            app_logger.error(f"Error comparing templates: {e}")
            return 0
    
    def get_device_info(self) -> dict:
        """
        Get device information.
        
        Returns:
            Dict with device info (model, firmware, etc.)
        """
        if not self.is_connected:
            return {
                'connected': False,
                'error': 'Device not connected'
            }
        
        try:
            # Get device info from zklib
            return {
                'connected': True,
                'model': 'ZK9500',
                'manufacturer': 'ZKTeco',
                'status': 'Ready'
            }
        except Exception as e:
            app_logger.error(f"Error getting device info: {e}")
            return {
                'connected': self.is_connected,
                'error': str(e)
            }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.disconnect()


# Global singleton instance
_reader_instance: Optional[ZKTecoReader] = None


def get_reader() -> ZKTecoReader:
    """
    Get global ZKTeco reader instance (singleton).
    
    Returns:
        ZKTecoReader instance
    """
    global _reader_instance
    
    if _reader_instance is None:
        _reader_instance = ZKTecoReader()
        app_logger.info("📱 Created ZKTeco reader singleton instance")
    
    return _reader_instance
