"""Application settings and configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_VERSION = "v1"
API_PREFIX = os.getenv("API_PREFIX", "valhalla")  # valhalla prefix for Django
API_DESKTOP_PATH = f"/{API_PREFIX}/api/{API_VERSION}/desktop"

# Heimdall WebSocket Configuration
HEIMDALL_WS_URL = os.getenv("HEIMDALL_WS_URL", "ws://localhost:8080")
HEIMDALL_PREFIX = os.getenv("HEIMDALL_PREFIX", "heimdall")  # heimdall prefix
HEIMDALL_WS_ENDPOINT = f"/{HEIMDALL_PREFIX}/api/{API_VERSION}/ws/desktop-agent"
HEIMDALL_HEARTBEAT_INTERVAL = 30

# Database Configuration
DB_NAME = "thor_agent.db"
DB_PATH = DATA_DIR / DB_NAME

# Security Configuration
APP_NAME = "ThorDesktopAgent"
KEYRING_SERVICE_NAME = "ThorAgent"

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 10
JWT_REFRESH_TOKEN_LIFETIME_DAYS = 30

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "thor_agent.log"
LOG_ROTATION = "10 MB"
LOG_RETENTION = "30 days"

# Development Configuration
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# WebView Configuration
# Django app URLs - WebEngine loads this directly
if DEV_MODE:
    DJANGO_WEB_URL = os.getenv("DJANGO_WEB_URL", "http://localhost:8000")
else:
    DJANGO_WEB_URL = os.getenv("DJANGO_WEB_URL", "https://your-production-domain.com")

# WebView settings
WEBVIEW_ENABLE_DEVTOOLS = DEV_MODE  # F12 DevTools only in development
WEBVIEW_ENABLE_CONTEXT_MENU = DEV_MODE  # Right-click menu only in development

# Application Configuration
APP_VERSION = "1.0.0"
WINDOW_TITLE = "Thor Desktop Agent"
MIN_WINDOW_WIDTH = 400
MIN_WINDOW_HEIGHT = 500
