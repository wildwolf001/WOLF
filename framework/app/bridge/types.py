"""
Bridge Types
Type definitions for bridge layer
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum


class BridgeEventType(Enum):
    """Bridge event types"""
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    THINKING_START = "thinking_start"
    THINKING_COMPLETE = "thinking_complete"
    CONTENT = "content"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    SESSION_UPDATE = "session_update"


@dataclass
class BridgeMessage:
    """Bridge message structure"""
    type: str
    data: Dict[str, Any]
    session_id: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class SessionInfo:
    """Session information"""
    session_id: str
    user_id: str
    workspace_path: str
    created_at: float
    last_active: float
    metadata: Dict[str, Any]


@dataclass
class AuthTokens:
    """Authentication tokens"""
    access_token: str
    refresh_token: str
    expires_at: float


@dataclass
class BridgeConfig:
    """Bridge configuration"""
    endpoint: str
    ws_endpoint: str
    auth_endpoint: str
    client_id: str
    client_secret: str
    refresh_before: int = 300  # seconds before expiry to refresh