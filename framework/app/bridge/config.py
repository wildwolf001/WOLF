"""
Bridge Configuration
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class BridgeConfig:
    """Bridge layer configuration"""
    # Endpoints
    api_endpoint: str = "http://localhost:8000/api"
    ws_endpoint: str = "ws://localhost:8000/ws"

    # Auth
    auth_endpoint: str = "http://localhost:8000/auth"
    client_id: str = "wolf2"
    client_secret: str = ""

    # Reconnection
    max_reconnect_attempts: int = 3
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 30.0

    # Heartbeat
    heartbeat_interval: int = 30
    liveness_timeout: int = 45

    # Flush gate
    flush_gate_max_size: int = 100

    # JWT
    jwt_secret: str = "wolf-secret-key"
    jwt_access_token_ttl: int = 3600
    jwt_refresh_token_ttl: int = 86400 * 7

    # Refresh
    refresh_before: int = 300  # seconds before expiry to refresh


@dataclass
class RemoteBridgeConfig:
    """Configuration for remote bridge connection"""
    endpoint: str
    ws_endpoint: str
    auth_endpoint: str
    workspace_id: str
    user_id: str
    token: Optional[str] = None


DEFAULT_BRIDGE_CONFIG = BridgeConfig()