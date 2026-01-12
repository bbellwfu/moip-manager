"""Configuration for MoIP Manager."""
import os
from dotenv import load_dotenv

load_dotenv()

# Default values - credentials should be set via environment variables or web UI
_DEFAULTS = {
    "controller_ip": "",
    "telnet_port": "23",
    "api_port": "443",
    "username": "",
    "password": "",
    "verify_ssl": "false",
    "timeout": "10"
}


def get_setting(key: str, default: str = None) -> str:
    """
    Get a setting value with priority:
    1. Database settings (if available)
    2. Environment variable
    3. Default value
    """
    # Try database first
    try:
        from app import database as db
        stored = db.get_all_settings()
        if key in stored and stored[key]:
            return stored[key]
    except Exception:
        pass  # Database not available yet

    # Map setting keys to env var names
    env_map = {
        "controller_ip": "MOIP_HOST",
        "telnet_port": "MOIP_TELNET_PORT",
        "api_port": "MOIP_API_PORT",
        "username": "MOIP_API_USERNAME",
        "password": "MOIP_API_PASSWORD",
    }

    env_name = env_map.get(key)
    if env_name:
        env_val = os.getenv(env_name)
        if env_val:
            return env_val

    # Fall back to default
    return default or _DEFAULTS.get(key, "")


# Legacy config variables (for backward compatibility)
# These are evaluated once at import time
MOIP_HOST = os.getenv("MOIP_HOST", "")
MOIP_TELNET_PORT = int(os.getenv("MOIP_TELNET_PORT", "23"))
MOIP_API_PORT = int(os.getenv("MOIP_API_PORT", "443"))
MOIP_API_USERNAME = os.getenv("MOIP_API_USERNAME", "")
MOIP_API_PASSWORD = os.getenv("MOIP_API_PASSWORD", "")

# Web Server Settings
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))


def get_moip_settings() -> dict:
    """Get current MoIP settings from database or defaults."""
    return {
        "host": get_setting("controller_ip"),
        "telnet_port": int(get_setting("telnet_port")),
        "api_port": int(get_setting("api_port")),
        "username": get_setting("username"),
        "password": get_setting("password"),
        "verify_ssl": get_setting("verify_ssl") == "true",
        "timeout": int(get_setting("timeout"))
    }
