"""
Core Configuration
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration"""
    # App
    app_name: str = "WOLF 2.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    # Workspace
    workspace_base: str = "./workspace"

    # Model
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    # Query
    max_turns: int = 10
    max_tokens: int = 8000
    temperature: float = 0.7

    # Transport
    heartbeat_interval: int = 30
    reconnect_max_attempts: int = 3

    # Auth
    jwt_secret: str = "wolf-secret-key-change-in-production"
    jwt_access_token_ttl: int = 3600
    jwt_refresh_token_ttl: int = 86400 * 7


def load_config() -> Config:
    """Load configuration from environment"""
    import os

    return Config(
        app_name=os.getenv("WOLF_APP_NAME", "WOLF 2.0"),
        debug=os.getenv("WOLF_DEBUG", "false").lower() == "true",
        host=os.getenv("WOLF_HOST", "0.0.0.0"),
        port=int(os.getenv("WOLF_PORT", "8080")),
        workspace_base=os.getenv("WOLF_WORKSPACE_BASE", "./workspace"),
        model=os.getenv("WOLF_MODEL", "claude-sonnet-4-20250514"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        api_base=os.getenv("API_BASE"),
        max_turns=int(os.getenv("WOLF_MAX_TURNS", "10")),
        max_tokens=int(os.getenv("WOLF_MAX_TOKENS", "8000")),
        temperature=float(os.getenv("WOLF_TEMPERATURE", "0.7")),
        jwt_secret=os.getenv("JWT_SECRET", "wolf-secret-key-change-in-production"),
    )


DEFAULT_CONFIG = Config()