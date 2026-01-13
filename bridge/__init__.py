"""
Hardware Bridge Module

This module provides the QWebChannel bridge for JavaScript ↔ Python communication.
Allows web pages (Django) to access local hardware like fingerprint scanners.
"""

from .hardware_bridge import HardwareBridge

__all__ = ['HardwareBridge']
