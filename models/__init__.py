"""Data models and schemas."""
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime


@dataclass
class User:
    """User model from backend."""
    id: int
    email: str
    first_name: str
    last_name: str
    user_type: int
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}".strip()


@dataclass
class LoginResponse:
    """Login response from API."""
    access_token: str
    refresh_token: str
    device_id: str
    user: User


@dataclass
class RefreshResponse:
    """Refresh token response from API."""
    access_token: str
    refresh_token: str


@dataclass
class ApiError:
    """API error response."""
    error: str
    detail: Optional[str] = None
    status_code: Optional[int] = None
