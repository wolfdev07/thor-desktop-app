"""Application constants."""

# Application Info
APP_VERSION = "1.0.0"
APP_NAME = "Thor Desktop Agent"

# User Types (must match backend)
USER_TYPE_OWNER = 0
USER_TYPE_MANAGER = 1
USER_TYPE_ADMIN = 2

ALLOWED_USER_TYPES = [USER_TYPE_OWNER, USER_TYPE_MANAGER, USER_TYPE_ADMIN]

# API Endpoints
ENDPOINT_LOGIN = "/auth/login"
ENDPOINT_REFRESH = "/auth/refresh"
ENDPOINT_LOGOUT = "/auth/logout"
ENDPOINT_DEVICES = "/devices"

# Keyring Keys
KEY_ACCESS_TOKEN = "access_token"
KEY_REFRESH_TOKEN = "refresh_token"
KEY_DEVICE_ID = "device_id"
KEY_USER_EMAIL = "user_email"
KEY_DB_ENCRYPTION_KEY = "db_encryption_key"

# Database Tables
TABLE_MEMBERS = "members"
TABLE_FINGERPRINTS = "fingerprints"
TABLE_SETTINGS = "settings"

# Application States
STATE_LOGGED_OUT = "logged_out"
STATE_LOGGED_IN = "logged_in"
STATE_TOKEN_REFRESHING = "token_refreshing"
STATE_ERROR = "error"
